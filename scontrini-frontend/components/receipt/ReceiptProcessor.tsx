'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, CheckCircle2, XCircle, ScanLine, BrainCircuit, Database } from 'lucide-react'

interface ProcessingStep {
  id: string
  label: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  icon: React.ReactNode
}

interface ReceiptProcessorProps {
  imageUrl: string
  householdId: string
  userId: string
  onComplete: (data: any) => void
  onError: (error: string) => void
}

export function ReceiptProcessor({ imageUrl, householdId, userId, onComplete, onError }: ReceiptProcessorProps) {
  const [steps, setSteps] = useState<ProcessingStep[]>([
    {
      id: 'upload',
      label: 'Upload immagine',
      status: 'completed',
      icon: <CheckCircle2 className="w-5 h-5" />
    },
    {
      id: 'ocr',
      label: 'Estrazione testo (OCR)',
      status: 'pending',
      icon: <ScanLine className="w-5 h-5" />
    },
    {
      id: 'parsing',
      label: 'Analisi con AI',
      status: 'pending',
      icon: <BrainCircuit className="w-5 h-5" />
    },
    {
      id: 'save',
      label: 'Salvataggio dati',
      status: 'pending',
      icon: <Database className="w-5 h-5" />
    }
  ])

  useEffect(() => {
    processReceipt()
  }, [imageUrl])

  const updateStepStatus = (
    stepId: string,
    status: 'pending' | 'processing' | 'completed' | 'error'
  ) => {
    setSteps(prev =>
      prev.map(step =>
        step.id === stepId ? { ...step, status } : step
      )
    )
  }

  const processReceipt = async () => {
    try {
      console.log('Starting processing with:', {
        imageUrl,
        householdId,
        userId
      })

      // Simula step OCR
      updateStepStatus('ocr', 'processing')
      await new Promise(resolve => setTimeout(resolve, 1500))
      updateStepStatus('ocr', 'completed')

      // Simula step AI Parsing
      updateStepStatus('parsing', 'processing')
      await new Promise(resolve => setTimeout(resolve, 2000))
      updateStepStatus('parsing', 'completed')

      // Step Salvataggio
      updateStepStatus('save', 'processing')

      // Chiama backend
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      const requestBody = {
        image_url: imageUrl,
        household_id: householdId,
        uploaded_by: userId
      }

      console.log('API Request:', {
        url: `${apiUrl}/receipts/process`,
        body: requestBody
      })

      const response = await fetch(`${apiUrl}/receipts/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      })

      const data = await response.json()

      console.log('API Response:', {
        status: response.status,
        data
      })

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Errore durante il processing')
      }

      updateStepStatus('save', 'completed')

      // Attendi un attimo per mostrare completamento
      await new Promise(resolve => setTimeout(resolve, 500))

      onComplete(data)

    } catch (error: any) {
      console.error('Processing error:', error)
      
      // Marca step corrente come errore
      const currentStep = steps.find(s => s.status === 'processing')
      if (currentStep) {
        updateStepStatus(currentStep.id, 'error')
      }

      onError(error.message || 'Errore durante il processing dello scontrino')
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Elaborazione in corso...</CardTitle>
        <CardDescription>
          Stiamo processando il tuo scontrino
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {steps.map((step, index) => (
          <div
            key={step.id}
            className="flex items-center space-x-4 p-4 rounded-lg border-2 transition-all"
            style={{
              borderColor:
                step.status === 'completed' ? '#22c55e' :
                step.status === 'processing' ? '#3b82f6' :
                step.status === 'error' ? '#ef4444' :
                '#e5e7eb',
              backgroundColor:
                step.status === 'completed' ? '#f0fdf4' :
                step.status === 'processing' ? '#eff6ff' :
                step.status === 'error' ? '#fef2f2' :
                'transparent'
            }}
          >
            {/* Icon */}
            <div className="flex-shrink-0">
              {step.status === 'processing' ? (
                <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
              ) : step.status === 'completed' ? (
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              ) : step.status === 'error' ? (
                <XCircle className="w-5 h-5 text-red-500" />
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
              )}
            </div>

            {/* Label */}
            <div className="flex-1">
              <p className={`font-medium ${
                step.status === 'completed' ? 'text-green-700' :
                step.status === 'processing' ? 'text-blue-700' :
                step.status === 'error' ? 'text-red-700' :
                'text-muted-foreground'
              }`}>
                {step.label}
              </p>
              {step.status === 'processing' && (
                <p className="text-sm text-muted-foreground mt-1">
                  Elaborazione...
                </p>
              )}
              {step.status === 'error' && (
                <p className="text-sm text-red-600 mt-1">
                  Si è verificato un errore
                </p>
              )}
            </div>

            {/* Step Number */}
            <div className="flex-shrink-0 text-sm font-medium text-muted-foreground">
              {index + 1}/{steps.length}
            </div>
          </div>
        ))}

        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className="bg-primary h-full transition-all duration-500 ease-out"
            style={{
              width: `${(steps.filter(s => s.status === 'completed').length / steps.length) * 100}%`
            }}
          />
        </div>
      </CardContent>
    </Card>
  )
}