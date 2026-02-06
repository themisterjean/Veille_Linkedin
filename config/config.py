"""
Configuration centralisee pour Veille LinkedIn
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charge .env depuis la racine du projet
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")

# ==================== CREDENTIALS ====================
GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==================== QUERIES LINKEDIN ====================
LINKEDIN_QUERIES = [
    'site:linkedin.com "Cognos to Power BI migration" (help OR looking OR need OR seeking)',
    'site:linkedin.com ("Cognos migration" OR "Tableau migration") (struggle OR challenge OR difficult OR problem) 2024..2025',
    'site:linkedin.com (Kanerika FLIP OR "Senturus Migration Assistant" OR "Sparity BIPort") Power BI',
    'site:linkedin.com "Power BI migration" (automated OR tool OR accelerator OR solution)',
    'site:linkedin.com "legacy BI migration" (Cognos OR Tableau) modernization',
]

# ==================== SCORING SIMPLE ====================
SCORE_WEIGHTS = {
    "tier1_keyword": 50,      # Migration Cognos/Tableau -> Power BI
    "intent_signal": 30,      # need help, looking for, struggling
    "competitor_mention": 20, # Kanerika, Senturus, Sparity
}

# Keywords par critere
TIER1_KEYWORDS = [
    "cognos to power bi",
    "tableau to power bi",
    "migrate cognos",
    "migrate tableau",
    "power bi migration",
]

INTENT_SIGNALS = [
    "need help",
    "looking for",
    "seeking",
    "struggling",
    "challenge",
    "difficult",
    "problem",
]

COMPETITOR_NAMES = [
    "kanerika flip",
    "senturus",
    "sparity biport",
    "dataterrain",
    "winwire",
]

# ==================== LIMITES ====================
MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", 10))
MAX_LEADS_TELEGRAM = int(os.getenv("MAX_LEADS_TELEGRAM", 5))

# ==================== PATHS ====================
DB_PATH = str(_project_root / "data" / "leads.db")
LOG_DIR = str(_project_root / "logs")

# ==================== EMOJIS ====================
EMOJIS = {
    "prospect_direct": "\U0001f525",
    "veille_concurrent": "\U0001f441\ufe0f",
    "discussion": "\U0001f4ac",
}
