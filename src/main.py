"""
Orchestrateur principal de la veille LinkedIn.

Workflow:
  1. Scanner CSE LinkedIn (5 queries)
  2. Filtrer doublons via SQLite
  3. Scorer leads (3 criteres)
  4. Sauvegarder en base
  5. Envoyer top N via Telegram
"""
import sys
import logging
from datetime import datetime
from pathlib import Path

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
from src.cse_scanner import scan_linkedin
from src.scorer import score_leads
from src.telegram_bot import send_daily_digest
from config.config import MAX_LEADS_TELEGRAM


def main():
    """Pipeline principal de veille quotidienne"""
    logging.info("=" * 50)
    logging.info("DEMARRAGE Veille LinkedIn")
    logging.info("=" * 50)

    # Init DB
    init_db()

    # Etape 1: Scanner CSE
    logging.info("[1/5] Scan LinkedIn CSE...")
    raw_results = scan_linkedin()

    if not raw_results:
        logging.warning("Aucun resultat CSE - arret")
        return

    logging.info(f"  -> {len(raw_results)} resultats bruts recuperes")

    # Etape 2: Filtrer doublons
    logging.info("[2/5] Filtrage anti-doublons...")
    new_leads = [lead for lead in raw_results if not is_duplicate(lead['url'])]

    dupes = len(raw_results) - len(new_leads)
    logging.info(f"  -> {len(new_leads)} nouveaux leads ({dupes} doublons ignores)")

    if not new_leads:
        logging.info("Tous les leads sont des doublons - arret")
        return

    # Etape 3: Scoring
    logging.info("[3/5] Scoring des leads...")
    scored_leads = score_leads(new_leads)

    # Etape 4: Sauvegarde DB (tous les nouveaux leads)
    logging.info("[4/5] Sauvegarde en base...")
    save_leads(scored_leads)

    # Etape 5: Top N pour Telegram
    top_leads = scored_leads[:MAX_LEADS_TELEGRAM]
    logging.info(f"[5/5] Envoi digest Telegram (top {len(top_leads)} leads)...")
    send_daily_digest(top_leads)

    logging.info("=" * 50)
    logging.info("Veille LinkedIn terminee avec succes")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
