import { useState } from 'react'

import Button from '../components/Button'
import Input from '../components/Input'

function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()

    console.log({ email, password })
  }

  return (
    <main className="auth-page">
      <div className="auth-container">
        <p>Connexion à votre compte</p>

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

          <Button type="submit">Se connecter</Button>
        </form>
      </div>
    </main>
  )
}

export default Login
