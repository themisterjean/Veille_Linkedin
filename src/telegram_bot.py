"""
Bot Telegram avec digest quotidien et boutons interactifs.

Envoie un digest avec le top N leads scores, chacun avec
des boutons [Je garde] / [Je laisse] pour review manuelle.
"""
import asyncio
import logging
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, EMOJIS
from src.database import mark_reviewed, get_lead_by_url


def _format_lead_message(lead, index):
    """Formate un lead pour affichage Telegram (Markdown)"""
    emoji = EMOJIS.get(lead['lead_type'], "\U0001f4cc")

    type_labels = {
        "prospect_direct": "Prospect Direct",
        "veille_concurrent": "Veille Concurrent",
        "discussion": "Discussion",
    }
    type_label = type_labels.get(lead['lead_type'], "Lead")

    # Tronque snippet proprement
    snippet = lead.get('snippet', '')
    if len(snippet) > 150:
        snippet = snippet[:147] + "..."

    lines = [
        f"{emoji} *#{index} (Score: {lead['score']}) {type_label}*",
        f"\U0001f4ac \"{snippet}\"",
        "",
        f"\U0001f517 {lead['url']}",
    ]

    if lead.get('keywords'):
        kw_display = ', '.join(lead['keywords'][:3])
        lines.append(f"\U0001f3af Keywords: {kw_display}")

    lines.append("\u2501" * 18)

    return '\n'.join(lines)


def _create_buttons(lead_url):
    """Cree les boutons interactifs pour un lead"""
    keyboard = [
        [
            InlineKeyboardButton(
                "\u2705 Je garde",
                callback_data=f"keep|{lead_url[:60]}",
            ),
            InlineKeyboardButton(
                "\u274c Je laisse",
                callback_data=f"skip|{lead_url[:60]}",
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def _send_digest_async(leads):
    """Version async de l'envoi digest"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    # Header
    today = datetime.now().strftime("%d/%m/%Y")
    header = (
        f"\U0001f4ca *LinkedIn Veille - {today}*\n"
        f"\u2705 {len(leads)} nouveaux leads detectes\n\n"
        f"\u2501" * 18
    )

    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=header,
        parse_mode='Markdown',
    )

    # Chaque lead avec ses boutons
    for i, lead in enumerate(leads, 1):
        message = _format_lead_message(lead, i)
        buttons = _create_buttons(lead['url'])

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='Markdown',
            reply_markup=buttons,
            disable_web_page_preview=True,
        )

    # Footer
    footer = f"\n\u23f0 Prochain scan demain 8h CET"
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=footer,
        parse_mode='Markdown',
    )


def send_daily_digest(leads):
    """
    Envoie le digest quotidien avec les top leads.
    Fonction synchrone qui wrap l'envoi async.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram non configure - digest ignore")
        return

    if not leads:
        logging.info("Aucun lead a envoyer via Telegram")
        return

    try:
        asyncio.run(_send_digest_async(leads))
        logging.info(f"Digest Telegram envoye ({len(leads)} leads)")
    except TelegramError as e:
        logging.error(f"Erreur Telegram: {e}")
    except Exception as e:
        logging.error(f"Erreur envoi digest: {e}")


# ==================== CALLBACK HANDLERS ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gere les clics sur boutons Telegram (Je garde / Je laisse)"""
    query = update.callback_query
    await query.answer()

    # Parse callback data: "keep|url..." ou "skip|url..."
    parts = query.data.split('|', 1)
    if len(parts) != 2:
        await query.edit_message_text("Erreur: donnees callback invalides")
        return

    action, url_fragment = parts

    # Recherche lead en base par URL partielle
    lead_id = get_lead_by_url(url_fragment)

    if not lead_id:
        # Essai avec le texte du message pour retrouver l'URL complete
        logging.warning(f"Lead introuvable pour URL fragment: {url_fragment}")
        await query.edit_message_text(
            text=f"{query.message.text}\n\n\u26a0\ufe0f Lead introuvable en base",
            parse_mode='Markdown',
        )
        return

    keep = (action == "keep")
    mark_reviewed(lead_id, keep)

    if keep:
        suffix = "\n\n\u2705 *Marque: A GARDER*"
    else:
        suffix = "\n\n\u274c *Marque: IGNORE*"

    await query.edit_message_text(
        text=f"{query.message.text}{suffix}",
        parse_mode='Markdown',
    )


def setup_telegram_handlers():
    """
    Configure et retourne l'Application Telegram avec handlers.
    Utile si on veut faire tourner le bot en mode serveur (polling).
    """
    if not TELEGRAM_BOT_TOKEN:
        logging.warning("Telegram non configure - handlers ignores")
        return None

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(button_callback))
    return app
