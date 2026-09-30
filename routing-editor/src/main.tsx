import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { bootstrapToken } from './api'
import { App } from './App'
import './styles.css'

try {
  const savedTheme = localStorage.getItem('routing-editor-theme')
  if (savedTheme === 'light' || savedTheme === 'dark') document.documentElement.dataset.theme = savedTheme
  else document.documentElement.removeAttribute('data-theme')
} catch {
  // Keep the CSS system theme when browser storage is unavailable.
}

bootstrapToken()
createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
