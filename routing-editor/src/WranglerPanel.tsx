import { useState } from 'react'

import { api } from './api'



export function WranglerPanel({ status }: { status?: { available: boolean; running: boolean; reason?: string } }) {
  const available = status?.available ?? false
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [failed, setFailed] = useState(false)
  const [output, setOutput] = useState('')
  const run = async () => {

    setBusy(true); setFailed(false); setOutput(''); setMessage('Running Wrangler…')

    try {

      const result = await api.runWrangler()

      setFailed(!result.success)

      setMessage(result.message + (result.truncated ? ' Showing the last 64 KB of output.' : ''))

      setOutput(result.output)

    } catch (error) {

      setFailed(true); setMessage(error instanceof Error ? error.message : 'Unable to run Wrangler.')

    } finally { setBusy(false) }

  }

  return <div className="wrangler-action">
    <button type="button" className="secondary" disabled={!available || busy} onClick={() => void run()}>{busy ? 'Running Wrangler…' : 'Run Wrangler'}</button>
    <details className="wrangler-details">
      <summary>Install details</summary>
      <div className="wrangler-popover">
        <p>Update local Codex, Claude Code and Windsurf rules and skills from this checkout. Previously installed files may be replaced. Saved routing preferences are preserved; unsaved edits are not saved.</p>
        <p role={failed ? 'alert' : 'status'}>{message || status?.reason || (available ? 'Ready to install.' : 'Installer unavailable on this editor service.')}</p>
        {output && <pre>{output}</pre>}
      </div>
    </details>
    {message && <span className="wrangler-result" role={failed ? 'alert' : 'status'}>{message}</span>}
  </div>
}
