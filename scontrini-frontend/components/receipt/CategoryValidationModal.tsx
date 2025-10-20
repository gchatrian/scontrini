'use client'

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Loader2, Check, Edit2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface CategoryValidationModalProps {
  isOpen: boolean
  loading: boolean
  productName: string
  suggestedCategory: string | null
  suggestedSubcategory: string | null
  onConfirm: (category: string, subcategory: string) => void
  onCancel: () => void
}

export function CategoryValidationModal({
  isOpen,
  loading,
  productName,
  suggestedCategory,
  suggestedSubcategory,
  onConfirm,
  onCancel,
}: CategoryValidationModalProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [category, setCategory] = useState('')
  const [subcategory, setSubcategory] = useState('')

  useEffect(() => {
    if (suggestedCategory) {
      setCategory(suggestedCategory)
    }
    if (suggestedSubcategory) {
      setSubcategory(suggestedSubcategory)
    }
  }, [suggestedCategory, suggestedSubcategory])

  const handleConfirm = () => {
    if (!category.trim()) {
      alert('La categoria è obbligatoria')
      return
    }
    onConfirm(category.trim(), subcategory.trim())
  }

  return (
    <Dialog open={isOpen} onOpenChange={onCancel}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Validazione Categorizzazione</DialogTitle>
          <DialogDescription>
            Verifica la categorizzazione proposta per il prodotto modificato
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Product Name */}
          <div>
            <Label className="text-sm text-muted-foreground">Prodotto</Label>
            <p className="font-medium text-lg">{productName}</p>
          </div>

          {loading ? (
            // Loading State
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                Categorizzazione in corso tramite AI...
              </p>
            </div>
          ) : (
            // Results
            <div className="space-y-4">
              <Alert>
                <AlertDescription className="text-sm">
                  L'AI ha analizzato il prodotto modificato e suggerisce questa categorizzazione.
                  Puoi confermare o modificare manualmente.
                </AlertDescription>
              </Alert>

              {isEditing ? (
                // Edit Mode
                <div className="space-y-3">
                  <div>
                    <Label htmlFor="category">Categoria *</Label>
                    <Input
                      id="category"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      placeholder="es. Latticini"
                    />
                  </div>
                  <div>
                    <Label htmlFor="subcategory">Sottocategoria</Label>
                    <Input
                      id="subcategory"
                      value={subcategory}
                      onChange={(e) => setSubcategory(e.target.value)}
                      placeholder="es. Formaggi (opzionale)"
                    />
                  </div>
                  <Button
                    onClick={() => setIsEditing(false)}
                    variant="outline"
                    size="sm"
                    className="w-full"
                  >
                    Annulla Modifiche
                  </Button>
                </div>
              ) : (
                // View Mode
                <div className="space-y-3">
                  <div className="p-4 bg-muted rounded-lg space-y-2">
                    <div>
                      <Label className="text-xs text-muted-foreground">Categoria</Label>
                      <p className="font-medium text-lg">
                        {category || 'Non categorizzato'}
                      </p>
                    </div>
                    {subcategory && (
                      <div>
                        <Label className="text-xs text-muted-foreground">Sottocategoria</Label>
                        <p className="font-medium">
                          {subcategory}
                        </p>
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={() => setIsEditing(true)}
                    variant="outline"
                    size="sm"
                    className="w-full"
                  >
                    <Edit2 className="w-4 h-4 mr-2" />
                    Modifica Manualmente
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            onClick={onCancel}
            variant="outline"
            disabled={loading}
          >
            Annulla
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={loading || !category.trim()}
          >
            <Check className="w-4 h-4 mr-2" />
            Conferma
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}