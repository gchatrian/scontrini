'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Check, Edit2, X, AlertCircle, Loader2 } from 'lucide-react'
import { ParsedReceipt, ReceiptItem } from '@/types/receipt'
import { CategoryValidationModal } from '@/components/receipt/CategoryValidationModal'

interface ReceiptReviewProps {
  data: ParsedReceipt
  onConfirm: (editedData: ParsedReceipt) => void
  onCancel: () => void
  loading?: boolean
}

interface EditingItem {
  index: number
  data: ReceiptItem
}

interface PendingCategorization {
  itemIndex: number
  modifiedItem: ReceiptItem
  suggestedCategory: string | null
  suggestedSubcategory: string | null
  loading: boolean
}

export function ReceiptReview({ data, onConfirm, onCancel, loading = false }: ReceiptReviewProps) {
  const [editedData, setEditedData] = useState<ParsedReceipt>(data)
  const [editingItem, setEditingItem] = useState<EditingItem | null>(null)
  const [pendingCategorization, setPendingCategorization] = useState<PendingCategorization | null>(null)

  const handleEditItem = (index: number) => {
    setEditingItem({
      index,
      data: { ...editedData.items[index] }
    })
  }

  const handleCancelEdit = () => {
    setEditingItem(null)
  }

  const handleSaveEdit = async () => {
    if (!editingItem) return

    // Avvia processo di categorizzazione
    setPendingCategorization({
      itemIndex: editingItem.index,
      modifiedItem: editingItem.data,
      suggestedCategory: null,
      suggestedSubcategory: null,
      loading: true
    })

    try {
      // Chiamata LLM per categorizzazione
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/products/categorize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          canonical_name: editingItem.data.normalized_product?.canonical_name || editingItem.data.raw_product_name,
          brand: editingItem.data.normalized_product?.brand,
          size: editingItem.data.normalized_product?.size,
          unit_type: editingItem.data.normalized_product?.unit_type,
        })
      })

      if (!response.ok) {
        throw new Error('Errore durante categorizzazione')
      }

      const result = await response.json()

      // Aggiorna stato con risultati categorizzazione
      setPendingCategorization(prev => prev ? {
        ...prev,
        suggestedCategory: result.category,
        suggestedSubcategory: result.subcategory,
        loading: false
      } : null)

    } catch (error) {
      console.error('Categorization error:', error)
      setPendingCategorization(prev => prev ? {
        ...prev,
        loading: false
      } : null)
      alert('Errore durante la categorizzazione. Riprova.')
    }
  }

  const handleConfirmCategorization = (category: string, subcategory: string) => {
    if (!pendingCategorization || !editingItem) return

    // Applica modifiche con categoria validata
    const updatedItem = {
      ...editingItem.data,
      normalized_product: {
        ...editingItem.data.normalized_product!,
        category,
        subcategory
      }
    }

    const newItems = [...editedData.items]
    newItems[editingItem.index] = updatedItem

    setEditedData({
      ...editedData,
      items: newItems
    })

    // Reset stati
    setEditingItem(null)
    setPendingCategorization(null)
  }

  const handleCancelCategorization = () => {
    setPendingCategorization(null)
    setEditingItem(null)
  }

  const handleItemChange = (field: keyof ReceiptItem, value: any) => {
    if (!editingItem) return

    if (field === 'raw_product_name' || field === 'quantity' || field === 'unit_price' || field === 'total_price') {
      setEditingItem({
        ...editingItem,
        data: {
          ...editingItem.data,
          [field]: value
        }
      })
    } else {
      // Campi nested in normalized_product
      setEditingItem({
        ...editingItem,
        data: {
          ...editingItem.data,
          normalized_product: {
            ...editingItem.data.normalized_product!,
            [field]: value
          }
        }
      })
    }
  }

  const handleConfirmAll = () => {
    if (editingItem || pendingCategorization) {
      alert('Completa la modifica in corso prima di confermare')
      return
    }

    // Identifica solo i prodotti MODIFICATI (confronta con data originale)
    const modifiedProducts = editedData.items
      .filter((item, index) => {
        const original = data.items[index]
        if (!original) return false
        
        // Controlla se qualcosa è cambiato
        return (
          item.normalized_product?.canonical_name !== original.normalized_product?.canonical_name ||
          item.normalized_product?.brand !== original.normalized_product?.brand ||
          item.normalized_product?.size !== original.normalized_product?.size ||
          item.quantity !== original.quantity ||
          item.total_price !== original.total_price
        )
      })
      .map(item => ({
        receipt_item_id: item.id,
        canonical_name: item.normalized_product?.canonical_name || item.raw_product_name,
        brand: item.normalized_product?.brand,
        size: item.normalized_product?.size,
        unit_type: item.normalized_product?.unit_type,
        quantity: item.quantity,
        total_price: item.total_price
      }))

    console.log('Modified products:', modifiedProducts)
    
    // Chiama onConfirm con i prodotti modificati
    onConfirm({ modified_products: modifiedProducts })
  }

  return (
    <>
      <div className="space-y-6">
        {/* Header Info */}
        <Card>
          <CardHeader>
            <CardTitle>Verifica Scontrino</CardTitle>
            <CardDescription>
              Controlla i dati estratti e conferma
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm text-muted-foreground">Negozio</Label>
                <p className="font-medium">{editedData?.store_name || 'Non riconosciuto'}</p>
              </div>
              <div>
                <Label className="text-sm text-muted-foreground">Data</Label>
                <p className="font-medium">
                  {editedData?.receipt_date ? new Date(editedData.receipt_date).toLocaleDateString('it-IT') : 'N/A'}
                </p>
              </div>
              <div>
                <Label className="text-sm text-muted-foreground">Totale</Label>
                <p className="font-medium text-lg">€ {editedData.total_amount?.toFixed(2)}</p>
              </div>
              <div>
                <Label className="text-sm text-muted-foreground">Prodotti</Label>
                <p className="font-medium">{editedData?.items?.length || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Items List */}
        <Card>
          <CardHeader>
            <CardTitle>Prodotti Riconosciuti</CardTitle>
            <CardDescription>
              Clicca su un prodotto per modificarlo
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(editedData?.items || []).map((item, index) => (
                <div
                  key={index}
                  className={`
                    p-4 border rounded-lg transition-all
                    ${editingItem?.index === index ? 'border-primary bg-primary/5' : 'hover:border-muted-foreground/50'}
                  `}
                >
                  {editingItem?.index === index ? (
                    // Edit Mode
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="col-span-2">
                          <Label>Nome Prodotto</Label>
                          <Input
                            value={editingItem.data.normalized_product?.canonical_name || editingItem.data.raw_product_name}
                            onChange={(e) => handleItemChange('canonical_name', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>Brand</Label>
                          <Input
                            value={editingItem.data.normalized_product?.brand || ''}
                            onChange={(e) => handleItemChange('brand', e.target.value)}
                            placeholder="Brand (opzionale)"
                          />
                        </div>
                        <div>
                          <Label>Size</Label>
                          <Input
                            value={editingItem.data.normalized_product?.size || ''}
                            onChange={(e) => handleItemChange('size', e.target.value)}
                            placeholder="es. 500ml"
                          />
                        </div>
                        <div>
                          <Label>Quantità</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={editingItem.data.quantity}
                            onChange={(e) => handleItemChange('quantity', parseFloat(e.target.value))}
                          />
                        </div>
                        <div>
                          <Label>Prezzo Totale</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={editingItem.data.total_price}
                            onChange={(e) => handleItemChange('total_price', parseFloat(e.target.value))}
                          />
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button onClick={handleSaveEdit} size="sm" className="flex-1">
                          <Check className="w-4 h-4 mr-2" />
                          Salva e Categorizza
                        </Button>
                        <Button onClick={handleCancelEdit} variant="outline" size="sm">
                          <X className="w-4 h-4 mr-2" />
                          Annulla
                        </Button>
                      </div>
                    </div>
                  ) : (
                    // View Mode
                    <div className="flex justify-between items-start">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <p className="font-medium">
                            {item.normalized_product?.canonical_name || item.raw_product_name}
                          </p>
                          {item.normalized_product?.brand && (
                            <Badge variant="secondary">{item.normalized_product.brand}</Badge>
                          )}
                        </div>
                        <div className="flex gap-4 text-sm text-muted-foreground">
                          {item.normalized_product?.size && (
                            <span>{item.normalized_product.size}</span>
                          )}
                          <span>Qty: {item.quantity}</span>
                          <span className="font-medium text-foreground">€ {item.total_price.toFixed(2)}</span>
                        </div>
                        {item.product_mapping?.requires_manual_review && (
                          <Alert className="mt-2">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription className="text-xs">
                              Questo prodotto richiede verifica manuale
                            </AlertDescription>
                          </Alert>
                        )}
                      </div>
                      <Button
                        onClick={() => handleEditItem(index)}
                        variant="ghost"
                        size="sm"
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex gap-4">
          <Button
            onClick={handleConfirmAll}
            disabled={loading || !!editingItem || !!pendingCategorization}
            className="flex-1"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Salvataggio...
              </>
            ) : (
              <>
                <Check className="w-4 h-4 mr-2" />
                Conferma Tutto
              </>
            )}
          </Button>
          <Button
            onClick={onCancel}
            variant="outline"
            disabled={loading}
          >
            <X className="w-4 h-4 mr-2" />
            Annulla
          </Button>
        </div>
      </div>

      {/* Category Validation Modal */}
      {pendingCategorization && (
        <CategoryValidationModal
          isOpen={true}
          loading={pendingCategorization.loading}
          productName={pendingCategorization.modifiedItem.normalized_product?.canonical_name || pendingCategorization.modifiedItem.raw_product_name}
          suggestedCategory={pendingCategorization.suggestedCategory}
          suggestedSubcategory={pendingCategorization.suggestedSubcategory}
          onConfirm={handleConfirmCategorization}
          onCancel={handleCancelCategorization}
        />
      )}
    </>
  )
}