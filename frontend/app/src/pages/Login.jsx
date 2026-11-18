import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function getDestination(value) {
  if (
    typeof value !== 'string' ||
    !value.startsWith('/') ||
    value.startsWith('//') ||
    value.includes('\\') ||
    /^\/login(?:[/?#]|$)/i.test(value)
  ) {
    return '/'
  }

  return value
}

export default function Login() {
  const {
    isAuthenticated,
    mustChangePassword,
    loading,
    signIn,
    signOut,
    updatePassword,
  } = useAuth()

  const location = useLocation()
  const destination = getDestination(location.state?.from)

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')

  const changingPassword = isAuthenticated && mustChangePassword

  if (isAuthenticated && !mustChangePassword) {
    return <Navigate to={destination} replace />
  }

  async function handleLogin(event) {
    event.preventDefault()

    if (loading) return

    setError('')

    try {
      await signIn(username, password)
    } catch (problem) {
      setError(problem.message || 'Sign-in failed. Please try again.')
    } finally {
      setPassword('')
    }
  }

  async function handlePasswordChange(event) {
    event.preventDefault()

    if (loading) return

    setError('')

    if (newPassword !== confirmPassword) {
      setError('The new passwords do not match.')
      return
    }

    if (
      newPassword.length < 10 ||
      !/[A-Za-z]/.test(newPassword) ||
      !/[0-9]/.test(newPassword)
    ) {
      setError(
        'Use at least 10 characters, including a letter and a number.',
      )
      return
    }

    if (newPassword === currentPassword) {
      setError('Choose a different password from your current password.')
      return
    }

    try {
      await updatePassword(currentPassword, newPassword)
    } catch (problem) {
      setError(problem.message || 'Could not change your password.')
    } finally {
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    }
  }

  function handleBack() {
    signOut()
    setError('')
    setPassword('')
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
  }

  const inputClass =
    'mt-2 block w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-slate-900 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100 disabled:opacity-60'

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10">
      <section
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl sm:p-8"
        aria-labelledby="login-title"
      >
        <p className="text-xs font-bold uppercase tracking-widest text-teal-700">
          NovaFodge / MachGuard
        </p>

        <h1
          id="login-title"
          className="mt-3 text-2xl font-bold text-slate-900"
        >
          {changingPassword ? 'Choose your new password' : 'Welcome back'}
        </h1>

        <p className="mt-2 text-sm leading-6 text-slate-600">
          {changingPassword
            ? 'Change your initial password to continue. Use at least 10 characters, including a letter and a number. Do not include your username.'
            : 'Sign in to view your machines, readings and maintenance warnings.'}
        </p>

        {error && (
          <div
            id="auth-error"
            role="alert"
            className="mt-5 whitespace-pre-line rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        {changingPassword ? (
          <form
            onSubmit={handlePasswordChange}
            className="mt-6 space-y-4"
            aria-busy={loading}
          >
            <div>
              <label
                htmlFor="current-password"
                className="text-sm font-medium text-slate-700"
              >
                Current password
              </label>
              <input
                id="current-password"
                name="current_password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                className={inputClass}
                disabled={loading}
                required
              />
            </div>

            <div>
              <label
                htmlFor="new-password"
                className="text-sm font-medium text-slate-700"
              >
                New password
              </label>
              <input
                id="new-password"
                name="new_password"
                type="password"
                autoComplete="new-password"
                minLength={10}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                className={inputClass}
                disabled={loading}
                required
              />
            </div>

            <div>
              <label
                htmlFor="confirm-password"
                className="text-sm font-medium text-slate-700"
              >
                Confirm new password
              </label>
              <input
                id="confirm-password"
                name="confirm_password"
                type="password"
                autoComplete="new-password"
                minLength={10}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className={inputClass}
                disabled={loading}
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-teal-700 px-4 py-3 font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? 'Saving password…' : 'Save password and continue'}
            </button>

            <button
              type="button"
              onClick={handleBack}
              disabled={loading}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              Back to sign in
            </button>
          </form>
        ) : (
          <form
            onSubmit={handleLogin}
            className="mt-6 space-y-4"
            aria-busy={loading}
          >
            <div>
              <label
                htmlFor="username"
                className="text-sm font-medium text-slate-700"
              >
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className={inputClass}
                disabled={loading}
                required
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="text-sm font-medium text-slate-700"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className={inputClass}
                disabled={loading}
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading || !username.trim()}
              className="w-full rounded-lg bg-teal-700 px-4 py-3 font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        )}
      </section>
    </main>
  )
}