// components/receipt/ProductReviewItem.tsx
'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { 
  AlertCircle, 
  CheckCircle2, 
  Edit2, 
  Save, 
  X,
  Package,
  Tag,
  Ruler,
  TrendingUp
} from 'lucide-react'
import { ReceiptItemWithNormalized } from '@/types/receipt'

interface ProductReviewItemProps {
  item: ReceiptItemWithNormalized
  editable: boolean
  highlighted?: boolean
  onUpdate?: (itemId: string, updates: any) => void
}

export function ProductReviewItem({
  item,
  editable,
  highlighted = false,
  onUpdate
}: ProductReviewItemProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState({
    raw_product_name: item.raw_product_name || '',
    canonical_name: item.canonical_name || '',
    brand: item.brand || '',
    category: item.category || '',
    subcategory: item.subcategory || '',
    size: item.size || '',
    unit_type: item.unit_type || '',
    quantity: item.quantity || 1,
    unit_price: item.unit_price || 0,
    total_price: item.total_price || 0
  })

  // Usa sempre i valori dalle props, non stato locale
  const isPendingReview = item.pending_review || false
  const confidence = item.confidence || 0
  const fromCache = item.from_cache || false
  const userVerified = item.user_verified || false
  
  // Sincronizza editData quando le props cambiano
  useEffect(() => {
    setEditData({
      raw_product_name: item.raw_product_name || '',
      canonical_name: item.canonical_name || '',
      brand: item.brand || '',
      category: item.category || '',
      subcategory: item.subcategory || '',
      size: item.size || '',
      unit_type: item.unit_type || '',
      quantity: item.quantity || 1,
      unit_price: item.unit_price || 0,
      total_price: item.total_price || 0
    })
  }, [item])

  // Mostra pulsante "Conferma senza modifiche" solo se:
  // - È in pending review
  // - Non è stato ancora confermato dall'utente
  // - Non è in modalità editing
  const showConfirmButton = isPendingReview && !userVerified && !isEditing
  
  console.log('🔍 Visibilità pulsante per', item.raw_product_name, {
    isPendingReview,
    userVerified,
    isEditing,
    showConfirmButton
  })

  const handleSave = () => {
    console.log('💾 Salva cliccato!', {
      itemId: item.receipt_item_id,
      hasOnUpdate: !!onUpdate,
      currentUserVerified: userVerified,
      currentPendingReview: isPendingReview
    })
    
    if (onUpdate && item.receipt_item_id) {
      onUpdate(item.receipt_item_id, {
        ...editData,
        user_verified: true,
        pending_review: false,
        confidence: 1.0
      })
    }
    setIsEditing(false)
  }

  const handleConfirmWithoutChanges = () => {
    console.log('🟢 Conferma senza modifiche cliccata!', {
      itemId: item.receipt_item_id,
      hasOnUpdate: !!onUpdate,
      currentUserVerified: userVerified,
      currentPendingReview: isPendingReview
    })
    
    if (onUpdate && item.receipt_item_id) {
      onUpdate(item.receipt_item_id, {
        ...editData,
        user_verified: true,
        pending_review: false,
        confidence: 1.0
      })
    }
  }

  const handleCancel = () => {
    setEditData({
      raw_product_name: item.raw_product_name || '',
      canonical_name: item.canonical_name || '',
      brand: item.brand || '',
      category: item.category || '',
      subcategory: item.subcategory || '',
      size: item.size || '',
      unit_type: item.unit_type || '',
      quantity: item.quantity || 1,
      unit_price: item.unit_price || 0,
      total_price: item.total_price || 0
    })
    setIsEditing(false)
  }

  // Determina colore badge confidence
  const getConfidenceBadge = () => {
    if (userVerified) {
      return (
        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300">
          <CheckCircle2 className="w-3 h-3 mr-1" />
          Verificato dall'utente
        </Badge>
      )
    }
    
    if (fromCache) {
      return (
        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300">
          <CheckCircle2 className="w-3 h-3 mr-1" />
          Cache
        </Badge>
      )
    }
    
    if (confidence >= 0.8) {
      return (
        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300">
          Alta ({(confidence * 100).toFixed(0)}%)
        </Badge>
      )
    } else if (confidence >= 0.6) {
      return (
        <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
          Media ({(confidence * 100).toFixed(0)}%)
        </Badge>
      )
    } else {
      return (
        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-300">
          Bassa ({(confidence * 100).toFixed(0)}%)
        </Badge>
      )
    }
  }

  return (
    <Card className={`
      ${highlighted ? 'border-2 border-yellow-400 bg-yellow-50' : ''}
      ${isPendingReview && !highlighted && !userVerified ? 'border-yellow-300' : ''}
      ${userVerified ? 'border-blue-300 bg-blue-50' : ''}
    `}>
      <CardContent className="pt-4 space-y-3">
        {/* Header con nome grezzo e confidence */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
              Descrizione Originale
            </p>
            <p className="font-mono text-sm font-medium">
              {item.raw_product_name}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            {getConfidenceBadge()}
            {isPendingReview && (
              <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-400">
                <AlertCircle className="w-3 h-3 mr-1" />
                Revisione Richiesta
              </Badge>
            )}
          </div>
        </div>

        {/* Divider */}
        <div className="border-t" />

        {/* Dati Normalizzati */}
        {!isEditing ? (
          <div className="space-y-2">
            {/* Nome Canonico */}
            <div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <Package className="w-3 h-3" />
                <span className="font-medium uppercase">Prodotto Normalizzato</span>
              </div>
              <p className="text-base font-semibold ml-5">
                {item.canonical_name || item.raw_product_name}
              </p>
            </div>

            {/* Dettagli in griglia */}
            <div className="grid grid-cols-2 gap-3 ml-5">
              {/* Brand */}
              {item.brand && (
                <div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground mb-0.5">
                    <Tag className="w-3 h-3" />
                    <span>Brand</span>
                  </div>
                  <p className="text-sm font-medium">{item.brand}</p>
                </div>
              )}

              {/* Categoria */}
              {item.category && (
                <div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground mb-0.5">
                    <TrendingUp className="w-3 h-3" />
                    <span>Categoria</span>
                  </div>
                  <p className="text-sm">{item.category}</p>
                  {item.subcategory && (
                    <p className="text-xs text-muted-foreground">{item.subcategory}</p>
                  )}
                </div>
              )}

              {/* Formato - FIX: mostra size senza duplicare unit_type */}
              {item.size && (
                <div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground mb-0.5">
                    <Ruler className="w-3 h-3" />
                    <span>Formato</span>
                  </div>
                  <p className="text-sm font-medium">
                    {item.size}
                    {item.unit_type && !item.size.includes(item.unit_type) && ` ${item.unit_type}`}
                  </p>
                </div>
              )}

              {/* Quantità */}
              <div>
                <div className="text-xs text-muted-foreground mb-0.5">Quantità</div>
                <p className="text-sm font-medium">
                  {item.quantity}x
                </p>
              </div>

              {/* Prezzo Unitario */}
              <div>
                <div className="text-xs text-muted-foreground mb-0.5">Prezzo Unit.</div>
                <p className="text-sm font-medium">
                  €{item.unit_price.toFixed(2)}
                </p>
              </div>

              {/* Prezzo Totale */}
              <div>
                <div className="text-xs text-muted-foreground mb-0.5">Totale</div>
                <p className="text-sm font-semibold">
                  €{item.total_price.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        ) : (
          // EDIT MODE
          <div className="space-y-3">
            {/* Nome Grezzo - EDITABILE */}
            <div className="space-y-2">
              <Label htmlFor="raw_product_name" className="text-xs">
                Descrizione Originale
              </Label>
              <Input
                id="raw_product_name"
                value={editData.raw_product_name}
                onChange={(e) => setEditData({ ...editData, raw_product_name: e.target.value })}
                placeholder="Come appare sullo scontrino"
                className="font-mono text-xs"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="canonical_name" className="text-xs">
                Nome Prodotto Normalizzato *
              </Label>
              <Input
                id="canonical_name"
                value={editData.canonical_name}
                onChange={(e) => setEditData({ ...editData, canonical_name: e.target.value })}
                placeholder="es. Coca Cola Zero 1.5L"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="brand" className="text-xs">Brand</Label>
                <Input
                  id="brand"
                  value={editData.brand}
                  onChange={(e) => setEditData({ ...editData, brand: e.target.value })}
                  placeholder="es. Coca Cola"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="category" className="text-xs">Categoria *</Label>
                <Input
                  id="category"
                  value={editData.category}
                  onChange={(e) => setEditData({ ...editData, category: e.target.value })}
                  placeholder="es. Bevande"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="size" className="text-xs">Formato</Label>
                <Input
                  id="size"
                  value={editData.size}
                  onChange={(e) => setEditData({ ...editData, size: e.target.value })}
                  placeholder="es. 1.5"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="unit_type" className="text-xs">Unità</Label>
                <Input
                  id="unit_type"
                  value={editData.unit_type}
                  onChange={(e) => setEditData({ ...editData, unit_type: e.target.value })}
                  placeholder="L, ml, kg, g"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="subcategory" className="text-xs">Sottocategoria</Label>
              <Input
                id="subcategory"
                value={editData.subcategory}
                onChange={(e) => setEditData({ ...editData, subcategory: e.target.value })}
                placeholder="es. Bibite Gassate"
              />
            </div>

            {/* Quantità e Prezzi */}
            <div className="border-t pt-3 mt-3">
              <p className="text-xs font-medium text-muted-foreground mb-3">Quantità e Prezzi</p>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="quantity" className="text-xs">Quantità</Label>
                  <Input
                    id="quantity"
                    type="number"
                    step="0.001"
                    min="0"
                    value={editData.quantity}
                    onChange={(e) => {
                      const qty = parseFloat(e.target.value) || 0
                      setEditData({ 
                        ...editData, 
                        quantity: qty,
                        total_price: qty * editData.unit_price
                      })
                    }}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="unit_price" className="text-xs">€ Unitario</Label>
                  <Input
                    id="unit_price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={editData.unit_price}
                    onChange={(e) => {
                      const price = parseFloat(e.target.value) || 0
                      setEditData({ 
                        ...editData, 
                        unit_price: price,
                        total_price: editData.quantity * price
                      })
                    }}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="total_price" className="text-xs">€ Totale</Label>
                  <Input
                    id="total_price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={editData.total_price}
                    onChange={(e) => {
                      const total = parseFloat(e.target.value) || 0
                      setEditData({ 
                        ...editData, 
                        total_price: total,
                        unit_price: editData.quantity > 0 ? total / editData.quantity : 0
                      })
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        {editable && (
          <div className="flex gap-2 pt-2">
            {!isEditing ? (
              <div className="flex gap-2 w-full">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditing(true)}
                  className="flex-1"
                >
                  <Edit2 className="w-4 h-4 mr-2" />
                  Modifica
                </Button>
                {showConfirmButton && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleConfirmWithoutChanges}
                    className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white opacity-90 hover:opacity-100 transition-opacity"
                  >
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Conferma senza modifiche
                  </Button>
                )}
              </div>
            ) : (
              <>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSave}
                  className="flex-1"
                  disabled={!editData.canonical_name || !editData.category}
                >
                  <Save className="w-4 h-4 mr-2" />
                  Salva
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCancel}
                  className="flex-1"
                >
                  <X className="w-4 h-4 mr-2" />
                  Annulla
                </Button>
              </>
            )}
          </div>
        )}

        {/* Sempre editabile anche per prodotti verificati */}
        {!editable && (
          <div className="flex gap-2 pt-2">
            {!isEditing ? (
              <div className="flex gap-2 w-full">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsEditing(true)}
                  className="flex-1 text-xs"
                >
                  <Edit2 className="w-3 h-3 mr-2" />
                  Correggi se necessario
                </Button>
                {showConfirmButton && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleConfirmWithoutChanges}
                    className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white opacity-90 hover:opacity-100 transition-opacity text-xs"
                  >
                    <CheckCircle2 className="w-3 h-3 mr-2" />
                    Conferma senza modifiche
                  </Button>
                )}
              </div>
            ) : (
              <>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSave}
                  className="flex-1"
                  disabled={!editData.canonical_name || !editData.category}
                >
                  <Save className="w-4 h-4 mr-2" />
                  Salva
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCancel}
                  className="flex-1"
                >
                  <X className="w-4 h-4 mr-2" />
                  Annulla
                </Button>
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}