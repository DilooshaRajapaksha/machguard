import { Link } from 'react-router-dom'

function NotFound() {
  return (
    <div className="py-20 text-center">
      <p className="text-5xl font-bold text-teal-600">404</p>
      <h1 className="mt-3 text-xl font-bold text-navy-900">Page not found</h1>
      <p className="mt-2 text-slate-500">The page you are looking for does not exist.</p>
      <Link
        to="/"
        className="mt-6 inline-block rounded-lg bg-navy-900 px-4 py-2 text-sm font-medium text-white hover:bg-navy-800"
      >
        Back to dashboard
      </Link>
    </div>
  )
}

export default NotFound
