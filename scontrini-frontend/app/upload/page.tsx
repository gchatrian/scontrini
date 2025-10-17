'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { useHousehold } from '@/hooks/useHousehold'
import { ReceiptUploader } from '@/components/receipt/ReceiptUploader'
import { ReceiptProcessor } from '@/components/receipt/ReceiptProcessor'
import { ReceiptReview } from '@/components/receipt/ReceiptReview'
import { uploadReceiptImage } from '@/lib/supabase/storage'
import { UploadStep, ParsedReceipt, ProcessReceiptResponse } from '@/types/receipt'
import { ChevronLeft, Upload, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

export default function UploadPage() {
  const router = useRouter()
  const { user } = useAuth()
  const { household } = useHousehold()
  
  const [currentStep, setCurrentStep] = useState<UploadStep>('upload')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [imageUrl, setImageUrl] = useState<string>('')
  const [imagePath, setImagePath] = useState<string>('')
  const [processedData, setProcessedData] = useState<ProcessReceiptResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const handleFileSelected = async (file: File) => {
    if (!user) {
      setError('Devi essere autenticato per caricare scontrini')
      return
    }

    if (!household) {
      setError('Nessun household trovato. Crea o seleziona un household.')
      return
    }

    console.log('Upload starting with:', {
      userId: user.id,
      householdId: household.id,
      userEmail: user.email
    })

    setSelectedFile(file)
    setUploading(true)
    setError(null)

    try {
      // Upload a Supabase Storage
      const result = await uploadReceiptImage(file, user.id)

      if (!result.success) {
        throw new Error(result.error || 'Errore durante upload')
      }

      console.log('Upload successful:', result.url)

      setImageUrl(result.url!)
      setImagePath(result.path!)
      
      // Passa allo step di processing
      setCurrentStep('processing')
      setUploading(false)

    } catch (err: any) {
      console.error('Upload error:', err)
      setError(err.message || 'Errore durante upload')
      setUploading(false)
    }
  }

  const handleProcessingComplete = (data: ProcessReceiptResponse) => {
    console.log('Processing completed:', data)
    console.log('Parsed data:', data.parsed_data)
    setProcessedData(data)
    setCurrentStep('review')
  }

  const handleProcessingError = (errorMessage: string) => {
    setError(errorMessage)
    setCurrentStep('upload')
  }

  const handleConfirm = async (editedData: ParsedReceipt) => {
    try {
      // Qui potresti fare una chiamata API per aggiornare i dati
      // se l'utente ha fatto modifiche
      
      setCurrentStep('complete')
      
      // Redirect dopo 2 secondi
      setTimeout(() => {
        router.push('/receipts')
      }, 2000)

    } catch (err: any) {
      console.error('Confirm error:', err)
      setError(err.message || 'Errore durante salvataggio')
    }
  }

  const handleCancel = () => {
    setCurrentStep('upload')
    setSelectedFile(null)
    setImageUrl('')
    setImagePath('')
    setProcessedData(null)
    setError(null)
  }

  return (
    <div className="container max-w-4xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm" className="mb-4">
            <ChevronLeft className="w-4 h-4 mr-2" />
            Torna alla Dashboard
          </Button>
        </Link>
        
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Nuovo Scontrino</h1>
            <p className="text-muted-foreground mt-2">
              Carica e digitalizza il tuo scontrino
            </p>
          </div>
          
          {/* Step Indicator */}
          <div className="hidden md:flex items-center space-x-2">
            <StepBadge
              label="Upload"
              active={currentStep === 'upload'}
              completed={['processing', 'review', 'complete'].includes(currentStep)}
              icon={<Upload className="w-4 h-4" />}
            />
            <div className="w-8 h-0.5 bg-muted" />
            <StepBadge
              label="Processing"
              active={currentStep === 'processing'}
              completed={['review', 'complete'].includes(currentStep)}
              icon={<div className="w-4 h-4 border-2 border-current rounded-full" />}
            />
            <div className="w-8 h-0.5 bg-muted" />
            <StepBadge
              label="Review"
              active={currentStep === 'review'}
              completed={currentStep === 'complete'}
              icon={<div className="w-4 h-4 border-2 border-current rounded-full" />}
            />
            <div className="w-8 h-0.5 bg-muted" />
            <StepBadge
              label="Completo"
              active={currentStep === 'complete'}
              completed={false}
              icon={<CheckCircle className="w-4 h-4" />}
            />
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p className="font-medium">Si è verificato un errore</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Content based on Step */}
      <div>
        {currentStep === 'upload' && (
          <ReceiptUploader
            onFileSelected={handleFileSelected}
            loading={uploading}
          />
        )}

        {currentStep === 'processing' && imageUrl && household && user && (
          <ReceiptProcessor
            imageUrl={imageUrl}
            householdId={household.id}
            userId={user.id}
            onComplete={handleProcessingComplete}
            onError={handleProcessingError}
          />
        )}

        {currentStep === 'review' && processedData && processedData.parsed_data && (
          <ReceiptReview
            parsedData={processedData.parsed_data}
            imageUrl={imageUrl}
            ocrConfidence={processedData.ocr_confidence}
            onConfirm={handleConfirm}
            onCancel={handleCancel}
          />
        )}

        {currentStep === 'review' && processedData && !processedData.parsed_data && (
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">
              Errore nel parsing dei dati dello scontrino.
            </p>
            <Button onClick={handleCancel}>
              Riprova
            </Button>
          </div>
        )}

        {currentStep === 'complete' && (
          <div className="text-center py-12">
            <div className="mb-6">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Scontrino Salvato!</h2>
            <p className="text-muted-foreground mb-6">
              Il tuo scontrino è stato elaborato e salvato con successo.
            </p>
            <p className="text-sm text-muted-foreground">
              Reindirizzamento allo storico...
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// Helper Component: Step Badge
function StepBadge({
  label,
  active,
  completed,
  icon
}: {
  label: string
  active: boolean
  completed: boolean
  icon: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center">
      <div
        className={`
          w-10 h-10 rounded-full flex items-center justify-center mb-2 transition-colors
          ${completed ? 'bg-green-500 text-white' : ''}
          ${active && !completed ? 'bg-primary text-white' : ''}
          ${!active && !completed ? 'bg-muted text-muted-foreground' : ''}
        `}
      >
        {icon}
      </div>
      <span
        className={`
          text-xs font-medium
          ${active ? 'text-primary' : 'text-muted-foreground'}
        `}
      >
        {label}
      </span>
    </div>
  )
}