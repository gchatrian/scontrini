// lib/supabase/storage.ts
/**
 * Utility per upload file su Supabase Storage
 */

import { createClient } from '@/lib/supabase/client'

const BUCKET_NAME = 'scontrini-receipts'
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/heic']

export interface UploadResult {
  success: boolean
  url?: string
  path?: string
  error?: string
}

export async function uploadReceiptImage(
  file: File,
  userId: string
): Promise<UploadResult> {
  try {
    // Validazione tipo file
    if (!ALLOWED_TYPES.includes(file.type)) {
      return {
        success: false,
        error: 'Formato file non supportato. Usa JPG, PNG o HEIC.'
      }
    }

    // Validazione dimensione
    if (file.size > MAX_FILE_SIZE) {
      return {
        success: false,
        error: 'File troppo grande. Massimo 10MB.'
      }
    }

    const supabase = createClient()

    // Genera nome file unico
    const timestamp = Date.now()
    const randomString = Math.random().toString(36).substring(7)
    const extension = file.name.split('.').pop()
    const fileName = `${userId}/${timestamp}-${randomString}.${extension}`

    // Upload a Supabase Storage
    const { data, error } = await supabase.storage
      .from(BUCKET_NAME)
      .upload(fileName, file, {
        cacheControl: '3600',
        upsert: false
      })

    if (error) {
      console.error('Upload error:', error)
      return {
        success: false,
        error: 'Errore durante upload. Riprova.'
      }
    }

    // Ottieni URL pubblico
    const { data: urlData } = supabase.storage
      .from(BUCKET_NAME)
      .getPublicUrl(data.path)

    return {
      success: true,
      url: urlData.publicUrl,
      path: data.path
    }

  } catch (error) {
    console.error('Unexpected error:', error)
    return {
      success: false,
      error: 'Errore imprevisto durante upload.'
    }
  }
}

export async function deleteReceiptImage(path: string): Promise<boolean> {
  try {
    const supabase = createClient()
    
    const { error } = await supabase.storage
      .from(BUCKET_NAME)
      .remove([path])

    return !error
  } catch (error) {
    console.error('Delete error:', error)
    return false
  }
}

export function validateImageFile(file: File): { valid: boolean; error?: string } {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return {
      valid: false,
      error: 'Formato non supportato. Usa JPG, PNG o HEIC.'
    }
  }

  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: 'File troppo grande. Massimo 10MB.'
    }
  }

  return { valid: true }
}