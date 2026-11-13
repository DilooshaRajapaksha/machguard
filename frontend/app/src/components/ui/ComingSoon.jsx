function ComingSoon({ icon: Icon, title, text }) {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center rounded-2xl bg-white px-6 py-14 text-center shadow-sm ring-1 ring-slate-200">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 text-teal-600">
        <Icon size={28} />
      </span>
      <h1 className="mt-5 text-xl font-bold text-navy-900">{title}</h1>
      <p className="mt-2 text-slate-500">{text}</p>
      <span className="mt-6 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
        Coming soon
      </span>
    </div>
  )
}

export default ComingSoon