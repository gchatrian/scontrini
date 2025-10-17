import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Upload } from 'lucide-react'

export default function UploadPage() {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Carica Scontrino</h1>
        <p className="text-muted-foreground mt-2">
          Scatta una foto o carica un file del tuo scontrino
        </p>
      </div>

      <Card className="border-dashed border-2">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
            <Upload className="h-6 w-6 text-blue-600" />
          </div>
          <CardTitle>Feature in arrivo</CardTitle>
          <CardDescription>
            La funzionalità di upload sarà disponibile nel Task 7
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <p className="text-sm text-muted-foreground">
            Stiamo lavorando per permetterti di caricare e processare i tuoi scontrini con OCR e AI.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}