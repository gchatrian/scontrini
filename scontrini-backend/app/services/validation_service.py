"""
Validation Service - Validazione e scoring normalizzazioni prodotti
"""
from typing import Dict, Any, List, Optional
from enum import Enum
from app.config import settings


class ConfidenceLevel(str, Enum):
    """Livelli di confidence per normalizzazione"""
    HIGH = "high"      # ≥0.90
    MEDIUM = "medium"  # 0.70-0.89
    LOW = "low"        # <0.70


class ValidationService:
    """Servizio per validazione qualità normalizzazioni"""

    def __init__(self):
        # Configurazione dalla config centralizzata
        self.high_threshold = settings.VALIDATION_HIGH_CONFIDENCE_THRESHOLD
        self.low_threshold = settings.VALIDATION_LOW_CONFIDENCE_THRESHOLD
        self.price_tolerance = settings.CACHE_PRICE_TOLERANCE

    def validate_normalization(
        self,
        normalized_product: Dict[str, Any],
        raw_name: str,
        confidence_score: float,
        context: Optional[Dict[str, Any]] = None,
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Valida una normalizzazione prodotto e calcola score finale

        Args:
            normalized_product: Dati prodotto normalizzato
            raw_name: Nome grezzo originale
            confidence_score: Score base di confidence
            context: Contesto household/store (opzionale)
            current_price: Prezzo corrente per validazione (opzionale)

        Returns:
            {
                "is_valid": bool,
                "final_confidence": float,
                "confidence_level": "high" | "medium" | "low",
                "warnings": [str],
                "flags": {
                    "missing_fields": bool,
                    "price_anomaly": bool,
                    "low_context": bool,
                    "needs_review": bool
                },
                "recommendations": [str]
            }
        """
        warnings = []
        flags = {
            'missing_fields': False,
            'price_anomaly': False,
            'low_context': False,
            'needs_review': False
        }
        recommendations = []

        # Validazione campi obbligatori
        missing_fields = self._check_missing_fields(normalized_product)
        if missing_fields:
            flags['missing_fields'] = True
            warnings.append(f"Campi mancanti: {', '.join(missing_fields)}")
            recommendations.append("Verificare completezza dati prodotto")

        # Validazione prezzo se disponibile
        if context and current_price:
            price_check = self._validate_price(
                current_price=current_price,
                context=context
            )
            if not price_check['is_coherent']:
                flags['price_anomaly'] = True
                warnings.append(price_check['warning'])
                recommendations.append("Verificare correttezza prezzo")

        # Validazione contesto
        if context:
            context_check = self._validate_context(context)
            if context_check['is_low']:
                flags['low_context'] = True
                warnings.append(context_check['warning'])
                recommendations.append("Dati storici limitati - verificare accuratezza")

        # Calcola confidence finale
        final_confidence = self._calculate_final_confidence(
            base_confidence=confidence_score,
            has_missing_fields=flags['missing_fields'],
            has_price_anomaly=flags['price_anomaly'],
            context_score=context.get('context_score', 0.0) if context else 0.0
        )

        # Determina livello confidence
        confidence_level = self._get_confidence_level(final_confidence)

        # Flag per review manuale
        if confidence_level == ConfidenceLevel.LOW or flags['price_anomaly']:
            flags['needs_review'] = True
            recommendations.append("Review manuale consigliata")

        # Validazione generale
        is_valid = (
            final_confidence >= self.low_threshold and
            not (flags['missing_fields'] and not normalized_product.get('canonical_name'))
        )

        return {
            'is_valid': is_valid,
            'final_confidence': round(final_confidence, 3),
            'confidence_level': confidence_level.value,
            'warnings': warnings,
            'flags': flags,
            'recommendations': recommendations
        }

    def validate_batch(
        self,
        normalizations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Valida batch di normalizzazioni

        Args:
            normalizations: Lista di normalizzazioni
                [
                    {
                        "normalized_product": {...},
                        "raw_name": "...",
                        "confidence_score": 0.85,
                        "context": {...},
                        "current_price": 1.49
                    },
                    ...
                ]

        Returns:
            {
                "results": [validation_result, ...],
                "summary": {
                    "total": int,
                    "valid": int,
                    "needs_review": int,
                    "high_confidence": int,
                    "medium_confidence": int,
                    "low_confidence": int
                }
            }
        """
        results = []
        summary = {
            'total': len(normalizations),
            'valid': 0,
            'needs_review': 0,
            'high_confidence': 0,
            'medium_confidence': 0,
            'low_confidence': 0
        }

        for norm in normalizations:
            validation = self.validate_normalization(
                normalized_product=norm.get('normalized_product', {}),
                raw_name=norm.get('raw_name', ''),
                confidence_score=norm.get('confidence_score', 0.0),
                context=norm.get('context'),
                current_price=norm.get('current_price')
            )

            results.append(validation)

            # Aggiorna summary
            if validation['is_valid']:
                summary['valid'] += 1

            if validation['flags']['needs_review']:
                summary['needs_review'] += 1

            level = validation['confidence_level']
            if level == ConfidenceLevel.HIGH.value:
                summary['high_confidence'] += 1
            elif level == ConfidenceLevel.MEDIUM.value:
                summary['medium_confidence'] += 1
            else:
                summary['low_confidence'] += 1

        return {
            'results': results,
            'summary': summary
        }

    def _check_missing_fields(self, product: Dict[str, Any]) -> List[str]:
        """
        Verifica campi mancanti nel prodotto normalizzato

        Returns:
            Lista di nomi campi mancanti
        """
        required_fields = ['canonical_name']
        important_fields = ['category', 'brand', 'size', 'unit_type']

        missing = []

        for field in required_fields:
            if not product.get(field):
                missing.append(field)

        for field in important_fields:
            if not product.get(field):
                missing.append(field)

        return missing

    def _validate_price(
        self,
        current_price: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Valida coerenza prezzo con storico

        Returns:
            {
                "is_coherent": bool,
                "warning": str | None,
                "deviation_percent": float
            }
        """
        household_ctx = context.get('household', {})
        avg_price = household_ctx.get('avg_price')

        if not avg_price:
            return {
                'is_coherent': True,
                'warning': None,
                'deviation_percent': 0.0
            }

        # Calcola deviazione percentuale
        deviation = abs(current_price - avg_price) / avg_price

        is_coherent = deviation <= self.price_tolerance

        warning = None
        if not is_coherent:
            warning = f"Prezzo anomalo: {current_price:.2f}€ vs media storica {avg_price:.2f}€ ({deviation*100:.1f}% differenza)"

        return {
            'is_coherent': is_coherent,
            'warning': warning,
            'deviation_percent': round(deviation, 3)
        }

    def _validate_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida disponibilità contesto storico

        Returns:
            {
                "is_low": bool,
                "warning": str | None
            }
        """
        context_score = context.get('context_score', 0.0)

        is_low = context_score < 0.3

        warning = None
        if is_low:
            warning = "Contesto storico limitato - prima volta o pochi acquisti"

        return {
            'is_low': is_low,
            'warning': warning
        }

    def _calculate_final_confidence(
        self,
        base_confidence: float,
        has_missing_fields: bool,
        has_price_anomaly: bool,
        context_score: float
    ) -> float:
        """
        Calcola confidence finale applicando penalità e boost

        Args:
            base_confidence: Score base (da cache o vector search)
            has_missing_fields: Se ha campi mancanti
            has_price_anomaly: Se prezzo anomalo
            context_score: Score contesto (0-1)

        Returns:
            Confidence finale (0-1)
        """
        confidence = base_confidence

        # Penalità per campi mancanti
        if has_missing_fields:
            confidence -= 0.10

        # Penalità per prezzo anomalo
        if has_price_anomaly:
            confidence -= 0.15

        # Boost per contesto forte (max +5%)
        if context_score >= 0.7:
            confidence += 0.05

        # Clamp tra 0 e 1
        return max(0.0, min(1.0, confidence))

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """
        Determina livello confidence

        Returns:
            HIGH, MEDIUM, o LOW
        """
        if confidence >= self.high_threshold:
            return ConfidenceLevel.HIGH
        elif confidence >= self.low_threshold:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def get_validation_summary(
        self,
        validations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Genera summary statistiche per lista validazioni

        Args:
            validations: Lista di validation results

        Returns:
            {
                "total_products": int,
                "avg_confidence": float,
                "distribution": {
                    "high": int,
                    "medium": int,
                    "low": int
                },
                "issues": {
                    "missing_fields": int,
                    "price_anomalies": int,
                    "low_context": int
                },
                "needs_review_count": int
            }
        """
        if not validations:
            return {
                'total_products': 0,
                'avg_confidence': 0.0,
                'distribution': {'high': 0, 'medium': 0, 'low': 0},
                'issues': {'missing_fields': 0, 'price_anomalies': 0, 'low_context': 0},
                'needs_review_count': 0
            }

        total = len(validations)
        confidences = [v['final_confidence'] for v in validations]
        avg_confidence = sum(confidences) / total

        distribution = {'high': 0, 'medium': 0, 'low': 0}
        issues = {'missing_fields': 0, 'price_anomalies': 0, 'low_context': 0}
        needs_review = 0

        for v in validations:
            distribution[v['confidence_level']] += 1

            flags = v['flags']
            if flags['missing_fields']:
                issues['missing_fields'] += 1
            if flags['price_anomaly']:
                issues['price_anomalies'] += 1
            if flags['low_context']:
                issues['low_context'] += 1
            if flags['needs_review']:
                needs_review += 1

        return {
            'total_products': total,
            'avg_confidence': round(avg_confidence, 3),
            'distribution': distribution,
            'issues': issues,
            'needs_review_count': needs_review
        }
