export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gradient-to-b from-blue-50 to-white">
      <div className="text-center space-y-6">
        <h1 className="text-6xl font-bold text-gray-900">
          🧾 Scontrini
        </h1>
        
        <p className="text-xl text-gray-600 max-w-2xl">
          Gestisci i tuoi acquisti, migliora le tue scelte
        </p>
        
        <div className="mt-8 space-y-4">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-2xl font-semibold mb-2">Setup completato! ✅</h2>
            <p className="text-gray-600">
              Frontend Next.js funzionante
            </p>
          </div>
          
          <div className="text-sm text-gray-500 space-y-1">
            <p>📱 Frontend: http://localhost:3000</p>
            <p>🔌 Backend API: http://localhost:8000</p>
            <p>📚 API Docs: http://localhost:8000/docs</p>
          </div>
        </div>
        
        <div className="mt-12 text-sm text-gray-400">
          <p>Task 1 completato - Prossimo: Setup Supabase</p>
        </div>
      </div>
    </main>
  );
}
