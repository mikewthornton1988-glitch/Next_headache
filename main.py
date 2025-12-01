import os
import json
import asyncio
from datetime import datetime
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------- CONFIG ----------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

PLAYERS_FILE = DATA_DIR / "players.json"
TOURNAMENTS_FILE = DATA_DIR / "tournaments.json"
ENTRIES_FILE = DATA_DIR / "entries.json"

BOT_TOKEN = os.getenv("BOT_TOKEN")


# ---------- JSON HELPERS ----------

def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data is not None else default
    except Exception:
        return default


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def default_tournaments():
    return [
        {
            "id": "5wta",
            "name": "$5 Winner Takes All",
            "buy_in": 5.0,
            "format": "wta",
            "prize_pool_pct": 0.75,
        },
        {
            "id": "10wta",
            "name": "$10 Winner Takes All",
            "buy_in": 10.0,
            "format": "wta",
            "prize_pool_pct": 0.75,
        },
        {
            "id": "10top2",
            "name": "$10 Top 2 Payout",
            "buy_in": 10.0,
            "format": "top2",
            "prize_pool_pct": 0.75,
        },
        {
            "id": "20top3",
            "name": "$20 Top 3 Payout",
            "buy_in": 20.0,
            "format": "top3",
            "prize_pool_pct": 0.75,
        },
    ]


def get_players():
    data = load_json(PLAYERS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_players(players):
    save_json(PLAYERS_FILE, players)


def get_tournaments():
    data = load_json(TOURNAMENTS_FILE, None)
    if not data:
        data = default_tournaments()
        save_json(TOURNAMENTS_FILE, data)
    return data


def get_entries():
    data = load_json(ENTRIES_FILE, [])
    return data if isinstance(data, list) else []


def save_entries(entries):
    save_json(ENTRIES_FILE, entries)


def find_tournament(t_id: str):
    for t in get_tournaments():
        if t["id"] == t_id:
            return t
    return None


# ---------- HANDLERS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    players = get_players()
    uid = str(user.id)

    if uid not in players:
        players[uid] = {
            "username": user.username or user.full_name,
            "joined_at": datetime.utcnow().isoformat(),
            "entries": 0,
            "total_buyins": 0.0,
        }
        save_players(players)

    text = (
        "🎱 Welcome to the Cashpool Tournament Bot\n\n"
        "This bot tracks your real 8-ball cash games.\n"
        "You collect buy-ins in Cash App / cash like normal;\n"
        "the bot keeps the records & stats.\n\n"
        "Use the buttons below to view tournaments or your stats."
    )

    keyboard = [
        [InlineKeyboardButton("📜 View Tournaments", callback_data="menu_tournaments")],
        [InlineKeyboardButton("📊 My Stats", callback_data="menu_stats")],
    ]

    if update.message:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.effective_chat.send_message(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Commands:\n"
        "/start - open main menu\n"
        "/help - show this message\n"
        "/tournaments - list tournaments\n"
        "/stats - show your stats\n\n"
        "Use the buttons in the menus to join tables."
    )
    await update.message.reply_text(text)


async def tournaments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tournaments = get_tournaments()
    if not tournaments:
        await update.message.reply_text("No tournaments configured yet.")
        return

    lines = []
    for t in tournaments:
        lines.append(f"{t['id']}: {t['name']} – ${t['buy_in']:.0f} buy-in")

    text = "🎱 Available Tournaments:\n\n" + "\n".join(lines)
    await update.message.reply_text(text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    players = get_players()
    uid = str(user.id)
    p = players.get(uid)

    if not p:
        await update.message.reply_text(
            "No stats yet. Join a tournament from the menu first."
        )
        return

    text = (
        f"📊 Stats for {p.get('username', user.full_name)}\n\n"
        f"Tournaments joined: {p.get('entries', 0)}\n"
        f"Total buy-ins logged: ${p.get('total_buyins', 0.0):.2f}"
    )
    await update.message.reply_text(text)


async def show_tournament_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tournaments = get_tournaments()
    if not tournaments:
        await query.edit_message_text("No tournaments configured yet.")
        return

    buttons = []
    for t in tournaments:
        label = f"{t['name']} – ${t['buy_in']:.0f}"
        buttons.append(
            [InlineKeyboardButton(label, callback_data=f"join_{t['id']}")]
        )

    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_main")])

    await query.edit_message_text(
        "🎱 Choose a tournament to log a new buy-in:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📜 View Tournaments", callback_data="menu_tournaments")],
        [InlineKeyboardButton("📊 My Stats", callback_data="menu_stats")],
    ]

    await query.edit_message_text(
        "Main menu:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    players = get_players()
    uid = str(user.id)
    p = players.get(uid)

    if not p:
        text = "No stats yet. Join a tournament from the menu first."
    else:
        text = (
            f"📊 Stats for {p.get('username', user.full_name)}\n\n"
            f"Tournaments joined: {p.get('entries', 0)}\n"
            f"Total buy-ins logged: ${p.get('total_buyins', 0.0):.2f}"
        )

    keyboard = [
        [InlineKeyboardButton("📜 View Tournaments", callback_data="menu_tournaments")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_join(update: Update, context: ContextTypes.DEFAULT_TYPE, t_id: str):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    t = find_tournament(t_id)

    if not t:
        await query.edit_message_text("That tournament is no longer available.")
        return

    players = get_players()
    entries = get_entries()
    uid = str(user.id)

    if uid not in players:
        players[uid] = {
            "username": user.username or user.full_name,
            "joined_at": datetime.utcnow().isoformat(),
            "entries": 0,
            "total_buyins": 0.0,
        }

    buy_in = float(t["buy_in"])
    players[uid]["entries"] = players[uid].get("entries", 0) + 1
    players[uid]["total_buyins"] = players[uid].get(
        "total_buyins", 0.0
    ) + buy_in
    save_players(players)

    entry = {
        "user_id": uid,
        "username": user.username or user.full_name,
        "tournament_id": t["id"],
        "tournament_name": t["name"],
        "buy_in": buy_in,
        "timestamp": datetime.utcnow().isoformat(),
    }
    entries.append(entry)
    save_entries(entries)

    prize_pool = buy_in * t.get("prize_pool_pct", 0.75)

    text = (
        f"✅ Logged entry for {t['name']}.\n\n"
        f"Buy-in: ${buy_in:.2f}\n"
        f"Prize pool contribution (@{t.get('prize_pool_pct', 0.75)*100:.0f}%): "
        f"${prize_pool:.2f}\n\n"
        "You still collect the real money yourself; this bot just tracks who is in and total buy-ins."
    )

    keyboard = [
        [InlineKeyboardButton("📜 View Tournaments", callback_data="menu_tournaments")],
        [InlineKeyboardButton("📊 My Stats", callback_data="menu_stats")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_main")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def callbacks_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "menu_tournaments":
        await show_tournament_menu(update, context)
    elif data == "menu_main":
        await show_main_menu(update, context)
    elif data == "menu_stats":
        await show_stats_menu(update, context)
    elif data.startswith("join_"):
        t_id = data.split("join_", 1)[1]
        await handle_join(update, context, t_id)
    else:
        await query.answer("Unknown option", show_alert=True)


# ---------- MAIN ----------

async def run_bot():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("tournaments", tournaments_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(callbacks_router))

    print("Bot starting polling...")
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(run_bot())
