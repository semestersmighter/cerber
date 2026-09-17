import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

function Register() {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()

    if (password !== confirmPassword) {
      alert('Les mots de passe ne correspondent pas.')
      return
    }

    console.log({
      email,
      password,
    })

    // Plus tard : appel API
    navigate('/')
  }

  return (
    <main className="auth-page">
      <div className="auth-container">
        <h1>Créer un compte</h1>
        <p>Rejoignez Cerber</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Mot de passe</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">
              Confirmer le mot de passe
            </label>

            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
          </div>

          <button type="submit">
            Créer mon compte
          </button>
        </form>

        <p>
          Déjà un compte ?{' '}
          <Link to="/">
            Se connecter
          </Link>
        </p>
      </div>
    </main>
  )
}

export default Register