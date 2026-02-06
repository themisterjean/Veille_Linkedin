"""
Scanner LinkedIn via Google Custom Search Engine
"""
import logging
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import (
    GOOGLE_CSE_CX,
    GOOGLE_API_KEY,
    LINKEDIN_QUERIES,
    MAX_RESULTS_PER_QUERY,
)


def scan_linkedin():
    """
    Lance les 5 queries CSE et retourne liste de resultats bruts.
    Filtre pour ne garder que les posts et articles LinkedIn.
    """
    if not GOOGLE_CSE_CX or not GOOGLE_API_KEY:
        logging.error("Credentials Google CSE manquants dans .env")
        return []

    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        logging.info("Connexion Google CSE OK")
    except Exception as e:
        logging.error(f"Erreur connexion CSE: {e}")
        return []

    all_results = []

    for i, query in enumerate(LINKEDIN_QUERIES, 1):
        logging.info(f"[Query {i}/{len(LINKEDIN_QUERIES)}] {query[:80]}...")

        try:
            response = service.cse().list(
                q=query,
                cx=GOOGLE_CSE_CX,
                num=min(MAX_RESULTS_PER_QUERY, 10),  # CSE max = 10
            ).execute()

            items = response.get('items', [])
            logging.info(f"  -> {len(items)} resultats trouves")

            for item in items:
                url = item.get('link', '')
                # Filtre: garde seulement posts et articles LinkedIn
                if '/posts/' in url or '/pulse/' in url:
                    all_results.append({
                        'url': url,
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                    })
                else:
                    logging.debug(f"  URL ignoree (profil/page?): {url}")

            # Pause entre queries pour respecter rate limits Google
            if i < len(LINKEDIN_QUERIES):
                time.sleep(1.5)

        except HttpError as e:
            if e.resp.status == 429:
                logging.warning(f"  Rate limit atteint, pause 10s...")
                time.sleep(10)
            else:
                logging.error(f"  Erreur HTTP CSE (query {i}): {e}")
        except Exception as e:
            logging.error(f"  Erreur inattendue (query {i}): {e}")

    logging.info(f"Total brut: {len(all_results)} resultats LinkedIn (posts/articles)")
    return all_results
