import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  login,
  getCurrentUser,
  changePassword,
} from '../services/authService'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(false)
  const requestVersion = useRef(0)

  const signOut = useCallback(() => {
    requestVersion.current += 1
    setSession(null)
    setLoading(false)
  }, [])

  const signIn = useCallback(async (username, password) => {
    const version = ++requestVersion.current

    setLoading(true)
    setSession(null)

    try {
      const result = await login(username, password)
      const user = await getCurrentUser(result.access_token)

      if (version !== requestVersion.current) {
        return null
      }

      setSession({
        token: result.access_token,
        user,
      })

      return user
    } finally {
      if (version === requestVersion.current) {
        setLoading(false)
      }
    }
  }, [])

  const updatePassword = useCallback(
    async (currentPassword, newPassword) => {
      if (!session?.token) {
        throw new Error('Please sign in first.')
      }

      const version = ++requestVersion.current
      let passwordChanged = false

      setLoading(true)

      try {
        const result = await changePassword(
          session.token,
          currentPassword,
          newPassword,
        )

        passwordChanged = true

        const user = await getCurrentUser(result.access_token)

        if (version !== requestVersion.current) {
          return null
        }

        setSession({
          token: result.access_token,
          user,
        })

        return user
      } catch (error) {
        if (
          version === requestVersion.current &&
          (passwordChanged || error.status === 401)
        ) {
          setSession(null)
        }

        if (passwordChanged) {
          throw new Error(
            'Your password was changed. Please sign in with your new password.',
          )
        }

        throw error
      } finally {
        if (version === requestVersion.current) {
          setLoading(false)
        }
      }
    },
    [session],
  )

  const value = useMemo(
    () => ({
      user: session?.user ?? null,
      token: session?.token ?? null,
      isAuthenticated: Boolean(session),
      mustChangePassword: Boolean(session?.user?.must_change_password),
      loading,
      signIn,
      signOut,
      updatePassword,
    }),
    [session, loading, signIn, signOut, updatePassword],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (context === null) {
    throw new Error('useAuth must be used inside AuthProvider.')
  }

  return context
}