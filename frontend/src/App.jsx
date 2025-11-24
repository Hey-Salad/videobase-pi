import MultiCameraView from './components/MultiCameraView'

function App() {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Sticky nav with Logo */}
      <header className="sticky top-0 z-40 bg-black/90 backdrop-blur border-b border-white/10 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4">
          <a href="#" className="flex items-center gap-3">
            <img
              src="/heysalad_white_logo.svg"
              alt="HeySalad"
              className="h-12 w-auto"
            />
            <span className="text-xs font-semibold tracking-wide uppercase text-white">
              Videobase Pi
            </span>
          </a>
        </div>
      </header>

      {/* Multi-Camera View */}
      <main className="px-4 pb-8">
        <MultiCameraView />
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto mt-8 text-center text-gray-400 text-sm">
        <p>Powered by Seeedstudio's reCamera & Raspberry Pi</p>
        <p className="mt-2">
          Made with by{' '}
          <a
            href="https://heysalad.io"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 transition-colors"
          >
            HeySalad
          </a>
        </p>
      </footer>
    </div>
  )
}

export default App
