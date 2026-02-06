# Veille LinkedIn - Meta BI

Bot automatise de veille LinkedIn pour detecter des opportunites de migration BI (Cognos/Tableau vers Power BI) via Google Custom Search Engine.

## Fonctionnalites

- Scan quotidien LinkedIn via Google CSE (5 queries ciblees)
- Scoring automatique sur 100 points (3 criteres)
- Anti-doublons SQLite
- Digest Telegram avec top 5 leads
- Boutons interactifs Telegram (Je garde / Je laisse)
- GitHub Actions pour execution quotidienne

## Installation Locale

### Prerequis

- Python 3.9+
- Compte Google (pour CSE)
- Bot Telegram

### Installation

```bash
git clone <url-du-repo>
cd Veille_Linkedin
chmod +x setup_local.sh
./setup_local.sh
```

### Configuration

#### A. Google Custom Search Engine

1. Aller sur https://programmablesearchengine.google.com/
2. Creer un nouveau moteur:
   - Sites a rechercher: `linkedin.com/posts/*` et `linkedin.com/pulse/*`
   - Langue: Anglais + Francais + Allemand
3. Noter le **CX ID** (format: `abc123def456:ghijklmnop`)

#### B. Google API Key

1. Aller sur https://console.cloud.google.com/
2. APIs & Services > Credentials
3. Create Credentials > API Key
4. Activer "Custom Search JSON API"

#### C. Bot Telegram

1. Parler a @BotFather sur Telegram
2. `/newbot` et suivre les instructions
3. Noter le **bot_token**
4. Recuperer son **chat_id**:
   - Envoyer un message au bot
   - Aller sur `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Chercher `"chat":{"id":123456789}`

#### D. Fichier .env

```bash
cp config/.env.example .env
# Editer .env avec les credentials
```

### Test Local

```bash
source venv/bin/activate
python src/main.py
```

## Deploiement GitHub Actions

### Secrets a configurer

Dans Settings > Secrets and variables > Actions, ajouter:

- `GOOGLE_CSE_CX`
- `GOOGLE_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Le workflow `.github/workflows/daily-scan.yml` lance le scan chaque jour a 8h CET.

Test manuel: Actions > Veille LinkedIn Quotidienne > Run workflow

## Base de Donnees

```
Table: linkedin_leads
- id              INTEGER PRIMARY KEY
- url             TEXT UNIQUE (cle deduplication)
- title           TEXT
- snippet         TEXT
- detected_date   DATE
- score           INTEGER (0-100)
- lead_type       TEXT (prospect_direct, veille_concurrent, discussion)
- manually_reviewed  BOOLEAN
- keep_decision      BOOLEAN
- google_sheet_exported  BOOLEAN
```

## Queries LinkedIn

| # | Query | Cible |
|---|-------|-------|
| 1 | `"Cognos to Power BI migration" (help OR looking OR need OR seeking)` | Migration directe avec intent |
| 2 | `("Cognos migration" OR "Tableau migration") (struggle OR challenge)` | Frustrations migration |
| 3 | `(Kanerika FLIP OR Senturus OR Sparity) Power BI` | Veille concurrents |
| 4 | `"Power BI migration" (automated OR tool OR accelerator)` | Solutions automatisees |
| 5 | `"legacy BI migration" (Cognos OR Tableau) modernization` | Legacy BI modernization |

## Scoring (sur 100)

| Critere | Points | Exemples |
|---------|--------|----------|
| tier1_keyword | 50 | migration Cognos/Tableau vers Power BI |
| intent_signal | 30 | need help, looking for, struggling |
| competitor_mention | 20 | Kanerika, Senturus, Sparity |

## Structure du projet

```
Veille_Linkedin/
  .github/workflows/daily-scan.yml
  config/__init__.py
  config/config.py
  config/.env.example
  src/__init__.py
  src/main.py
  src/cse_scanner.py
  src/scorer.py
  src/telegram_bot.py
  src/database.py
  data/.gitkeep
  logs/.gitkeep
  requirements.txt
  setup_local.sh
  .gitignore
  README.md
```

## Troubleshooting

**Erreur CSE**: Verifier `GOOGLE_CSE_CX` et `GOOGLE_API_KEY` dans .env

**Pas de message Telegram**: Verifier `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`

**Doublons**: La DB SQLite filtre automatiquement via URL unique

**Boutons ne repondent pas**: Le bot Telegram doit tourner en mode serveur pour les callbacks (phase 2)

## Auteur

Jean-Michel BRICLOT - Morning Hills / Meta BI
