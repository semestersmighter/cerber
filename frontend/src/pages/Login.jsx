import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import Button from '../components/Button'
import Input from '../components/Input'
import { login } from '../services/api'
import { saveSession } from '../services/session'

function Login() {
  const navigate = useNavigate()

  const [nif, setNif] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      const { nif: userNif, token } = await login(nif, password)
      saveSession({ nif: userNif, token })
      navigate('/dashboard')
    } catch (err) {
      setError(
        err.status === 401 ? 'NIF ou mot de passe incorrect.' : err.message,
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-container">
        <p>Connexion à votre compte</p>

        <form onSubmit={handleSubmit}>
          <Input
            id="nif"
            label="Numéro fiscal (NIF)"
            type="text"
            inputMode="numeric"
            autoComplete="username"
            maxLength={13}
            pattern="[0-9]{13}"
            title="13 chiffres"
            value={nif}
            onChange={(event) => setNif(event.target.value)}
            required
          />

          <Input
            id="password"
            label="Mot de passe"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}

          <Button type="submit" disabled={loading}>
            {loading ? 'Connexion…' : 'Se connecter'}
          </Button>
        </form>

        <p>
          Pas encore de compte ? <Link to="/register">Créer un compte</Link>
        </p>
      </div>
    </main>
  )
}

export default Login
