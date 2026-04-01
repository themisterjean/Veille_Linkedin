"""
Systeme de scoring simple (3 criteres, max 100 points)

- tier1_keyword:      50 pts  (migration Cognos/Tableau -> Power BI)
- intent_signal:      30 pts  (need help, looking for, struggling)
- competitor_mention:  20 pts  (Kanerika, Senturus, Sparity)

+ DISQUALIFIERS: met score a 0 si detecte
+ Detection secteur automatique
+ Bonus +20 pts si deadline/evaluating/replace/switching/budget
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import (
    SCORE_WEIGHTS,
    TIER1_KEYWORDS,
    INTENT_SIGNALS,
    COMPETITOR_NAMES,
)

# Mots-cles disqualifiants -> score = 0
DISQUALIFIERS = [
    "freelance",
    "consultant indépendant",
    "contractor",
    "self-employed",
    "microsoft partner",
    "ibm partner",
    "data analyst",
    "bi developer",
    "cognos developer",
    "tableau developer",
    "staffing",
    "recruitment",
    "we are hiring",
]

# Mots-cles bonus (+20 pts)
BONUS_KEYWORDS = [
    "deadline",
    "evaluating",
    "replace",
    "switching",
    "budget",
]

# Detection secteur
SECTEURS = {
    "Finance": ["finance", "banking", "insurance", "bank", "fintech", "assurance"],
    "Industrie": ["manufacturing", "industrial", "automotive", "factory", "production"],
    "Santé": ["healthcare", "pharma", "hospital", "medical", "health"],
    "Energie": ["energy", "utilities", "oil", "gas", "renewable", "power plant"],
    "Retail": ["retail", "distribution", "commerce", "e-commerce", "store"],
}


def detect_secteur(text):
    """
    Detecte le secteur d'activite a partir du texte.

    Returns:
        str: Nom du secteur ou "Autre"
    """
    text_lower = text.lower()
    for secteur, keywords in SECTEURS.items():
        for kw in keywords:
            if kw in text_lower:
                return secteur
    return "Autre"


def is_disqualified(text):
    """
    Verifie si le texte contient un mot-cle disqualifiant.

    Returns:
        bool: True si disqualifie
    """
    text_lower = text.lower()
    for disq in DISQUALIFIERS:
        if disq.lower() in text_lower:
            return True
    return False


def calculate_score(lead):
    """
    Calcule score sur 100 et determine type de lead.

    Retourne: (score, lead_type, matched_keywords, secteur)
    """
    text = f"{lead['title']} {lead.get('snippet', '')} {lead.get('description', '')}".lower()

    # Check disqualifiers first
    if is_disqualified(text):
        return 0, "disqualified", [], detect_secteur(text)

    score = 0
    matched_keywords = []

    # Tier 1: Keywords migration (50 pts)
    tier1_matches = [kw for kw in TIER1_KEYWORDS if kw.lower() in text]
    if tier1_matches:
        score += SCORE_WEIGHTS['tier1_keyword']
        matched_keywords.extend(tier1_matches)

    # Intent signals (30 pts)
    intent_matches = [sig for sig in INTENT_SIGNALS if sig.lower() in text]
    if intent_matches:
        score += SCORE_WEIGHTS['intent_signal']
        matched_keywords.extend(intent_matches)

    # Competitor mentions (20 pts)
    competitor_matches = [comp for comp in COMPETITOR_NAMES if comp.lower() in text]
    if competitor_matches:
        score += SCORE_WEIGHTS['competitor_mention']
        matched_keywords.extend(competitor_matches)

    # Bonus +20 pts si deadline/evaluating/replace/switching/budget
    bonus_matches = [bk for bk in BONUS_KEYWORDS if bk.lower() in text]
    if bonus_matches:
        score += 20
        matched_keywords.extend(bonus_matches)

    # Cap score at 100
    score = min(score, 100)

    # Determiner type de lead
    if intent_matches and tier1_matches:
        lead_type = "prospect_direct"
    elif competitor_matches:
        lead_type = "veille_concurrent"
    else:
        lead_type = "discussion"

    # Detection secteur
    secteur = detect_secteur(text)

    return score, lead_type, matched_keywords, secteur


def score_leads(raw_leads):
    """
    Score tous les leads et trie par score decroissant.
    """
    scored_leads = []

    for lead in raw_leads:
        score, lead_type, keywords, secteur = calculate_score(lead)

        scored_leads.append({
            **lead,
            'score': score,
            'lead_type': lead_type,
            'keywords': keywords,
            'secteur': secteur,
        })

    # Tri par score decroissant
    scored_leads.sort(key=lambda x: x['score'], reverse=True)

    # Stats par type
    type_counts = {}
    for sl in scored_leads:
        t = sl['lead_type']
        type_counts[t] = type_counts.get(t, 0) + 1

    logging.info(f"{len(scored_leads)} leads scores - repartition: {type_counts}")
    return scored_leads
