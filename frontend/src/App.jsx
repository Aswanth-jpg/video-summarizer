import { useState } from 'react'
import './App.css'
import VideoProcessor from './components/VideoProcessor'
import Header from './components/Header'

function App() {
  return (
    <div className="App">
      <Header />
      <main className="main-content">
        <VideoProcessor />
      </main>
    </div>
  )
}

export default App
