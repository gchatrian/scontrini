import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Receipt } from 'lucide-react'

export default function ReceiptsPage() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Storico Scontrini</h1>
        <p className="text-muted-foreground mt-2">
          Visualizza e gestisci tutti i tuoi scontrini
        </p>
      </div>

      <Card className="border-dashed border-2">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
            <Receipt className="h-6 w-6 text-purple-600" />
          </div>
          <CardTitle>Nessuno scontrino</CardTitle>
          <CardDescription>
            Carica il tuo primo scontrino per vederlo qui
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-sm text-muted-foreground">
            Una volta caricati, i tuoi scontrini appariranno qui con filtri e statistiche dettagliate.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}