// components/receipt/ReceiptReview.tsx
'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  CheckCircle2, 
  AlertCircle, 
  Calendar,
  Clock,
  CreditCard,
  Receipt as ReceiptIcon,
  ChevronRight
} from 'lucide-react'
import { ParsedReceipt } from '@/types/receipt'
import { StoreInfoCard } from './StoreInfoCard'
import { ProductReviewItem } from './ProductReviewItem'

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
  const [editedData, setEditedData] = useState<ParsedReceipt>(parsedData)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Conta prodotti pending review
  const pendingReviewCount = editedData.items.filter(
    item => item.pending_review
  ).length

  // Conta prodotti verificati
  const verifiedCount = editedData.items.filter(
    item => !item.pending_review
  ).length

  const handleStoreUpdate = (storeData: any) => {
    // Aggiorna store nel state locale
    setEditedData({
      ...editedData,
      store_name: storeData.name,
      company_name: storeData.company_name,
      vat_number: storeData.vat_number,
      store_address: storeData.address_full,
      store_data: {
        ...editedData.store_data,
        ...storeData
      }
    })

    // TODO: Implementare chiamata API per salvare store se necessario
    console.log('Store aggiornato:', storeData)
  }

  const handleProductUpdate = async (itemId: string, updates: any) => {
    // Aggiorna item nel state locale
    const updatedItems = editedData.items.map(item => {
      if (item.receipt_item_id === itemId) {
        return {
          ...item,
          ...updates,
          pending_review: false,
          confidence: 1.0
        }
      }
      return item
    })

    setEditedData({
      ...editedData,
      items: updatedItems
    })

    // Chiama API per salvare update
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/receipts/items/${itemId}/review`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates)
      })

      if (!response.ok) {
        throw new Error('Errore durante aggiornamento prodotto')
      }

      const result = await response.json()
      console.log('Prodotto aggiornato:', result)
    } catch (error) {
      console.error('Errore update prodotto:', error)
      // In caso di errore, potresti voler mostrare un toast/notification
    }
  }

  const handleConfirm = async () => {
    if (pendingReviewCount > 0) {
      // Mostra warning se ci sono ancora prodotti da verificare
      const confirmed = window.confirm(
        `Ci sono ancora ${pendingReviewCount} prodotti che richiedono verifica. Vuoi procedere comunque?`
      )
      if (!confirmed) return
    }

    setIsSubmitting(true)
    onConfirm(editedData)
  }

  const confidenceBadge = ocrConfidence >= 0.8 ? (
    <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300">
      <CheckCircle2 className="w-3 h-3 mr-1" />
      Alta qualità ({(ocrConfidence * 100).toFixed(0)}%)
    </Badge>
  ) : ocrConfidence >= 0.6 ? (
    <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
      <AlertCircle className="w-3 h-3 mr-1" />
      Qualità media ({(ocrConfidence * 100).toFixed(0)}%)
    </Badge>
  ) : (
    <Badge variant="outline" className="bg-red-50 text-red-700 border-red-300">
      <AlertCircle className="w-3 h-3 mr-1" />
      Bassa qualità ({(ocrConfidence * 100).toFixed(0)}%)
    </Badge>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <ReceiptIcon className="w-5 h-5" />
              Verifica Scontrino
            </CardTitle>
            {confidenceBadge}
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Controlla i dati estratti e verifica i prodotti contrassegnati.
          </p>
        </CardContent>
      </Card>

      {/* Store Info */}
      <StoreInfoCard
        storeName={editedData.store_name}
        companyName={editedData.company_name}
        vatNumber={editedData.vat_number}
        address={editedData.store_address}
        storeData={editedData.store_data}
        editable={true}
        onUpdate={handleStoreUpdate}
      />

      {/* Receipt Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Dettagli Scontrino</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            {/* Data */}
            {editedData.receipt_date && (
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Data</p>
                  <p className="text-sm font-medium">
                    {new Date(editedData.receipt_date).toLocaleDateString('it-IT')}
                  </p>
                </div>
              </div>
            )}

            {/* Ora */}
            {editedData.receipt_time && (
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Ora</p>
                  <p className="text-sm font-medium">{editedData.receipt_time}</p>
                </div>
              </div>
            )}

            {/* Metodo Pagamento */}
            {editedData.payment_method && (
              <div className="flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Pagamento</p>
                  <p className="text-sm font-medium capitalize">{editedData.payment_method}</p>
                </div>
              </div>
            )}

            {/* Totale */}
            {editedData.total_amount !== undefined && (
              <div className="flex items-center gap-2">
                <ReceiptIcon className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Totale</p>
                  <p className="text-lg font-bold">€{editedData.total_amount.toFixed(2)}</p>
                </div>
              </div>
            )}
          </div>

          {/* Sconto */}
          {editedData.discount_amount && editedData.discount_amount > 0 && (
            <div className="pt-2 border-t">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Sconto applicato</span>
                <span className="text-sm font-medium text-green-600">
                  -€{editedData.discount_amount.toFixed(2)}
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Products Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">
              Prodotti ({editedData.items.length})
            </CardTitle>
            <div className="flex gap-2">
              {pendingReviewCount > 0 && (
                <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-400">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  {pendingReviewCount} da verificare
                </Badge>
              )}
              {verifiedCount > 0 && (
                <Badge variant="outline" className="bg-green-100 text-green-800 border-green-400">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  {verifiedCount} verificati
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Warning se ci sono pending review */}
          {pendingReviewCount > 0 && (
            <div className="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-yellow-900 mb-1">
                    Verifica Richiesta
                  </h4>
                  <p className="text-sm text-yellow-800">
                    Alcuni prodotti richiedono la tua verifica perché il sistema non è riuscito 
                    a identificarli con sufficiente sicurezza. Controlla e correggi i dati se necessario.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Prodotti PENDING REVIEW - mostrati per primi */}
          {editedData.items
            .filter(item => item.pending_review)
            .map((item, idx) => (
              <ProductReviewItem
                key={`pending-${idx}`}
                item={item}
                editable={true}
                highlighted={true}
                onUpdate={handleProductUpdate}
              />
            ))}

          {/* Separator se ci sono entrambi i tipi */}
          {pendingReviewCount > 0 && verifiedCount > 0 && (
            <div className="flex items-center gap-4 my-6">
              <Separator className="flex-1" />
              <span className="text-xs text-muted-foreground uppercase tracking-wide">
                Prodotti Verificati (editabili)
              </span>
              <Separator className="flex-1" />
            </div>
          )}

          {/* Prodotti AUTO-VERIFIED - ORA EDITABILI */}
          {editedData.items
            .filter(item => !item.pending_review)
            .map((item, idx) => (
              <ProductReviewItem
                key={`verified-${idx}`}
                item={item}
                editable={true}
                highlighted={false}
                onUpdate={handleProductUpdate}
              />
            ))}
        </CardContent>
      </Card>

      {/* Summary */}
      <Card className="bg-slate-50 border-slate-200">
        <CardContent className="pt-6">
          <div className="flex justify-between items-center mb-4">
            <span className="text-lg font-semibold">Totale Scontrino</span>
            <span className="text-2xl font-bold">
              €{editedData.total_amount?.toFixed(2) || '0.00'}
            </span>
          </div>
          
          <div className="text-sm text-muted-foreground space-y-1">
            <div className="flex justify-between">
              <span>Prodotti:</span>
              <span className="font-medium">{editedData.items.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Verificati:</span>
              <span className="font-medium text-green-600">{verifiedCount}</span>
            </div>
            {pendingReviewCount > 0 && (
              <div className="flex justify-between">
                <span>Da verificare:</span>
                <span className="font-medium text-yellow-600">{pendingReviewCount}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-4 pt-4 sticky bottom-0 bg-white p-4 border-t">
        <Button
          variant="outline"
          onClick={onCancel}
          disabled={isSubmitting}
          className="flex-1"
        >
          Annulla
        </Button>
        <Button
          onClick={handleConfirm}
          disabled={isSubmitting}
          className="flex-1"
        >
          {isSubmitting ? (
            'Salvataggio...'
          ) : pendingReviewCount > 0 ? (
            <>
              Conferma ({pendingReviewCount} avvisi)
              <ChevronRight className="w-4 h-4 ml-2" />
            </>
          ) : (
            <>
              Conferma e Salva
              <CheckCircle2 className="w-4 h-4 ml-2" />
            </>
          )}
        </Button>
      </div>
    </div>
  )
}