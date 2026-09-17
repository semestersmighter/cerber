import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import Button from '../components/Button'
import Input from '../components/Input'

function Mfa() {
  const navigate = useNavigate()
  const [code, setCode] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()

    console.log('Code MFA :', code)

    // Plus tard : appel API pour vérifier le code
    navigate('/dashboard')
  }

  return (
    <main className="auth-page">
      <div className="auth-container">
        <h1>Vérification MFA</h1>

        <p>
          Entrez le code à 6 chiffres affiché dans votre application
          d'authentification.
        </p>

        <form onSubmit={handleSubmit}>
          <Input
            id="code"
            label="Code de vérification"
            type="text"
            inputMode="numeric"
            maxLength={6}
            pattern="[0-9]{6}"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            required
          />

          <Button type="submit">Vérifier</Button>
        </form>
      </div>
    </main>
  )
}

export default Mfa
