"""
Gestion base de donnees SQLite pour anti-doublons et tracking
+ Integration Apps Script pour check_url
"""
import sqlite3
import logging
import os
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import DB_PATH

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL")


def init_db():
    """Cree la table leads si elle n'existe pas"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS linkedin_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            snippet TEXT,
            detected_date DATE,
            score INTEGER,
            lead_type TEXT,
            secteur TEXT,
            manually_reviewed BOOLEAN DEFAULT 0,
            keep_decision BOOLEAN DEFAULT NULL,
            google_sheet_exported BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    logging.info("Base de donnees initialisee")


def _check_url_apps_script(url):
    """
    Verifie si l'URL existe via Apps Script.

    Returns:
        bool: True si existe, False sinon, None si erreur
    """
    if not APPS_SCRIPT_URL:
        return None

    try:
        encoded_url = quote(url, safe='')
        response = requests.get(
            f"{APPS_SCRIPT_URL}?action=check_url&url={encoded_url}",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("exists", False)
    except Exception as e:
        logging.warning(f"Erreur Apps Script check_url: {e}")
        return None


def _check_url_sqlite(url):
    """Verifie si l'URL existe en SQLite local"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM linkedin_leads WHERE url = ?', (url,))
    result = cursor.fetchone()

    conn.close()
    return result is not None


def is_duplicate(url):
    """
    Verifie si l'URL existe deja.
    Priorite: Apps Script si configure, sinon SQLite local.
    """
    # Essayer Apps Script d'abord si configure
    if APPS_SCRIPT_URL:
        result = _check_url_apps_script(url)
        if result is not None:
            return result
        logging.warning("Fallback vers SQLite local")

    # Fallback SQLite
    return _check_url_sqlite(url)


def save_leads(leads):
    """Sauvegarde une liste de leads en base"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    saved_count = 0
    for lead in leads:
        try:
            cursor.execute('''
                INSERT INTO linkedin_leads
                (url, title, snippet, detected_date, score, lead_type, secteur)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                lead['url'],
                lead['title'],
                lead.get('snippet', ''),
                datetime.now().date().isoformat(),
                lead['score'],
                lead['lead_type'],
                lead.get('secteur', 'Autre'),
            ))
            saved_count += 1
        except sqlite3.IntegrityError:
            logging.debug(f"Doublon ignore: {lead['url']}")

    conn.commit()
    conn.close()

    logging.info(f"{saved_count}/{len(leads)} leads sauvegardes en base")
    return saved_count


def mark_reviewed(lead_id, keep):
    """Marque un lead comme reviewe suite a action bouton Telegram"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE linkedin_leads
        SET manually_reviewed = 1, keep_decision = ?
        WHERE id = ?
    ''', (keep, lead_id))

    conn.commit()
    conn.close()

    action = "garde" if keep else "ignore"
    logging.info(f"Lead {lead_id} marque: {action}")


def get_lead_by_url(url):
    """Recupere l'ID d'un lead par son URL (pour callback Telegram)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM linkedin_leads WHERE url = ?', (url,))
    result = cursor.fetchone()

    conn.close()
    return result[0] if result else None


def get_stats():
    """Recupere statistiques de la base"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM linkedin_leads')
    total = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM linkedin_leads WHERE manually_reviewed = 1')
    reviewed = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM linkedin_leads WHERE keep_decision = 1')
    kept = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "reviewed": reviewed,
        "kept": kept,
    }
