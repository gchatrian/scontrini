import { LoginForm } from '@/components/auth/LoginForm'

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2">🧾 Scontrini</h1>
          <p className="text-muted-foreground">Gestisci i tuoi acquisti</p>
        </div>
        <LoginForm />
      </div>
    </div>
  )
}