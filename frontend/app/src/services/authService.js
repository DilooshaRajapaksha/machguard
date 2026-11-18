import { apiRequest } from './api'

export function login(username, password, options = {}) {
  return apiRequest('/auth/login', {
    ...options,
    method: 'POST',
    body: {
      username: username.trim(),
      password,
    },
  })
}

export function getCurrentUser(token, options = {}) {
  return apiRequest('/auth/me', {
    ...options,
    method: 'GET',
    token,
  })
}

export function changePassword(
  token,
  currentPassword,
  newPassword,
  options = {},
) {
  return apiRequest('/auth/change-password', {
    ...options,
    method: 'POST',
    token,
    body: {
      current_password: currentPassword,
      new_password: newPassword,
    },
  })
}