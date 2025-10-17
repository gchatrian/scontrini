// types/receipt.ts
/**
 * Types per gestione scontrini
 */

export interface ReceiptItem {
  raw_product_name: string
  quantity: number
  unit_price: number
  total_price: number
  category?: string
}

export interface ParsedReceipt {
  store_name?: string
  store_address?: string
  receipt_date?: string
  receipt_time?: string
  total_amount?: number
  tax_amount?: number
  payment_method?: string
  items: ReceiptItem[]
}

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

export interface Receipt {
  id: string
  household_id: string
  uploaded_by: string
  image_url: string
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

export type UploadStep = 'upload' | 'processing' | 'review' | 'complete'