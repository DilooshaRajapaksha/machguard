import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { Anchor, Bot, Cog, LayoutDashboard, LifeBuoy, Menu, X } from 'lucide-react'
import ProfileMenu from './ProfileMenu'
import { appName, companyName } from '../../config'

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/machines', label: 'Machines', icon: Cog },
  { to: '/support', label: 'Support', icon: LifeBuoy },
  { to: '/assistant', label: 'AI', icon: Bot },
]

function linkClass({ isActive }) {
  const base = 'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors'
  return isActive
    ? `${base} bg-white/10 text-white`
    : `${base} text-slate-300 hover:bg-white/5 hover:text-white`
}

function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <header className="sticky top-0 z-30 bg-navy-900 shadow-lg shadow-navy-950/20">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-400 text-navy-950">
            <Anchor size={20} strokeWidth={2.5} />
          </span>
          <span className="leading-tight">
            <span className="block text-base font-bold text-white">{appName}</span>
            <span className="block text-xs text-slate-400">{companyName}</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={linkClass}>
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-1">
          <ProfileMenu />
          <button
            type="button"
            onClick={() => setMenuOpen(!menuOpen)}
            className="rounded-lg p-2 text-slate-300 hover:bg-white/10 hover:text-white md:hidden"
            aria-label="Open menu"
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav className="space-y-1 border-t border-white/10 px-4 py-3 md:hidden">
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={linkClass}
              onClick={() => setMenuOpen(false)}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}

export default Navbar