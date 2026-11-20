import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

export default function PasswordInput(props) {
  const [visible, setVisible] = useState(false)
  const Icon = visible ? EyeOff : Eye
  return <span className="password-control">
    <input {...props} type={visible ? 'text' : 'password'} />
    <button type="button" aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible} onClick={() => setVisible(!visible)}><Icon size={18} /></button>
  </span>
}
