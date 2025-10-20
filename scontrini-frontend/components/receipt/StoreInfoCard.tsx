// components/receipt/StoreInfoCard.tsx
'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Store, MapPin, FileText, Building2, Edit2, Save, X } from 'lucide-react'
import { StoreData } from '@/types/receipt'

interface StoreInfoCardProps {
  storeName?: string
  companyName?: string
  vatNumber?: string
  address?: string
  storeData?: StoreData
  editable?: boolean
  onUpdate?: (storeData: any) => void
}

export function StoreInfoCard({
  storeName,
  companyName,
  vatNumber,
  address,
  storeData,
  editable = true,
  onUpdate
}: StoreInfoCardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState({
    name: storeData?.name || storeName || '',
    company_name: storeData?.company_name || companyName || '',
    vat_number: storeData?.vat_number || vatNumber || '',
    address_full: storeData?.address_full || address || '',
    address_city: storeData?.address_city || '',
    address_province: storeData?.address_province || '',
    address_postal_code: storeData?.address_postal_code || ''
  })

  const handleSave = () => {
    if (onUpdate) {
      onUpdate(editData)
    }
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditData({
      name: storeData?.name || storeName || '',
      company_name: storeData?.company_name || companyName || '',
      vat_number: storeData?.vat_number || vatNumber || '',
      address_full: storeData?.address_full || address || '',
      address_city: storeData?.address_city || '',
      address_province: storeData?.address_province || '',
      address_postal_code: storeData?.address_postal_code || ''
    })
    setIsEditing(false)
  }

  const isMock = storeData?.is_mock || false
  const chain = storeData?.chain
  const branch = storeData?.branch_name

  return (
    <Card className={isMock ? 'border-yellow-300 bg-yellow-50' : ''}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Store className="w-5 h-5" />
            Informazioni Negozio
          </CardTitle>
          <div className="flex gap-2">
            {isMock && (
              <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-300">
                Dati Incompleti
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {!isEditing ? (
          <>
            {/* Nome Negozio */}
            <div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <Store className="w-4 h-4" />
                <span className="font-medium">Nome</span>
              </div>
              <p className="text-base font-semibold ml-6">{editData.name || 'Non specificato'}</p>
              {chain && chain !== editData.name && (
                <p className="text-sm text-muted-foreground ml-6">
                  Catena: {chain}
                </p>
              )}
              {branch && branch !== editData.name && (
                <p className="text-sm text-muted-foreground ml-6">
                  Punto vendita: {branch}
                </p>
              )}
            </div>

            {/* Ragione Sociale */}
            {editData.company_name && (
              <div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <Building2 className="w-4 h-4" />
                  <span className="font-medium">Ragione Sociale</span>
                </div>
                <p className="text-sm ml-6">{editData.company_name}</p>
              </div>
            )}

            {/* Partita IVA */}
            {editData.vat_number && (
              <div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <FileText className="w-4 h-4" />
                  <span className="font-medium">Partita IVA</span>
                </div>
                <p className="text-sm font-mono ml-6">{editData.vat_number}</p>
              </div>
            )}

            {/* Indirizzo */}
            {editData.address_full && (
              <div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <MapPin className="w-4 h-4" />
                  <span className="font-medium">Indirizzo</span>
                </div>
                <p className="text-sm ml-6">{editData.address_full}</p>
                {editData.address_city && editData.address_province && (
                  <p className="text-sm text-muted-foreground ml-6">
                    {editData.address_city} ({editData.address_province})
                    {editData.address_postal_code && ` - ${editData.address_postal_code}`}
                  </p>
                )}
              </div>
            )}

            {/* Warning se mock */}
            {isMock && (
              <div className="mt-4 p-3 bg-yellow-100 border border-yellow-300 rounded-md">
                <p className="text-xs text-yellow-800">
                  ℹ️ Le informazioni del negozio sono incomplete o non disponibili sullo scontrino.
                </p>
              </div>
            )}
          </>
        ) : (
          // EDIT MODE
          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="store_name" className="text-xs">Nome Negozio *</Label>
              <Input
                id="store_name"
                value={editData.name}
                onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                placeholder="es. Esselunga"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="company_name" className="text-xs">Ragione Sociale</Label>
              <Input
                id="company_name"
                value={editData.company_name}
                onChange={(e) => setEditData({ ...editData, company_name: e.target.value })}
                placeholder="es. Esselunga S.p.A."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="vat_number" className="text-xs">Partita IVA</Label>
              <Input
                id="vat_number"
                value={editData.vat_number}
                onChange={(e) => setEditData({ ...editData, vat_number: e.target.value })}
                placeholder="es. 12345678901"
                className="font-mono"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="address_full" className="text-xs">Indirizzo Completo</Label>
              <Input
                id="address_full"
                value={editData.address_full}
                onChange={(e) => setEditData({ ...editData, address_full: e.target.value })}
                placeholder="es. Via Roma 123"
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <Label htmlFor="address_city" className="text-xs">Città</Label>
                <Input
                  id="address_city"
                  value={editData.address_city}
                  onChange={(e) => setEditData({ ...editData, address_city: e.target.value })}
                  placeholder="Milano"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="address_province" className="text-xs">Prov.</Label>
                <Input
                  id="address_province"
                  value={editData.address_province}
                  onChange={(e) => setEditData({ ...editData, address_province: e.target.value })}
                  placeholder="MI"
                  maxLength={2}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="address_postal_code" className="text-xs">CAP</Label>
                <Input
                  id="address_postal_code"
                  value={editData.address_postal_code}
                  onChange={(e) => setEditData({ ...editData, address_postal_code: e.target.value })}
                  placeholder="20100"
                  maxLength={5}
                />
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        {editable && (
          <div className="flex gap-2 pt-3 border-t mt-3">
            {!isEditing ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditing(true)}
                className="w-full"
              >
                <Edit2 className="w-4 h-4 mr-2" />
                Modifica Negozio
              </Button>
            ) : (
              <>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSave}
                  className="flex-1"
                  disabled={!editData.name}
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
}// components/receipt/StoreInfoCard.tsx
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Store, MapPin, FileText, Building2 } from 'lucide-react'
import { StoreData } from '@/types/receipt'

interface StoreInfoCardProps {
  storeName?: string
  companyName?: string
  vatNumber?: string
  address?: string
  storeData?: StoreData
}

export function StoreInfoCard({
  storeName,
  companyName,
  vatNumber,
  address,
  storeData
}: StoreInfoCardProps) {
  // Usa storeData se disponibile, altrimenti props individuali
  const name = storeData?.name || storeName || 'Negozio Sconosciuto'
  const company = storeData?.company_name || companyName
  const vat = storeData?.vat_number || vatNumber
  const addr = storeData?.address_full || address
  const isMock = storeData?.is_mock || false
  const chain = storeData?.chain
  const branch = storeData?.branch_name

  return (
    <Card className={isMock ? 'border-yellow-300 bg-yellow-50' : ''}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Store className="w-5 h-5" />
            Informazioni Negozio
          </CardTitle>
          {isMock && (
            <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-300">
              Dati Incompleti
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Nome Negozio */}
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Store className="w-4 h-4" />
            <span className="font-medium">Nome</span>
          </div>
          <p className="text-base font-semibold ml-6">{name}</p>
          {chain && chain !== name && (
            <p className="text-sm text-muted-foreground ml-6">
              Catena: {chain}
            </p>
          )}
          {branch && branch !== name && (
            <p className="text-sm text-muted-foreground ml-6">
              Punto vendita: {branch}
            </p>
          )}
        </div>

        {/* Ragione Sociale */}
        {company && (
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Building2 className="w-4 h-4" />
              <span className="font-medium">Ragione Sociale</span>
            </div>
            <p className="text-sm ml-6">{company}</p>
          </div>
        )}

        {/* Partita IVA */}
        {vat && (
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <FileText className="w-4 h-4" />
              <span className="font-medium">Partita IVA</span>
            </div>
            <p className="text-sm font-mono ml-6">{vat}</p>
          </div>
        )}

        {/* Indirizzo */}
        {addr && (
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <MapPin className="w-4 h-4" />
              <span className="font-medium">Indirizzo</span>
            </div>
            <p className="text-sm ml-6">{addr}</p>
            {storeData?.address_city && storeData?.address_province && (
              <p className="text-sm text-muted-foreground ml-6">
                {storeData.address_city} ({storeData.address_province})
                {storeData.address_postal_code && ` - ${storeData.address_postal_code}`}
              </p>
            )}
          </div>
        )}

        {/* Warning se mock */}
        {isMock && (
          <div className="mt-4 p-3 bg-yellow-100 border border-yellow-300 rounded-md">
            <p className="text-xs text-yellow-800">
              ℹ️ Le informazioni del negozio sono incomplete o non disponibili sullo scontrino.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}