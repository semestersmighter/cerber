import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

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
          Entrez le code à 6 chiffres affiché
          dans votre application d'authentification.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="code">
              Code de vérification
            </label>

            <input
              id="code"
              type="text"
              inputMode="numeric"
              maxLength="6"
              pattern="[0-9]{6}"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              required
            />
          </div>

          <button type="submit">
            Vérifier
          </button>
        </form>
      </div>
    </main>
  )
}

export default Mfa