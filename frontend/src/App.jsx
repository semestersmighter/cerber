import './App.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

import Login from './pages/Login'
import Register from './pages/Register'
import Mfa from './pages/Mfa'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/mfa" element={<Mfa />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App