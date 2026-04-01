"""
Orchestrateur principal de la veille LinkedIn + Reddit.

Workflow:
  1. Scanner Brave (LinkedIn + Reddit)
  2. Filtrer doublons via Apps Script / SQLite
  3. Scorer leads (criteres + secteur)
  4. Reddit -> Apps Script add_veille_reddit
  5. LinkedIn -> Telegram si score >= 60
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
from src.brave_scanner import scan_linkedin, scan_reddit, REQUETES_REDDIT, REQUETES_LINKEDIN_VEILLE
from src.scorer import score_leads
from src.telegram_bot import send_daily_digest, alerte_lead_chaud
from config.config import MAX_LEADS_TELEGRAM

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL")


def send_to_apps_script_reddit(leads):
    """
    Envoie les leads Reddit vers Apps Script action add_veille_reddit.
    """
    if not APPS_SCRIPT_URL:
        logging.warning("APPS_SCRIPT_URL non configure - envoi Reddit ignore")
        return 0

    sent_count = 0
    for lead in leads:
        try:
            payload = {
                "action": "add_veille_reddit",
                "url": lead.get("url", ""),
                "title": lead.get("title", ""),
                "description": lead.get("description", ""),
                "score": lead.get("score", 0),
                "secteur": lead.get("secteur", "Autre"),
            }
            response = requests.post(
                APPS_SCRIPT_URL,
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            sent_count += 1
        except Exception as e:
            logging.error(f"Erreur envoi Reddit Apps Script: {e}")

    logging.info(f"{sent_count}/{len(leads)} leads Reddit envoyes a Apps Script")
    return sent_count


def main():
    """Pipeline principal de veille quotidienne"""
    logging.info("=" * 50)
    logging.info("DEMARRAGE Veille LinkedIn + Reddit (Brave API)")
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
    else:
        logging.info("  -> Aucun resultat Reddit")

    # ==================== PARTIE LINKEDIN ====================
    logging.info("[3/6] Scan LinkedIn via Brave...")
    linkedin_results = scan_linkedin()

    if not linkedin_results:
        logging.warning("Aucun resultat LinkedIn - arret")
        return

    logging.info(f"  -> {len(linkedin_results)} resultats LinkedIn bruts")

    # Filtrer doublons LinkedIn
    logging.info("[4/6] Filtrage anti-doublons LinkedIn...")
    new_leads = [lead for lead in linkedin_results if not is_duplicate(lead['url'])]

    dupes = len(linkedin_results) - len(new_leads)
    logging.info(f"  -> {len(new_leads)} nouveaux leads ({dupes} doublons ignores)")

    if not new_leads:
        logging.info("Tous les leads LinkedIn sont des doublons - arret")
        return

    # Scoring
    logging.info("[5/6] Scoring des leads LinkedIn...")
    scored_leads = score_leads(new_leads)

    # Sauvegarde en base locale
    save_leads(scored_leads)

    # Filtrer leads avec score >= 60 pour Telegram
    telegram_leads = [lead for lead in scored_leads if lead['score'] >= 60]
    logging.info(f"  -> {len(telegram_leads)} leads avec score >= 60")

    # Alertes leads chauds (score >= 75)
    hot_leads = [lead for lead in scored_leads if lead['score'] >= 75]
    if hot_leads:
        logging.info(f"[6/6] Envoi alertes leads chauds ({len(hot_leads)})...")
        for lead in hot_leads:
            alerte_lead_chaud(lead)

    # Digest Telegram (top N leads avec score >= 60)
    if telegram_leads:
        top_leads = telegram_leads[:MAX_LEADS_TELEGRAM]
        logging.info(f"Envoi digest Telegram (top {len(top_leads)} leads)...")
        send_daily_digest(top_leads)

    logging.info("=" * 50)
    logging.info("Veille LinkedIn + Reddit terminee avec succes")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
