"""
Systeme de scoring simple (3 criteres, max 100 points)

- tier1_keyword:      50 pts  (migration Cognos/Tableau -> Power BI)
- intent_signal:      30 pts  (need help, looking for, struggling)
- competitor_mention:  20 pts  (Kanerika, Senturus, Sparity)
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


def calculate_score(lead):
    """
    Calcule score sur 100 et determine type de lead.

    Retourne: (score, lead_type, matched_keywords)
    """
    text = f"{lead['title']} {lead['snippet']}".lower()

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

    # Determiner type de lead
    if intent_matches and tier1_matches:
        lead_type = "prospect_direct"
    elif competitor_matches:
        lead_type = "veille_concurrent"
    else:
        lead_type = "discussion"

    return score, lead_type, matched_keywords


def score_leads(raw_leads):
    """
    Score tous les leads et trie par score decroissant.
    """
    scored_leads = []

    for lead in raw_leads:
        score, lead_type, keywords = calculate_score(lead)

        scored_leads.append({
            **lead,
            'score': score,
            'lead_type': lead_type,
            'keywords': keywords,
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
