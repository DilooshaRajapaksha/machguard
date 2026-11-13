import { Bot } from 'lucide-react'
import ComingSoon from '../components/ui/ComingSoon'

function Assistant() {
  return (
    <ComingSoon
      icon={Bot}
      title="AI Assistant"
      text="Ask questions about error codes, machines and how to use the app."
    />
  )
}

export default Assistant