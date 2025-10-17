'use client'

import { useAuth } from '@/contexts/AuthContext'
import { useHousehold } from '@/hooks/useHousehold'
import { HouseholdSetupModal } from '@/components/household/HouseholdSetupModal'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { Upload, Receipt, Users, TrendingUp } from 'lucide-react'

export default function DashboardPage() {
  const { user } = useAuth()
  const { household, loading, needsSetup, createHousehold } = useHousehold()

  // Estrai nome dall'email o user metadata
  const firstName = user?.user_metadata?.first_name || user?.email?.split('@')[0] || 'Utente'

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Caricamento...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Modal Setup Household per utenti Google al primo accesso */}
      {needsSetup && user && (
        <HouseholdSetupModal
          userEmail={user.email!}
          onComplete={createHousehold}
        />
      )}

      <div className="space-y-8">
        {/* Welcome Section */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Ciao, {firstName}! 👋
          </h1>
          <p className="text-muted-foreground mt-2">
            Benvenuto nella tua dashboard. Ecco cosa puoi fare oggi.
          </p>
          {household && (
            <p className="text-sm text-muted-foreground mt-1">
              📍 Household: <strong>{household.name}</strong>
            </p>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <Link href="/upload">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Carica Scontrino
                </CardTitle>
                <Upload className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">+</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Scatta foto o carica file
                </p>
              </CardContent>
            </Link>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Scontrini Totali
              </CardTitle>
              <Receipt className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
              <p className="text-xs text-muted-foreground mt-1">
                Nessuno scontrino ancora
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Spesa Totale
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">€0.00</div>
              <p className="text-xs text-muted-foreground mt-1">
                Questo mese
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Household
              </CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">1</div>
              <p className="text-xs text-muted-foreground mt-1">
                Solo tu
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Getting Started */}
        <Card>
          <CardHeader>
            <CardTitle>Inizia Subito</CardTitle>
            <CardDescription>
              Segui questi passi per iniziare a gestire i tuoi scontrini
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start space-x-4">
              <div className="bg-primary text-primary-foreground rounded-full w-8 h-8 flex items-center justify-center flex-shrink-0 font-semibold">
                1
              </div>
              <div className="flex-1">
                <h4 className="font-medium mb-1">Carica il tuo primo scontrino</h4>
                <p className="text-sm text-muted-foreground mb-2">
                  Scatta una foto o carica un file del tuo scontrino del supermercato
                </p>
                <Link href="/upload">
                  <Button size="sm">Carica Ora</Button>
                </Link>
              </div>
            </div>

            <div className="flex items-start space-x-4 opacity-50">
              <div className="bg-gray-300 text-gray-600 rounded-full w-8 h-8 flex items-center justify-center flex-shrink-0 font-semibold">
                2
              </div>
              <div className="flex-1">
                <h4 className="font-medium mb-1">Visualizza lo storico</h4>
                <p className="text-sm text-muted-foreground">
                  Analizza i tuoi acquisti e scopri i pattern di spesa
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-4 opacity-50">
              <div className="bg-gray-300 text-gray-600 rounded-full w-8 h-8 flex items-center justify-center flex-shrink-0 font-semibold">
                3
              </div>
              <div className="flex-1">
                <h4 className="font-medium mb-1">Invita membri household</h4>
                <p className="text-sm text-muted-foreground">
                  Condividi la gestione con famiglia o coinquilini
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Info Box */}
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <div className="flex items-start space-x-3">
              <div className="text-2xl">💡</div>
              <div>
                <h4 className="font-medium text-blue-900 mb-1">Suggerimento</h4>
                <p className="text-sm text-blue-800">
                  L'OCR funziona meglio con foto ben illuminate e scontrini piatti. 
                  Evita ombre e angolazioni troppo inclinate per risultati ottimali.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}