import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gradient-to-b from-blue-50 to-white">
      <div className="text-center space-y-8 max-w-3xl">
        <div className="space-y-4">
          <h1 className="text-6xl font-bold text-gray-900">
            🧾 Scontrini
          </h1>
          <p className="text-2xl text-gray-600">
            Gestisci i tuoi acquisti, migliora le tue scelte
          </p>
        </div>

        <div className="space-y-4 text-lg text-gray-600">
          <p>
            Digitalizza i tuoi scontrini del supermercato con OCR,
            analizza i tuoi pattern di spesa e ottimizza il tuo budget.
          </p>
        </div>

        <div className="flex gap-4 justify-center pt-4">
          <Link href="/signup">
            <Button size="lg" className="text-lg px-8 py-6">
              Inizia Gratis
            </Button>
          </Link>
          <Link href="/login">
            <Button size="lg" variant="outline" className="text-lg px-8 py-6">
              Accedi
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-12">
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="text-3xl mb-2">📸</div>
            <h3 className="font-semibold mb-2">Scatta & Digitalizza</h3>
            <p className="text-sm text-gray-600">
              OCR automatico per estrarre tutti i dati dai tuoi scontrini
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="text-3xl mb-2">🤖</div>
            <h3 className="font-semibold mb-2">AI Intelligente</h3>
            <p className="text-sm text-gray-600">
              Normalizzazione prodotti e analisi automatica dei pattern
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="text-3xl mb-2">👥</div>
            <h3 className="font-semibold mb-2">Condividi</h3>
            <p className="text-sm text-gray-600">
              Gestisci le spese con la tua famiglia o coinquilini
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}