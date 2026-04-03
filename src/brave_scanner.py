"""
Scanner via Brave Search API
"""
import logging
import re
import time
import os
import requests
from datetime import datetime
from urllib.parse import quote

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

REQUETES_REDDIT = [
    'site:reddit.com "Cognos" "Power BI" "migrate" OR "migration" OR "replacing"',
    'site:reddit.com "Cognos" "move to Power BI" OR "switch to Power BI"',
    'site:reddit.com "migrate from Cognos" OR "leaving Cognos" OR "replacing Cognos"',
    'site:reddit.com "Tableau" "replace" "Power BI" OR "Superset" OR "migration"',
    'site:reddit.com "migrate from Tableau" OR "leaving Tableau" OR "Tableau license" "alternative"',
    'site:reddit.com "Cognos migration" OR "Cognos to Power BI" OR "Cognos alternatives"',
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
        for r in results:
            m = re.search(r'reddit\.com/(r/[^/?#]+)', r.get("url", ""))
            r["subreddit"] = m.group(1) if m else ""
            r["requete"] = query
            r["date_collecte"] = datetime.now().strftime("%Y-%m-%d")
        all_results.extend(results)

        if i < len(REQUETES_REDDIT):
            time.sleep(1)

    logging.info(f"Total Reddit: {len(all_results)} resultats")
    return all_results


