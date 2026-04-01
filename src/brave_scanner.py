"""
Scanner via Brave Search API
"""
import logging
import time
import os
import requests
from urllib.parse import quote

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

REQUETES_REDDIT = [
    'site:reddit.com/r/BusinessIntelligence "Cognos" "migrate" OR "replace" OR "alternative"',
    'site:reddit.com/r/PowerBI "migrating from Cognos" OR "Cognos to Power BI"',
    'site:reddit.com/r/Tableau "replace" OR "switching" OR "evaluating alternatives"',
    'site:reddit.com/r/dataengineering "Cognos" "migration" OR "replace" OR "deadline"',
    'site:reddit.com/r/ITManagers "BI migration" OR "replace Cognos" OR "Tableau license cost"',
    'site:reddit.com "Cognos" "migration" "Power BI" -site:linkedin.com',
]

REQUETES_LINKEDIN_VEILLE = [
    'site:linkedin.com/posts "replace Cognos" OR "Cognos migration" "Power BI"',
    'site:linkedin.com/pulse "BI modernization" "Power BI" 2025 OR 2026',
    'site:linkedin.com/posts "migrating from Tableau" OR "Tableau to Power BI"',
    'site:linkedin.com/pulse "legacy BI" "modernization" "Power BI"',
]


def _brave_search(query, max_retries=3):
    """
    Execute une recherche Brave avec backoff sur erreur 429.

    Args:
        query: Requete de recherche
        max_retries: Nombre max de tentatives

    Returns:
        Liste de dict {url, title, description}
    """
    if not BRAVE_API_KEY:
        logging.error("BRAVE_API_KEY non defini dans l'environnement")
        return []

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }

    params = {
        "q": query,
        "count": 10,
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(
                BRAVE_SEARCH_URL,
                headers=headers,
                params=params,
                timeout=30,
            )

            if response.status_code == 429:
                logging.warning(f"Rate limit Brave (429), backoff 60s (tentative {attempt + 1}/{max_retries})")
                time.sleep(60)
                continue

            response.raise_for_status()

            data = response.json()
            results = []

            web_results = data.get("web", {}).get("results", [])
            for item in web_results:
                results.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                })

            return results

        except requests.exceptions.RequestException as e:
            logging.error(f"Erreur requete Brave (tentative {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    return []


def scan_reddit():
    """
    Scanne Reddit via Brave Search.

    Returns:
        Liste de dict {url, title, description}
    """
    all_results = []

    for i, query in enumerate(REQUETES_REDDIT, 1):
        logging.info(f"[Reddit {i}/{len(REQUETES_REDDIT)}] {query[:60]}...")
        results = _brave_search(query)
        logging.info(f"  -> {len(results)} resultats")
        all_results.extend(results)

        if i < len(REQUETES_REDDIT):
            time.sleep(1)

    logging.info(f"Total Reddit: {len(all_results)} resultats")
    return all_results


def scan_linkedin():
    """
    Scanne LinkedIn via Brave Search.

    Returns:
        Liste de dict {url, title, description, snippet}
    """
    all_results = []

    for i, query in enumerate(REQUETES_LINKEDIN_VEILLE, 1):
        logging.info(f"[LinkedIn {i}/{len(REQUETES_LINKEDIN_VEILLE)}] {query[:60]}...")
        results = _brave_search(query)
        logging.info(f"  -> {len(results)} resultats")

        for r in results:
            url = r.get("url", "")
            if "/posts/" in url or "/pulse/" in url:
                all_results.append({
                    "url": url,
                    "title": r.get("title", ""),
                    "snippet": r.get("description", ""),
                })

        if i < len(REQUETES_LINKEDIN_VEILLE):
            time.sleep(1)

    logging.info(f"Total LinkedIn: {len(all_results)} resultats (posts/articles)")
    return all_results
