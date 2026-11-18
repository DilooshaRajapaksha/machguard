# Maintenance assistant

The Assistant page supports private conversation history, follow-up questions and optional machine context. It calls the Google Gemini generateContent API from the backend. It does not train a language model or operate equipment.

## Start

1. Open `backend/.env`. Keep its existing contents, especially `MACHGUARD_SECRET`.
2. Add `GEMINI_API_KEY=your-key` and `GEMINI_MODEL=your-enabled-model-id` on separate lines. Use a model available in your API project that supports generateContent and has free-tier quota. Do not copy these values into the frontend or commit `.env`.
3. From `backend`, run `venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
4. From `frontend/app`, run `npm run dev`.
5. Sign in and select Assistant. Ask a question, then a follow-up. Reloading requires signing in again because the existing login keeps tokens in memory; conversation history remains in the database.

For a free demo, create a key at https://aistudio.google.com/api-keys and keep the project on the Free tier without enabling billing. Use GEMINI_MODEL=gemini-3.8-flash if available in your project. Free quotas can change or be exhausted. Without configuration, the page explains setup and the energy calculator remains available. No API calls are made until a signed-in user sends a message.

## Check

From `backend`, run `venv\Scripts\python.exe check_chat.py`. Tests use a temporary database and a mocked provider; they do not incur API charges.

From `frontend/app`, run `npm run build`.

In the browser, check a general question, a follow-up, a new machine conversation, reopening a saved conversation, and the mobile layout. A second user must not see the first user's history.

For a calculator check only, enter energy 10, output 20, factor 0.5 and source `Hypothetical test`. Expect 5 kg CO2e and 0.5 kWh per unit. This factor is not a Sri Lankan grid factor.

## Evidence and limits

Current readings lack stored provenance, so chat labels their source unknown. Stale or timezone-unknown readings are not presented as a current diagnosis. The warning model uses synthetic healthy data, and maintenance cards remain sample guidance. The last twelve messages are sent as conversational context; the full saved conversation can be reopened.

Messages and selected machine context leave the server for Google Gemini. Only use material permitted for that service. Google may use free-tier content to improve products; use sample data only. There is no document retrieval or manual ingestion in this version.

The calculator multiplies entered kWh by the supplied kgCO2e/kWh factor and divides kWh by useful production units. Users must verify the factor and use energy/output from the same period. It does not calculate measured savings or optimize production settings.

Existing notification generation still needs wiring into reading ingestion and display in the dashboard. Existing monitoring/simulator endpoints retain their previous authentication behavior; do not expose this development server publicly.
