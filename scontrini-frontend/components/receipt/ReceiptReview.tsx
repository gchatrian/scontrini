'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Check, Edit2, X, AlertCircle, Loader2 } from 'lucide-react'
import { ParsedReceipt, ReceiptItem, ReceiptItemWithNormalized } from '@/types/receipt'

interface ReceiptReviewProps {
  data: ParsedReceipt
  onConfirm: (modifiedData: { modified_products: any[] }) => void
  onCancel: () => void
  loading?: boolean
}

interface EditingItem {
  index: number
  data: ReceiptItemWithNormalized
}


export function ReceiptReview({ data, onConfirm, onCancel, loading = false }: ReceiptReviewProps) {
  const [editedData, setEditedData] = useState<ParsedReceipt>(data)
  const [editingItem, setEditingItem] = useState<EditingItem | null>(null)

  const handleEditItem = (index: number) => {
    setEditingItem({
      index,
      data: { ...editedData.items[index] }
    })
  }

  const handleCancelEdit = () => {
    setEditingItem(null)
  }

  const handleSaveEdit = () => {
    if (!editingItem) return

    // Aggiorna i dati direttamente senza categorizzazione manuale
    const updatedItems = [...editedData.items]
    updatedItems[editingItem.index] = {
      ...editingItem.data,
      user_verified: true,
      pending_review: false
    }
    
    setEditedData({
      ...editedData,
      items: updatedItems
    })

    // Reset stati
    setEditingItem(null)
  }

  const handleConfirmWithoutChanges = (index: number) => {
    const updatedItems = [...editedData.items]
    updatedItems[index] = {
      ...updatedItems[index],
      user_verified: true,
      pending_review: false
    }
    
    setEditedData({
      ...editedData,
      items: updatedItems
    })
  }


  const handleItemChange = (field: keyof ReceiptItemWithNormalized, value: any) => {
    if (!editingItem) return

    let updatedData = {
      ...editingItem.data,
      [field]: value
    }

    // Ricalcola prezzo unitario se viene modificata la quantità
    if (field === 'quantity' && value > 0) {
      updatedData.unit_price = updatedData.total_price / value
    }

    setEditingItem({
      ...editingItem,
      data: updatedData
    })
  }

  const handleConfirmAll = () => {
    if (editingItem) {
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
          item.canonical_name !== original.canonical_name ||
          item.brand !== original.brand ||
          item.size !== original.size ||
          item.unit_type !== original.unit_type ||
          item.quantity !== original.quantity ||
          item.total_price !== original.total_price ||
          item.user_verified !== original.user_verified
        )
      })
      .map(item => ({
        receipt_item_id: item.receipt_item_id || item.id,
        canonical_name: item.canonical_name || item.raw_product_name,
        brand: item.brand,
        size: item.size,
        unit_type: item.unit_type,
        quantity: item.quantity,
        total_price: item.total_price,
        user_verified: item.user_verified
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
                    ${editingItem?.index === index ? 'border-primary bg-primary/5' : ''}
                    ${item.pending_review && !item.user_verified ? 'border-yellow-400 bg-yellow-50' : ''}
                    ${item.user_verified ? 'border-blue-400 bg-blue-50' : ''}
                    ${!editingItem?.index && !item.pending_review && !item.user_verified ? 'hover:border-muted-foreground/50' : ''}
                  `}
                >
                  {editingItem?.index === index ? (
                    // Edit Mode
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="col-span-2">
                          <Label>Nome Prodotto</Label>
                          <Input
                            value={editingItem.data.canonical_name || editingItem.data.raw_product_name}
                            onChange={(e) => handleItemChange('canonical_name', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label>Brand</Label>
                          <Input
                            value={editingItem.data.brand || ''}
                            onChange={(e) => handleItemChange('brand', e.target.value)}
                            placeholder="Brand (opzionale)"
                          />
                        </div>
                        <div>
                          <Label>Size</Label>
                          <Input
                            value={editingItem.data.size || ''}
                            onChange={(e) => handleItemChange('size', e.target.value)}
                            placeholder="es. 500"
                          />
                        </div>
                        <div>
                          <Label>Unità di Misura</Label>
                          <Input
                            value={editingItem.data.unit_type || ''}
                            onChange={(e) => handleItemChange('unit_type', e.target.value)}
                            placeholder="es. ml, g, pz"
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
                          Salva
                        </Button>
                        <Button onClick={handleCancelEdit} variant="outline" size="sm">
                          <X className="w-4 h-4 mr-2" />
                          Annulla
                        </Button>
                      </div>
                    </div>
                  ) : (
                    // View Mode
                    <div className="space-y-3">
                      {/* Confidence Tag sopra il box */}
                      {item.confidence && (
                        <div className="flex justify-end items-center gap-2">
                          {item.user_verified && (
                            <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-300">
                              Verificato dall'utente
                            </Badge>
                          )}
                          <span className="text-xs text-muted-foreground">AI confidence:</span>
                          <Badge 
                            variant={
                              item.confidence >= 0.8 ? "default" :
                              item.confidence >= 0.5 ? "secondary" : "destructive"
                            }
                            className="text-xs"
                          >
                            {`${(item.confidence * 100).toFixed(0)}%`}
                          </Badge>
                        </div>
                      )}

                      {/* Riga originale scontrino (RAW) */}
                      <div className="bg-gray-50 p-2 rounded border-l-4 border-gray-300">
                        <p className="text-xs text-gray-600 uppercase tracking-wide mb-1">Riga Originale</p>
                        <p className="font-mono text-sm text-gray-800">{item.raw_product_name}</p>
                      </div>

                      {/* Dettagli prodotto */}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Prodotto</p>
                          <p className="font-medium text-base">
                            {item.canonical_name || 'Non identificato'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Brand</p>
                          <p className="text-sm text-blue-600 font-medium">
                            {item.brand || 'Non specificato'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Quantità</p>
                          <p className="text-sm font-medium">{item.quantity}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Formato</p>
                          <p className="text-sm font-medium">
                            {item.size && item.unit_type 
                              ? `${item.size} ${item.unit_type}`
                              : item.size || item.unit_type || 'Non specificato'
                            }
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Prezzo Unitario</p>
                          <p className="text-sm font-medium">€{item.unit_price?.toFixed(2) || '0.00'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Prezzo Totale</p>
                          <p className="text-sm font-bold text-green-600">€{item.total_price.toFixed(2)}</p>
                        </div>
                      </div>

                      {/* Pulsanti di azione */}
                      <div className="flex justify-between items-center">
                        <div className="flex gap-2">
                          <Button
                            onClick={() => handleEditItem(index)}
                            variant="ghost"
                            size="sm"
                          >
                            <Edit2 className="w-4 h-4 mr-1" />
                            Modifica
                          </Button>
                          {item.pending_review && !item.user_verified && (
                            <Button
                              onClick={() => handleConfirmWithoutChanges(index)}
                              variant="outline"
                              size="sm"
                              className="bg-green-50 border-green-300 text-green-700 hover:bg-green-100"
                            >
                              <Check className="w-4 h-4 mr-1" />
                              Conferma senza modifiche
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Alert per review manuale */}
                      {item.pending_review && (
                        <Alert className="mt-2">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription className="text-xs">
                            Questo prodotto richiede verifica manuale
                          </AlertDescription>
                        </Alert>
                      )}
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
            disabled={loading || !!editingItem}
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

    </>
  )
}