'use client'

import { useState, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Upload, Camera, X, Image as ImageIcon } from 'lucide-react'
import { validateImageFile } from '@/lib/supabase/storage'

interface ReceiptUploaderProps {
  onFileSelected: (file: File) => void
  loading?: boolean
}

export function ReceiptUploader({ onFileSelected, loading = false }: ReceiptUploaderProps) {
  const [preview, setPreview] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    setError(null)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFile = (file: File) => {
    const validation = validateImageFile(file)
    
    if (!validation.valid) {
      setError(validation.error || 'File non valido')
      return
    }

    setSelectedFile(file)
    
    // Crea preview
    const reader = new FileReader()
    reader.onloadend = () => {
      setPreview(reader.result as string)
    }
    reader.readAsDataURL(file)
    
    setError(null)
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleRemove = () => {
    setPreview(null)
    setSelectedFile(null)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    if (cameraInputRef.current) cameraInputRef.current.value = ''
  }

  const handleContinue = () => {
    if (selectedFile) {
      onFileSelected(selectedFile)
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Carica Scontrino</CardTitle>
        <CardDescription>
          Scatta una foto o seleziona un'immagine del tuo scontrino
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!preview ? (
          <>
            {/* Drag & Drop Area */}
            <div
              className={`
                border-2 border-dashed rounded-lg p-8 text-center transition-colors
                ${dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
                ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-primary hover:bg-primary/5'}
              `}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => !loading && fileInputRef.current?.click()}
            >
              <ImageIcon className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-lg font-medium mb-2">
                Trascina qui il tuo scontrino
              </p>
              <p className="text-sm text-muted-foreground mb-4">
                oppure clicca per selezionare un file
              </p>
              <p className="text-xs text-muted-foreground">
                Formati supportati: JPG, PNG, HEIC (max 10MB)
              </p>
            </div>

            {/* Buttons */}
            <div className="grid grid-cols-2 gap-4">
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                className="w-full"
              >
                <Upload className="w-4 h-4 mr-2" />
                Seleziona File
              </Button>
              
              <Button
                variant="outline"
                onClick={() => cameraInputRef.current?.click()}
                disabled={loading}
                className="w-full"
              >
                <Camera className="w-4 h-4 mr-2" />
                Scatta Foto
              </Button>
            </div>

            {/* Hidden File Inputs */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/jpg,image/png,image/heic"
              onChange={handleFileInput}
              className="hidden"
              disabled={loading}
            />
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileInput}
              className="hidden"
              disabled={loading}
            />

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">
                {error}
              </div>
            )}
          </>
        ) : (
          <>
            {/* Preview */}
            <div className="relative">
              <img
                src={preview}
                alt="Preview scontrino"
                className="w-full h-auto rounded-lg border-2 border-muted"
              />
              <Button
                variant="destructive"
                size="icon"
                className="absolute top-2 right-2"
                onClick={handleRemove}
                disabled={loading}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* File Info */}
            <div className="bg-muted p-3 rounded-md text-sm">
              <p className="font-medium">{selectedFile?.name}</p>
              <p className="text-muted-foreground">
                {selectedFile && (selectedFile.size / 1024).toFixed(0)} KB
              </p>
            </div>

            {/* Continue Button */}
            <Button
              onClick={handleContinue}
              disabled={loading}
              className="w-full"
              size="lg"
            >
              {loading ? 'Caricamento...' : 'Continua'}
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}