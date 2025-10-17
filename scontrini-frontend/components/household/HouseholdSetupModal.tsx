'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'

interface HouseholdSetupModalProps {
  userEmail: string
  onComplete: (householdName: string) => Promise<void>
}

export function HouseholdSetupModal({ userEmail, onComplete }: HouseholdSetupModalProps) {
  const [householdName, setHouseholdName] = useState(getDefaultName(userEmail))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await onComplete(householdName)
    } catch (err: any) {
      setError(err.message || 'Errore nella creazione dell\'household')
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <Card className="w-full max-w-md bg-white shadow-2xl">
        <form onSubmit={handleSubmit}>
          <CardHeader>
            <CardTitle>Benvenuto! 🎉</CardTitle>
            <CardDescription>
              Hai effettuato l'accesso con Google. Prima di continuare, personalizza il nome del tuo gruppo famiglia.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="householdName">Nome Household</Label>
              <Input
                id="householdName"
                placeholder="Casa di Mario"
                value={householdName}
                onChange={(e) => setHouseholdName(e.target.value)}
                required
                disabled={loading}
                autoFocus
                className="bg-white"
              />
              <p className="text-xs text-muted-foreground">
                Questo è il nome del tuo gruppo famiglia. Potrai invitare altri membri in seguito.
              </p>
            </div>
            {error && (
              <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">
                {error}
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Creazione in corso...' : 'Continua'}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}

// Helper per generare nome default da email
function getDefaultName(email: string): string {
  const name = email.split('@')[0]
  const capitalized = name.charAt(0).toUpperCase() + name.slice(1)
  return `Casa di ${capitalized}`
}