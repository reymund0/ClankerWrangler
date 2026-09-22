import { afterEach } from 'vitest'

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true

afterEach(() => {
  document.body.replaceChildren()
  window.history.replaceState(null, '', '/')
})
