import { Link, useLocation } from 'react-router-dom'
import { Bell, Bot, Cog, FileText, LayoutDashboard, LifeBuoy, Ship, Users } from 'lucide-react'
import ProfileMenu from './ProfileMenu'
import WarningPopup from '../WarningPopup'
import { useAuth } from '../../context/AuthContext'
import './navigation.css'

const userPages = [['/', 'Dashboard', LayoutDashboard], ['/machines', 'Machines', Cog], ['/my-assigns', 'My Assigns', Users], ['/assistant', 'Assistant', Bot], ['/notifications','Notifications',Bell], ['/support', 'Support', LifeBuoy]]
const adminPages = [['/admin', 'Home', LayoutDashboard], ['/admin/machines', 'Machines', Cog], ['/admin/engineers', 'Engineers', Users], ['/admin/reports', 'Reports', FileText], ['/admin/notifications','Notifications',Bell], ['/admin/support','Support',LifeBuoy]]

export default function Navbar({ admin = false }) {
  const { pathname } = useLocation()
  const { user, signOut } = useAuth()
  const pages = admin ? adminPages : userPages.filter(([path]) => path !== '/my-assigns' || user.role === 'viewer')
  const selected = pages.findIndex(([path]) => pathname.replace(/\/$/, '') === path.replace(/\/$/, '') || (path === '/machines' && (pathname.startsWith('/equipment/') || pathname.startsWith('/machines/'))))
  return <aside className={admin ? "harbor-sidebar" : "harbor-sidebar user-rail"}>
    <div className="harbor-top">
      <Link className="harbor-logo" to={admin ? '/admin' : '/'} aria-label="MachGuard home" />
      <strong className="dockyard-word">DOCKYARD</strong>
    </div>
    <nav style={{'--pages': pages.length}} className="harbor-nav" aria-label={admin ? 'Admin pages' : 'User pages'}>
      {selected >= 0 && <span aria-hidden="true" className="harbor-ship" style={{'--row': selected}}><Ship size={28} /></span>}
      {pages.map(([path, label, Icon], index) => <Link key={path} to={path} aria-current={selected === index ? 'page' : undefined}>
        <Icon size={17} />{selected === index && <Ship className="mobile-ship" size={26} aria-hidden="true" />}{label}
      </Link>)}
    </nav>
    {user.role === 'admin' && <Link className="harbor-switch" to={admin ? '/' : '/admin'}>{admin ? 'User dashboard' : 'Admin dashboard'}</Link>}
    {admin ? <button className="dock-signout" onClick={signOut}>Sign out</button> : <div className="rail-profile"><ProfileMenu /></div>}
    <WarningPopup admin={admin} />
  </aside>
}
