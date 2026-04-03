"""
Scanner LinkedIn Profils via Google Custom Search Engine (CSE)
"""
import logging
import os
import time
import requests
from datetime import datetime

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CSE_CX = os.environ.get("GOOGLE_CSE_CX")
GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"

REQUETES_LINKEDIN_PROFILS = [
    'site:linkedin.com/in "IT Director" "Cognos" finance OR banking OR insurance',
    'site:linkedin.com/in "CTO" "Cognos" manufacturing OR industrial OR automotive',
    'site:linkedin.com/in "Head of BI" "Tableau" healthcare OR pharma OR hospital',
    'site:linkedin.com/in "IT Director" "Cognos" OR "Tableau" France OR Germany',
    'site:linkedin.com/in "VP Data" "Cognos" OR "MicroStrategy" energy OR utilities',
    'site:linkedin.com/in "CTO" "IBM Cognos" Netherlands OR Belgium OR Switzerland',
    'site:linkedin.com/in "Head of Analytics" "Tableau" retail OR distribution',
    'site:linkedin.com/in "Chief Data Officer" "Cognos" OR "Qlik" Italy OR Spain',
]


def _google_cse_search(query, max_retries=3):
    """
    Execute une recherche Google CSE avec backoff sur erreur 429.

    Args:
        query: Requete de recherche
        max_retries: Nombre max de tentatives

    Returns:
        Liste de dict {url, title, description}
    """
    if not GOOGLE_API_KEY:
        logging.error("GOOGLE_API_KEY non defini dans l'environnement")
        return []
    if not GOOGLE_CSE_CX:
        logging.error("GOOGLE_CSE_CX non defini dans l'environnement")
        return []

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_CX,
        "q": query,
        "num": 10,
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(GOOGLE_CSE_URL, params=params, timeout=30)

            if response.status_code == 429:
                logging.warning(
                    f"Rate limit Google CSE (429), backoff 60s (tentative {attempt + 1}/{max_retries})"
                )
                time.sleep(60)
                continue

            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get("items", []):
                results.append({
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "description": item.get("snippet", ""),
                })

            return results

        except requests.exceptions.RequestException as e:
            logging.error(f"Erreur requete Google CSE (tentative {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    return []


def scan_linkedin_profils():
    """
    Scanne les profils LinkedIn via Google CSE.

    Returns:
        Liste de dict {url, title, description, requete, date_collecte}
    """
    all_results = []

    for i, query in enumerate(REQUETES_LINKEDIN_PROFILS, 1):
        logging.info(f"[LinkedIn Profils {i}/{len(REQUETES_LINKEDIN_PROFILS)}] {query[:60]}...")
        results = _google_cse_search(query)
        logging.info(f"  -> {len(results)} resultats")

        for r in results:
            r["requete"] = query
            r["date_collecte"] = datetime.now().strftime("%Y-%m-%d")

        all_results.extend(results)

        if i < len(REQUETES_LINKEDIN_PROFILS):
            time.sleep(1)

    logging.info(f"Total LinkedIn Profils: {len(all_results)} resultats")
    return all_results
