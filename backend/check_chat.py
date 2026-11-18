import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sandbox = tempfile.TemporaryDirectory()
os.environ['MACHGUARD_DB'] = os.path.join(sandbox.name, 'chat.db')
os.environ['MACHGUARD_SECRET'] = 'chat-test-only-012345678901234567890123456789'

from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app import chat_service, db, security, users, simulator
from app.warning_service import build_warning
from app.notification_service import record_warning


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        with db.connect() as conn:
            for table in ('chat_messages', 'chat_conversations', 'chat_requests', 'users', 'notifications', 'notification_state', 'readings'):
                conn.execute(f'DELETE FROM {table}')
        for name, change in [('first', False), ('second', False), ('newuser', True)]:
            users.create(name, name, security.hash_password('Testing-Password-123'), 'viewer', change)
        self.headers = {}
        for name in ('first', 'second', 'newuser'):
            token = self.client.post('/auth/login', json={'username': name, 'password': 'Testing-Password-123'}).json()['access_token']
            self.headers[name] = {'Authorization': 'Bearer ' + token}
        self.config = patch.object(chat_service, 'settings', return_value={'GEMINI_API_KEY': 'test', 'GEMINI_MODEL': 'test'})
        self.config.start()
        self.addCleanup(self.config.stop)

    def send(self, body, user='first'):
        return self.client.post('/chat/messages', json=body, headers=self.headers[user])

    def reset_limit(self):
        with db.connect() as conn:
            conn.execute('DELETE FROM chat_requests')

    def test_auth_and_validation(self):
        self.assertEqual(self.client.get('/chat/conversations').status_code, 401)
        self.assertEqual(self.client.get('/chat/status', headers=self.headers['newuser']).status_code, 403)
        for body in ({'message': '   '}, {'message': 'x' * 4001}, {'message': 'hello', 'role': 'system'}):
            self.assertEqual(self.send(body).status_code, 422)

    def test_private_history_and_followups(self):
        with patch.object(chat_service, 'generate_reply', new_callable=AsyncMock, return_value='Review the readings.') as provider:
            first = self.send({'message': 'Check the motor'})
            self.assertEqual(first.status_code, 200, first.text)
            conversation_id = first.json()['conversation_id']
            self.assertEqual(self.client.get('/chat/conversations', headers=self.headers['second']).json(), [])
            self.assertEqual(self.client.get('/chat/conversations/' + conversation_id, headers=self.headers['second']).status_code, 404)
            self.assertEqual(self.send({'message': 'read it', 'conversation_id': conversation_id}, 'second').status_code, 404)
            self.assertEqual(self.send({'message': 'again', 'conversation_id': conversation_id}).status_code, 429)
            self.reset_limit()
            reply = self.send({'message': 'Explain simply', 'conversation_id': conversation_id})
            self.assertEqual(reply.status_code, 200)
            self.assertEqual(len(provider.call_args.args[0]), 3)
            self.assertEqual(provider.call_args.args[0][0]['content'], 'Check the motor')
            saved = self.client.get('/chat/conversations/' + conversation_id, headers=self.headers['first']).json()
            self.assertEqual(len(saved['messages']), 4)
            self.reset_limit()
            self.assertEqual(self.send({'message': 'switch', 'conversation_id': conversation_id, 'machine_id': 'other'}).status_code, 409)

    def test_configuration_and_failure(self):
        with patch.object(chat_service, 'settings', return_value={'GEMINI_API_KEY': '', 'GEMINI_MODEL': ''}):
            self.assertEqual(self.send({'message': 'Hello'}).status_code, 503)
        with patch.object(chat_service, 'generate_reply', new_callable=AsyncMock, side_effect=HTTPException(503, 'Unavailable')):
            self.assertEqual(self.send({'message': 'Hello'}).status_code, 503)
        self.assertEqual(self.client.get('/chat/conversations', headers=self.headers['first']).json(), [])
        with db.connect() as conn:
            self.assertEqual(conn.execute('SELECT busy_until FROM chat_requests').fetchone()[0], 0)

    def test_energy(self):
        body = {'energy_kwh': 10, 'production_units': 20, 'emission_factor': 0.5, 'factor_source': 'Hypothetical test'}
        response = self.client.post('/chat/energy', json=body, headers=self.headers['first'])
        self.assertEqual(response.json()['estimated_kg_co2e'], 5)
        self.assertEqual(response.json()['kwh_per_unit'], 0.5)
        body['production_units'] = 0
        self.assertEqual(self.client.post('/chat/energy', json=body, headers=self.headers['first']).status_code, 422)
        body['production_units'] = 1e-300
        self.assertEqual(self.client.post('/chat/energy', json=body, headers=self.headers['first']).status_code, 422)

    def test_context_and_warning_regression(self):
        readings = simulator.generate(simulator.Scenario.HEALTHY, steps=30)
        for reading in readings:
            db.save_reading(reading)
        context = chat_service.machine_context(readings[0].machine_id)
        self.assertEqual(context['source'], 'unknown')
        self.assertIn(context['warning']['status'], ('not_enough_data', 'stale'))
        self.assertEqual(chat_service.machine_context('absent')['warning']['status'], 'no_data')
        faulty = simulator.generate(simulator.Scenario.SLOW_OVERHEATING, steps=120)
        warning = build_warning(faulty[0].machine_id, faulty, source='simulated')
        self.assertEqual(warning.status, 'fault')
        self.assertIsNotNone(record_warning(warning))
        self.assertIsNone(record_warning(warning))

    def test_provider_response_handling(self):
        import asyncio
        import httpx
        response = httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'A clear answer.'}]}}]})
        fake = AsyncMock()
        fake.__aenter__.return_value = fake
        fake.post.return_value = response
        with patch.object(chat_service.httpx, 'AsyncClient', return_value=fake):
            text = asyncio.run(chat_service.generate_reply([{'role': 'user', 'content': 'Hello'}], {}, {'GEMINI_API_KEY': 'test', 'GEMINI_MODEL': 'test'}))
            self.assertEqual(text, 'A clear answer.')
            self.assertEqual(fake.post.call_args.kwargs['headers']['x-goog-api-key'], 'test')
            self.assertEqual(fake.post.call_args.kwargs['json']['contents'][0]['role'], 'user')
            fake.post.return_value = httpx.Response(429)
            with self.assertRaises(HTTPException):
                asyncio.run(chat_service.generate_reply([{'role': 'user', 'content': 'Hello'}], {}, {'GEMINI_API_KEY': 'test', 'GEMINI_MODEL': 'test'}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
