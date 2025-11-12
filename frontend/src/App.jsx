import { useState } from 'react'
import Chat from './components/Chat'
import './App.css'

function App() {
  return (
    <div className="App">
      <header>
        <h1>PartSelect Assistant</h1>
      </header>
      <main>
        <Chat />
      </main>
    </div>
  )
}

export default App
