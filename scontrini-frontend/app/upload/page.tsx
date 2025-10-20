'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { useHousehold } from '@/hooks/useHousehold'
import { ReceiptUploader } from '@/components/receipt/ReceiptUploader'
import { ReceiptProcessor } from '@/components/receipt/ReceiptProcessor'
import { ReceiptReview } from '@/components/receipt/ReceiptReview'
import { uploadReceiptImage } from '@/lib/supabase/storage'
import { ChevronLeft, Upload, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

type UploadStep = 'upload' | 'processing' | 'review' | 'complete'

interface ProcessReceiptResponse {
  success: boolean
  receipt_id: string
  message: string
  store_name?: string
  receipt_date?: string
  total_amount?: number
  items: any[]
}

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

    setSelectedFile(file)
    setUploading(true)
    setError(null)

    try {
      // Upload a Supabase Storage
      const result = await uploadReceiptImage(file, user.id)

      if (!result.success) {
        throw new Error(result.error || 'Errore durante upload')
      }

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
    setProcessedData(data)
    setCurrentStep('review')
  }

  const handleProcessingError = (errorMessage: string) => {
    setError(errorMessage)
    setCurrentStep('upload')
  }

  const handleConfirm = async (modifiedData: { modified_products: any[] }) => {
    try {
      if (!processedData) {
        throw new Error('No processed data')
      }

      console.log('Confirming receipt with modified products:', modifiedData)

      // Chiamata POST /receipts/confirm
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/receipts/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          receipt_id: processedData.receipt_id,
          modified_products: modifiedData.modified_products
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Errore durante salvataggio')
      }

      const result = await response.json()
      console.log('Confirm result:', result)
      
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
        
        <h1 className="text-3xl font-bold">Carica Scontrino</h1>
        <p className="text-muted-foreground mt-2">
          {currentStep === 'upload' && 'Scatta una foto o seleziona un file'}
          {currentStep === 'processing' && 'Stiamo processando il tuo scontrino...'}
          {currentStep === 'review' && 'Verifica i dati estratti'}
          {currentStep === 'complete' && 'Scontrino salvato con successo!'}
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-6 p-4 bg-destructive/10 text-destructive rounded-lg">
          <p className="font-medium">Errore</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Steps */}
      {currentStep === 'upload' && (
        <ReceiptUploader
          onFileSelected={handleFileSelected}
          loading={uploading}
        />
      )}

      {currentStep === 'processing' && (
        <ReceiptProcessor
          imageUrl={imageUrl}
          householdId={household?.id || ''}
          uploadedBy={user?.id || ''}
          onComplete={handleProcessingComplete}
          onError={handleProcessingError}
        />
      )}

      {currentStep === 'review' && processedData && (
        <ReceiptReview
          data={{
            store_name: processedData.store_name,
            receipt_date: processedData.receipt_date,
            total_amount: processedData.total_amount,
            items: processedData.items
          }}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      )}

      {currentStep === 'complete' && (
        <div className="text-center py-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold mb-2">Scontrino Salvato!</h2>
          <p className="text-muted-foreground mb-4">
            Il tuo scontrino è stato processato e salvato con successo.
          </p>
          <p className="text-sm text-muted-foreground">
            Verrai reindirizzato allo storico...
          </p>
        </div>
      )}
    </div>
  )
}