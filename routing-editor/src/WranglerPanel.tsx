import { useRef, useState } from 'react'

import { api } from './api'



export function WranglerPanel({ status }: { status?: { available: boolean; running: boolean; reason?: string } }) {
  const available = status?.available ?? false
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [failed, setFailed] = useState(false)
  const [output, setOutput] = useState('')
  const [open, setOpen] = useState(false)
  const runButton = useRef<HTMLButtonElement>(null)
  const details = useRef<HTMLDetailsElement>(null)
  const run = async () => {

    setBusy(true); setFailed(false); setOutput(''); setMessage('Running Wrangler…'); setOpen(true)

    try {

      const result = await api.runWrangler()

      setFailed(!result.success)

      setMessage(result.message + (result.truncated ? ' Showing the last 64 KB of output.' : ''))

      setOutput(result.output)

    } catch (error) {

      setFailed(true); setMessage(error instanceof Error ? error.message : 'Unable to run Wrangler.')

    } finally {
      if (details.current) details.current.open = true
      setBusy(false); setOpen(true)
    }

  }

  return <div className="wrangler-action">
    <button ref={runButton} type="button" className="secondary" disabled={!available || busy} onClick={() => void run()}>{busy ? 'Running Wrangler…' : 'Run Wrangler'}</button>
    <details ref={details} className="wrangler-details" open={open} onToggle={(event) => setOpen((event.currentTarget as HTMLDetailsElement).open)} onKeyDown={(event) => {
      if (event.key === 'Escape' && details.current?.open) { details.current.open = false; setOpen(false); runButton.current?.focus() }
    }}>
      <summary>Install details</summary>
      <div className="wrangler-popover">
        <p>Update local Codex, Claude Code and Windsurf rules and skills from this checkout. Previously installed files may be replaced. Saved routing preferences are preserved; unsaved edits are not saved.</p>
        <p role={failed ? 'alert' : 'status'}>{message || status?.reason || (available ? 'Ready to install.' : 'Installer unavailable on this editor service.')}</p>
        {output && <pre>{output}</pre>}
      </div>
    </details>
  </div>
}
