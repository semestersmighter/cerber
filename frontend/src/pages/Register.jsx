import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import Button from '../components/Button'
import Input from '../components/Input'

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

    console.log({ email, password })

    // Plus tard : appel API
    navigate('/')
  }

  return (
    <main className="auth-page">
      <div className="auth-container">
        <h1>Créer un compte</h1>
        <p>Rejoignez Cerber</p>

        <form onSubmit={handleSubmit}>
          <Input
            id="email"
            label="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <Input
            id="password"
            label="Mot de passe"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <Input
            id="confirmPassword"
            label="Confirmer le mot de passe"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />

          <Button type="submit">Créer mon compte</Button>
        </form>

        <p>
          Déjà un compte ? <Link to="/">Se connecter</Link>
        </p>
      </div>
    </main>
  )
}

export default Register
