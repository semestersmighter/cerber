// Toutes les requêtes vers le backend passent par ce fichier.
// En dev, Vite redirige /api vers le backend (voir vite.config.js) ;
// en prod, nginx fait de même (voir nginx.conf).
const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch {
    throw new ApiError(0, 'Serveur injoignable, réessayez plus tard.')
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    // FastAPI renvoie { detail: "..." } ; en cas de 422, detail est un tableau
    const message =
      typeof data?.detail === 'string' ? data.detail : 'Une erreur est survenue.'
    throw new ApiError(response.status, message)
  }

  return data
}

export function login(nif, password) {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ nif, password }),
  })
}
