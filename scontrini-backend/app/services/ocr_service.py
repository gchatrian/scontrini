"""
OCR Service - Google Cloud Vision API
Estrae testo da immagini di scontrini
"""
import os
from typing import Dict, Optional
from google.cloud import vision
from google.cloud.vision_v1 import types
import io
from PIL import Image
from app.config import settings

# IMPORTANTE: Imposta la variabile d'ambiente PRIMA di inizializzare il client
if settings.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS



class OCRService:
    """Servizio per OCR usando Google Cloud Vision"""
    
    def __init__(self):
        """Inizializza client Vision API"""
        self.client = vision.ImageAnnotatorClient()
    
    def extract_text_from_image(
        self, 
        image_path: str = None,
        image_content: bytes = None
    ) -> Dict[str, any]:
        """
        Estrae testo da un'immagine usando Google Cloud Vision
        
        Args:
            image_path: Path locale all'immagine
            image_content: Contenuto immagine come bytes
            
        Returns:
            Dict con:
                - text: Testo estratto completo
                - confidence: Confidenza media (0-1)
                - words: Lista di parole con bounding boxes
                - success: True se OCR riuscito
                - error: Messaggio errore se fallito
        """
        try:
            # Carica immagine
            if image_path:
                with io.open(image_path, 'rb') as image_file:
                    content = image_file.read()
            elif image_content:
                content = image_content
            else:
                return {
                    "success": False,
                    "error": "Nessuna immagine fornita"
                }
            
            # Crea oggetto immagine Vision
            image = types.Image(content=content)
            
            # Esegui document text detection (migliore per documenti/scontrini)
            response = self.client.document_text_detection(image=image)
            
            # Gestisci errori API
            if response.error.message:
                return {
                    "success": False,
                    "error": f"Vision API error: {response.error.message}"
                }
            
            # Estrai testo completo
            full_text = response.full_text_annotation.text if response.full_text_annotation else ""
            
            # Calcola confidenza media
            confidence = self._calculate_confidence(response)
            
            # Estrai parole con posizioni (utile per debugging)
            words = self._extract_words(response)
            
            return {
                "success": True,
                "text": full_text,
                "confidence": confidence,
                "words": words,
                "raw_response": response  # Per debugging avanzato
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR error: {str(e)}"
            }
    
    def _calculate_confidence(self, response) -> float:
        """Calcola confidenza media dall'OCR"""
        if not response.full_text_annotation:
            return 0.0
        
        # Prende la confidenza media dalle pagine
        pages = response.full_text_annotation.pages
        if not pages:
            return 0.0
        
        total_confidence = 0.0
        count = 0
        
        for page in pages:
            for block in page.blocks:
                if hasattr(block, 'confidence'):
                    total_confidence += block.confidence
                    count += 1
        
        return total_confidence / count if count > 0 else 0.0
    
    def _extract_words(self, response) -> list:
        """Estrae lista di parole con bounding boxes"""
        words = []
        
        if not response.full_text_annotation:
            return words
        
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        # Converte simboli in testo
                        word_text = ''.join([
                            symbol.text for symbol in word.symbols
                        ])
                        
                        words.append({
                            "text": word_text,
                            "confidence": word.confidence if hasattr(word, 'confidence') else None
                        })
        
        return words
    
    def preprocess_image(self, image_path: str, output_path: str = None) -> str:
        """
        Pre-processa immagine per migliorare OCR (opzionale)
        
        Args:
            image_path: Path immagine originale
            output_path: Path dove salvare immagine processata
            
        Returns:
            Path immagine processata
        """
        try:
            # Apri immagine
            img = Image.open(image_path)
            
            # Converti in scala di grigi (migliora OCR)
            img = img.convert('L')
            
            # Aumenta contrasto (opzionale)
            # from PIL import ImageEnhance
            # enhancer = ImageEnhance.Contrast(img)
            # img = enhancer.enhance(2)
            
            # Salva
            if output_path is None:
                output_path = image_path.replace('.', '_processed.')
            
            img.save(output_path)
            return output_path
            
        except Exception as e:
            print(f"Preprocessing error: {e}")
            return image_path  # Ritorna originale se preprocessing fallisce


# Istanza globale del servizio
ocr_service = OCRService()
