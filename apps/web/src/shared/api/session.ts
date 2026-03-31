const SESSION_KEY = "llm-router-session-id"

export function getSessionId(): string {
  if (globalThis.window === undefined) {
    return ""
  }
  let id = globalThis.window.localStorage.getItem(SESSION_KEY)
  if (!id) {
    id = crypto.randomUUID()
    globalThis.window.localStorage.setItem(SESSION_KEY, id)
  }
  return id
}
