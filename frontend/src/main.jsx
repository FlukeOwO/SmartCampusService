import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// HashRouter (/#/path): บน cloud เว็บโฮสต์บน Cloud Storage ซึ่งไม่ rewrite ทุก path ไป index.html
import { HashRouter } from 'react-router-dom'
import App from './App.jsx'
import { AuthProvider } from './auth/AuthContext.jsx'
import { DialogProvider } from './components/Dialog.jsx'
import { FlashProvider } from './components/Flash.jsx'
import './styles/style.css'
import './styles/app.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HashRouter>
      <AuthProvider>
        <FlashProvider>
          <DialogProvider>
            <App />
          </DialogProvider>
        </FlashProvider>
      </AuthProvider>
    </HashRouter>
  </StrictMode>,
)
