import { useEffect, useRef, useState } from 'react'
import { ChevronDown, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

function getInitials(name) {
  return name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export default function ProfileMenu() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)
  const buttonRef = useRef(null)

  const displayName =
    user?.full_name?.trim() || user?.username || 'User'

  const roleLabel =
    user?.role === 'admin'
      ? 'Administrator'
      : user?.role === 'viewer'
        ? 'Viewer'
        : user?.role || 'User'

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpen(false)
      }
    }

    function handleEscape(event) {
      if (event.key === 'Escape' && open) {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [open])

  function handleSignOut() {
    setOpen(false)
    signOut()
    navigate('/login', { replace: true })
  }

  if (!user) {
    return null
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        aria-label={`Account: ${displayName}`}
        aria-expanded={open}
        aria-controls="profile-details"
        className="flex items-center gap-2 rounded-full py-1 pl-1 pr-2 text-slate-200 hover:bg-white/10"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-400 text-sm font-semibold text-navy-950">
          {getInitials(displayName)}
        </span>

        <ChevronDown
          size={16}
          className={`transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div
          id="profile-details"
          className="absolute right-0 z-50 mt-2 w-72 overflow-hidden rounded-xl bg-white shadow-xl ring-1 ring-slate-200"
        >
          <div className="px-4 py-4">
            <p className="break-words font-semibold text-navy-900">
              {displayName}
            </p>

            <p className="mt-1 break-words text-sm text-slate-500">
              Username: {user.username}
            </p>

            <span className="mt-2 inline-block rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-700">
              {roleLabel}
            </span>
          </div>

          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-2 border-t border-slate-100 px-4 py-3 text-sm font-medium text-rose-600 hover:bg-rose-50"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}