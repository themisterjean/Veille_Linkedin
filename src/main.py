"""
Orchestrateur principal de la veille LinkedIn Profils + Reddit.

Workflow:
  1. Scanner Brave (Reddit) + Google CSE (LinkedIn Profils)
  2. Filtrer doublons via SQLite
  3. Scorer leads (criteres + secteur)
  4. Reddit -> Apps Script add_veille_reddit
  5. LinkedIn Profils -> Telegram si score >= 60
  6. Leads chauds (score >= 75) -> alerte Telegram
"""
import sys
import os
import logging
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

# Ajoute racine projet au path
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

# Setup logging (fichier + console)
_log_dir = _project_root / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

_log_file = _log_dir / f"veille_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(_log_file), encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)

from src.database import init_db, is_duplicate, save_leads
from src.brave_scanner import scan_reddit, REQUETES_REDDIT
from src.google_cse_scanner import scan_linkedin_profils
from src.scorer import score_leads
from src.telegram_bot import send_daily_digest, alerte_lead_chaud
from config.config import MAX_LEADS_TELEGRAM

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL")


def send_to_apps_script_reddit(leads):
    """
    Envoie les leads Reddit vers Apps Script action add_veille_reddit (batch unique).
    """
    if not APPS_SCRIPT_URL:
        logging.warning("APPS_SCRIPT_URL non configure - envoi Reddit ignore")
        return 0

    payload = {
        "action": "add_veille_reddit",
        "posts": [
            {
                "url_post": lead.get("url", ""),
                "titre": lead.get("title", ""),
                "snippet": lead.get("description", ""),
                "subreddit": lead.get("subreddit", ""),
                "score": lead.get("score", 0),
                "requete": lead.get("requete", ""),
                "date_collecte": lead.get("date_collecte", ""),
            }
            for lead in leads
        ],
    }

    try:
        response = requests.post(APPS_SCRIPT_URL, json=payload, timeout=30)
        response.raise_for_status()
        logging.info(f"{len(leads)} leads Reddit envoyes a Apps Script (batch)")
        return len(leads)
    except Exception as e:
        logging.error(f"Erreur envoi Reddit Apps Script: {e}")
        return 0


def main():
    """Pipeline principal de veille quotidienne"""
    logging.info("=" * 50)
    logging.info("DEMARRAGE Veille LinkedIn Profils + Reddit")
    logging.info("=" * 50)

    # Init DB
    init_db()

    # ==================== PARTIE REDDIT ====================
    logging.info("[1/6] Scan Reddit via Brave...")
    reddit_results = scan_reddit()

    if reddit_results:
        logging.info(f"  -> {len(reddit_results)} resultats Reddit bruts")

        # Filtrer doublons Reddit
        new_reddit = [r for r in reddit_results if not is_duplicate(r['url'])]
        logging.info(f"  -> {len(new_reddit)} nouveaux leads Reddit")

        if new_reddit:
            # Scorer les leads Reddit (ajoute snippet depuis description)
            for lead in new_reddit:
                lead['snippet'] = lead.get('description', '')
            scored_reddit = score_leads(new_reddit)

            # Envoyer vers Apps Script
            logging.info("[2/6] Envoi Reddit vers Apps Script...")
            send_to_apps_script_reddit(scored_reddit)

            # Alertes Telegram leads chauds Reddit (seuil 40, plus bas que LinkedIn)
            hot_reddit = [lead for lead in scored_reddit if lead['score'] >= 40]
            if hot_reddit:
                logging.info(f"  -> {len(hot_reddit)} leads chauds Reddit (score >= 40)")
                for lead in hot_reddit:
                    alerte_lead_chaud(lead)
    else:
        logging.info("  -> Aucun resultat Reddit")

    # ==================== PARTIE LINKEDIN PROFILS ====================
    logging.info("[3/6] Scan LinkedIn Profils via Google CSE...")
    profil_results = scan_linkedin_profils()

    if not profil_results:
        logging.warning("Aucun resultat LinkedIn Profils - etape ignoree")
    else:
        logging.info(f"  -> {len(profil_results)} resultats LinkedIn Profils bruts")

        # Filtrer doublons
        logging.info("[4/6] Filtrage anti-doublons LinkedIn Profils...")
        new_profils = [lead for lead in profil_results if not is_duplicate(lead['url'])]

        dupes = len(profil_results) - len(new_profils)
        logging.info(f"  -> {len(new_profils)} nouveaux profils ({dupes} doublons ignores)")

        if new_profils:
            # Ajoute snippet depuis description pour le scoring
            for lead in new_profils:
                lead['snippet'] = lead.get('description', '')

            # Scoring
            logging.info("[5/6] Scoring des profils LinkedIn...")
            scored_profils = score_leads(new_profils)

            # Sauvegarde en base locale
            save_leads(scored_profils)

            # Filtrer leads avec score >= 60 pour Telegram
            telegram_leads = [lead for lead in scored_profils if lead['score'] >= 60]
            logging.info(f"  -> {len(telegram_leads)} profils avec score >= 60")

            # Alertes leads chauds (score >= 75)
            hot_leads = [lead for lead in scored_profils if lead['score'] >= 75]
            if hot_leads:
                logging.info(f"[6/6] Envoi alertes leads chauds ({len(hot_leads)})...")
                for lead in hot_leads:
                    alerte_lead_chaud(lead)

            # Digest Telegram (top N leads avec score >= 60)
            if telegram_leads:
                top_leads = telegram_leads[:MAX_LEADS_TELEGRAM]
                logging.info(f"Envoi digest Telegram (top {len(top_leads)} profils)...")
                send_daily_digest(top_leads)
        else:
            logging.info("Tous les profils LinkedIn sont des doublons - etape ignoree")

    logging.info("=" * 50)
    logging.info("Veille LinkedIn Profils + Reddit terminee avec succes")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
