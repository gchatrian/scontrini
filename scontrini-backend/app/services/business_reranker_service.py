"""
Business Reranker Service - Regole business per filtering/reranking candidati
Applica logica deterministica per validare e riordinare risultati SQL
"""
from typing import List, Dict, Any, Optional
from app.config import settings


class BusinessRerankerService:
    """Servizio per reranking candidati con regole business"""

    # Unit families per validazione compatibilità
    UNIT_FAMILIES = {
        'liquidi': ['L', 'l', 'ml', 'cl'],
        'peso': ['kg', 'g'],
        'pezzi': ['pz', 'unit', 'pezzi']
    }

    def rerank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        hypothesis_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Applica regole business e ricalcola score

        Args:
            candidates: Lista candidati da SQL retriever
                [
                    {
                        "product_id": "uuid",
                        "canonical_name": "...",
                        "brand": "...",
                        "category": "...",
                        "size": "1500",
                        "unit_type": "ml",
                        "tags": [...],
                        "combined_score": 0.8
                    },
                    ...
                ]
            hypothesis_context: Dati estratti da LLM Interpret
                {
                    "brand": "Sant'Anna",
                    "category": "Bevande",
                    "size": "1500",
                    "unit_type": "ml",
                    "tags": ["acqua", "frizzante"]
                }

        Returns:
            Lista candidati filtrati e re-ranked con business_score
            Ordinati per business_score DESC
        """
        if not candidates:
            return []

        print(f"   [RERANK] Processing {len(candidates)} candidates...")
        filtered = []
        discarded = 0

        for candidate in candidates:
            # RULE 1: Scarta unità incompatibili
            if not self._are_units_compatible(
                hypothesis_context.get('unit_type'),
                candidate.get('unit_type')
            ):
                print(f"   [RERANK] SCARTATO per unità incompatibili: {candidate['canonical_name']}")
                discarded += 1
                continue  # SCARTA

            # Calcola business_score partendo da combined_score SQL
            business_score = candidate.get('combined_score', 0.0)

            # RULE 2: Penalità brand mismatch
            if hypothesis_context.get('brand') and candidate.get('brand'):
                hyp_brand = hypothesis_context['brand'].lower().strip()
                cand_brand = candidate['brand'].lower().strip()
                if hyp_brand != cand_brand:
                    business_score -= settings.RERANKER_BRAND_MISMATCH_PENALTY
                    print(f"   [RERANK] Penalità brand: {candidate['canonical_name']} (hyp={hyp_brand} vs cand={cand_brand})")

            # RULE 3: Penalità category mismatch
            if hypothesis_context.get('category') and candidate.get('category'):
                hyp_cat = hypothesis_context['category'].lower().strip()
                cand_cat = candidate['category'].lower().strip()
                if hyp_cat != cand_cat:
                    business_score -= settings.RERANKER_CATEGORY_MISMATCH_PENALTY

            # RULE 4: Boost tag overlap
            hyp_tags = set([t.lower() for t in hypothesis_context.get('tags', [])])
            cand_tags = set([t.lower() for t in candidate.get('tags', [])])
            tag_overlap = len(hyp_tags & cand_tags)
            if tag_overlap > 0:
                boost = tag_overlap * settings.RERANKER_TAG_OVERLAP_BOOST
                business_score += boost
                print(f"   [RERANK] Boost tag overlap (+{boost:.2f}): {candidate['canonical_name']}")

            # RULE 5: Boost size proximity
            if hypothesis_context.get('size') and candidate.get('size'):
                try:
                    hyp_size = float(hypothesis_context['size'])
                    cand_size = float(candidate['size'])
                    size_diff_pct = abs(hyp_size - cand_size) / hyp_size
                    if size_diff_pct < 0.05:  # <5% difference
                        business_score += settings.RERANKER_SIZE_PROXIMITY_BOOST
                        print(f"   [RERANK] Boost size proximity: {candidate['canonical_name']}")
                except (ValueError, ZeroDivisionError):
                    pass

            # Cap score between 0-1
            business_score = max(0.0, min(1.0, business_score))

            # Aggiungi business_score al candidato
            candidate['business_score'] = business_score
            filtered.append(candidate)

        if not filtered:
            print(f"   [RERANK] ⚠️ Tutti i {len(candidates)} candidati scartati ({discarded} unità incompatibili)")
            return []

        # Sort per business_score DESC
        filtered.sort(key=lambda x: x['business_score'], reverse=True)

        # Return top 10
        top_10 = filtered[:10]
        print(f"   [RERANK] ✅ {len(filtered)} survived ({discarded} discarded), returning top {len(top_10)} (best: {top_10[0]['business_score']:.3f})")

        return top_10

    def _are_units_compatible(
        self,
        unit1: Optional[str],
        unit2: Optional[str]
    ) -> bool:
        """
        Verifica se due unità sono compatibili

        Args:
            unit1: Unità ipotesi (es. "ml")
            unit2: Unità candidato (es. "L")

        Returns:
            True se compatibili o se manca info, False altrimenti
        """
        if not unit1 or not unit2:
            return True  # Se manca info, non scartare

        # Trova famiglia per ogni unità
        family1 = self._get_unit_family(unit1)
        family2 = self._get_unit_family(unit2)

        if not family1 or not family2:
            return True  # Unknown units, non scartare

        return family1 == family2

    def _get_unit_family(self, unit: str) -> Optional[str]:
        """
        Trova famiglia di appartenenza per unità

        Args:
            unit: Unità di misura (es. "ml", "kg", "pz")

        Returns:
            Nome famiglia ('liquidi', 'peso', 'pezzi') o None
        """
        unit_lower = unit.lower()
        for family, units in self.UNIT_FAMILIES.items():
            if unit_lower in [u.lower() for u in units]:
                return family
        return None


# Instanza globale
business_reranker_service = BusinessRerankerService()
