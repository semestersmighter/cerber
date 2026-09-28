import { Navigate, useNavigate } from 'react-router-dom'

import Button from '../components/Button'
import { clearSession, getSession } from '../services/session'

function Dashboard() {
  const navigate = useNavigate()
  const session = getSession()

  // Pas de session : retour à la connexion
  if (!session) {
    return <Navigate to="/" replace />
  }

  const handleLogout = () => {
    clearSession()
    navigate('/')
  }

  return (
    <main className="auth-page">
      <div className="auth-container">
        <h1>Tableau de bord</h1>
        <p>Connecté avec le NIF {session.nif}</p>

        <Button onClick={handleLogout}>Se déconnecter</Button>
      </div>
    </main>
  )
}

export default Dashboard
