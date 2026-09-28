// Le backend renvoie le token dans le corps de la réponse (pas de cookie).
// sessionStorage : la session disparaît à la fermeture de l'onglet.
const KEY = 'cerber_session'

export function saveSession({ nif, token }) {
  sessionStorage.setItem(KEY, JSON.stringify({ nif, token }))
}

export function getSession() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY))
  } catch {
    return null
  }
}

export function clearSession() {
  sessionStorage.removeItem(KEY)
}
