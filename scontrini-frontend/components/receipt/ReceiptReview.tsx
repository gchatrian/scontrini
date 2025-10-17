'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2, AlertCircle, Edit2, Trash2 } from 'lucide-react'
import { ParsedReceipt, ReceiptItem } from '@/types/receipt'

interface ReceiptReviewProps {
  parsedData: ParsedReceipt
  imageUrl: string
  ocrConfidence?: number
  onConfirm: (data: ParsedReceipt) => void
  onCancel: () => void
}

export function ReceiptReview({
  parsedData,
  imageUrl,
  ocrConfidence = 0,
  onConfirm,
  onCancel
}: ReceiptReviewProps) {
  // Assicurati che parsedData abbia valori di default
  const safeData = {
    store_name: parsedData?.store_name || '',
    store_address: parsedData?.store_address || '',
    receipt_date: parsedData?.receipt_date || '',
    receipt_time: parsedData?.receipt_time || '',
    total_amount: parsedData?.total_amount || 0,
    tax_amount: parsedData?.tax_amount || 0,
    payment_method: parsedData?.payment_method || '',
    items: parsedData?.items || []
  }

  const [editedData, setEditedData] = useState<ParsedReceipt>(safeData)
  const [editingItem, setEditingItem] = useState<number | null>(null)

  const updateField = (field: keyof ParsedReceipt, value: any) => {
    setEditedData(prev => ({ ...prev, [field]: value }))
  }

  const updateItem = (index: number, field: keyof ReceiptItem, value: any) => {
    const newItems = [...editedData.items]
    newItems[index] = { ...newItems[index], [field]: value }
    setEditedData(prev => ({ ...prev, items: newItems }))
  }

  const removeItem = (index: number) => {
    const newItems = editedData.items.filter((_, i) => i !== index)
    setEditedData(prev => ({ ...prev, items: newItems }))
  }

  const addItem = () => {
    const newItem: ReceiptItem = {
      raw_product_name: '',
      quantity: 1,
      unit_price: 0,
      total_price: 0
    }
    setEditedData(prev => ({ ...prev, items: [...prev.items, newItem] }))
    setEditingItem(editedData.items.length)
  }

  const handleConfirm = () => {
    onConfirm(editedData)
  }

  const confidenceBadge = ocrConfidence >= 0.8 ? (
    <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
      <CheckCircle2 className="w-3 h-3 mr-1" />
      Confidenza Alta ({(ocrConfidence * 100).toFixed(0)}%)
    </Badge>
  ) : (
    <Badge variant="secondary">
      <AlertCircle className="w-3 h-3 mr-1" />
      Confidenza Media ({(ocrConfidence * 100).toFixed(0)}%)
    </Badge>
  )

  return (
    <div className="space-y-6">
      {/* Header con Badge */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle>Verifica i Dati</CardTitle>
              <CardDescription>
                Controlla e correggi eventuali errori prima di salvare
              </CardDescription>
            </div>
            {confidenceBadge}
          </div>
        </CardHeader>
      </Card>

      {/* Anteprima Immagine */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Immagine Scontrino</CardTitle>
        </CardHeader>
        <CardContent>
          <img
            src={imageUrl}
            alt="Scontrino"
            className="w-full h-auto max-h-64 object-contain rounded-lg border"
          />
        </CardContent>
      </Card>

      {/* Dati Generali */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Informazioni Generali</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="store_name">Negozio</Label>
              <Input
                id="store_name"
                value={editedData.store_name || ''}
                onChange={(e) => updateField('store_name', e.target.value)}
                placeholder="Nome negozio"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="receipt_date">Data</Label>
              <Input
                id="receipt_date"
                type="date"
                value={editedData.receipt_date || ''}
                onChange={(e) => updateField('receipt_date', e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="store_address">Indirizzo</Label>
            <Input
              id="store_address"
              value={editedData.store_address || ''}
              onChange={(e) => updateField('store_address', e.target.value)}
              placeholder="Indirizzo negozio"
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="receipt_time">Ora</Label>
              <Input
                id="receipt_time"
                type="time"
                value={editedData.receipt_time || ''}
                onChange={(e) => updateField('receipt_time', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="total_amount">Totale (€)</Label>
              <Input
                id="total_amount"
                type="number"
                step="0.01"
                value={editedData.total_amount || 0}
                onChange={(e) => updateField('total_amount', parseFloat(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="payment_method">Pagamento</Label>
              <Input
                id="payment_method"
                value={editedData.payment_method || ''}
                onChange={(e) => updateField('payment_method', e.target.value)}
                placeholder="es. Carta"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Lista Prodotti */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">
              Prodotti ({editedData.items.length})
            </CardTitle>
            <Button variant="outline" size="sm" onClick={addItem}>
              Aggiungi Prodotto
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {editedData.items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              Nessun prodotto trovato. Aggiungi manualmente.
            </div>
          ) : (
            editedData.items.map((item, index) => (
              <div
                key={index}
                className="p-4 border rounded-lg space-y-3 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 space-y-2">
                    <Input
                      value={item.raw_product_name}
                      onChange={(e) => updateItem(index, 'raw_product_name', e.target.value)}
                      placeholder="Nome prodotto"
                      className="font-medium"
                    />
                    <div className="grid grid-cols-3 gap-2">
                      <Input
                        type="number"
                        step="0.01"
                        value={item.quantity}
                        onChange={(e) => {
                          const qty = parseFloat(e.target.value)
                          updateItem(index, 'quantity', qty)
                          updateItem(index, 'total_price', qty * item.unit_price)
                        }}
                        placeholder="Qtà"
                      />
                      <Input
                        type="number"
                        step="0.01"
                        value={item.unit_price}
                        onChange={(e) => {
                          const price = parseFloat(e.target.value)
                          updateItem(index, 'unit_price', price)
                          updateItem(index, 'total_price', item.quantity * price)
                        }}
                        placeholder="€ Cad."
                      />
                      <Input
                        type="number"
                        step="0.01"
                        value={item.total_price}
                        onChange={(e) => updateItem(index, 'total_price', parseFloat(e.target.value))}
                        placeholder="€ Tot."
                      />
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeItem(index)}
                    className="ml-2 text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <Card>
        <CardFooter className="flex justify-between pt-6">
          <Button variant="outline" onClick={onCancel}>
            Annulla
          </Button>
          <Button onClick={handleConfirm} size="lg">
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Conferma e Salva
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}