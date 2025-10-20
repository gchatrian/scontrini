// types/receipt.ts
/**
 * Types per gestione scontrini con prodotti normalizzati
 */

// ===================================
// STORE TYPES
// ===================================

export interface StoreData {
  id: string
  name: string
  chain?: string
  branch_name?: string
  vat_number?: string
  company_name?: string
  address_full?: string
  address_city?: string
  address_province?: string
  is_mock: boolean
}

// ===================================
// NORMALIZED PRODUCT TYPES
// ===================================

export interface NormalizedProduct {
  id: string
  canonical_name: string
  brand: string | null
  category: string
  subcategory: string | null
  size: string
  unit_type: string
  confidence: number
  pending_review: boolean
  from_cache?: boolean
}

// ===================================
// RECEIPT ITEM TYPES
// ===================================

export interface ReceiptItem {
  raw_product_name: string
  quantity: number
  unit_price: number
  total_price: number
  category?: string
}

export interface ReceiptItemWithNormalized extends ReceiptItem {
  // ID per tracking
  id?: string
  receipt_item_id?: string
  
  // Dati normalizzati
  normalized_product_id?: string
  canonical_name?: string
  brand?: string | null
  subcategory?: string | null
  size?: string
  unit_type?: string
  confidence?: number
  pending_review?: boolean
  from_cache?: boolean
  user_verified?: boolean
}

// ===================================
// PARSED RECEIPT
// ===================================

export interface ParsedReceipt {
  // Store info
  store_id?: string
  store_name?: string
  company_name?: string
  vat_number?: string
  store_address?: string
  store_data?: StoreData
  
  // Receipt info
  receipt_date?: string
  receipt_time?: string
  total_amount?: number
  tax_amount?: number
  payment_method?: string
  discount_amount?: number
  
  // Items con normalizzazione
  items: ReceiptItemWithNormalized[]
}

// ===================================
// API REQUEST/RESPONSE
// ===================================

export interface ProcessReceiptRequest {
  household_id: string
  uploaded_by: string
  image_url: string
}

export interface ProcessReceiptResponse {
  success: boolean
  receipt_id?: string
  parsed_data?: ParsedReceipt
  ocr_confidence?: number
  error?: string
  message?: string
}

export interface UpdateProductReviewRequest {
  canonical_name: string
  brand?: string | null
  category: string
  subcategory?: string | null
  size?: string
  unit_type?: string
}

export interface UpdateProductReviewResponse {
  success: boolean
  message?: string
  normalized_product_id?: string
}

// ===================================
// RECEIPT ENTITY
// ===================================

export interface Receipt {
  id: string
  household_id: string
  uploaded_by: string
  image_url: string
  store_id?: string
  store_name?: string
  store_address?: string
  receipt_date?: string
  receipt_time?: string
  total_amount?: number
  tax_amount?: number
  payment_method?: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  ocr_confidence?: number
  created_at: string
  updated_at: string
}

// ===================================
// UI HELPER TYPES
// ===================================

export type UploadStep = 'upload' | 'processing' | 'review' | 'complete'

export interface ProductEditState {
  receipt_item_id: string
  canonical_name: string
  brand: string
  category: string
  subcategory: string
  size: string
  unit_type: string
}