import json
import os
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# === Data paths ===
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

TOURN_FILE = DATA_DIR / "tournament.json"

# === Helpers ===
def load_json(path, default):
    if not path.exists():
        save_json(path, default)
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# === Load tournament on startup ===
tournament_data = load_json(TOURN_FILE, {"tournaments": []})

# === Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the tournament bot!")

async def new_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args) if context.args else "Untitled Tournament"

    # create new tournament object
    tournament = {
        "name": name,
        "players": [],
        "status": "open"
    }

    tournament_data["tournaments"].append(tournament)
    save_json(TOURN_FILE, tournament_data)

    await update.message.reply_text(f"Tournament created: {name}")

async def list_tournaments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tournament_data["tournaments"]:
        await update.message.reply_text("No tournaments found.")
        return

    msg = "Active tournaments:\n"
    for t in tournament_data["tournaments"]:
        msg += f"- {t['name']} ({len(t['players'])} players)\n"

    await update.message.reply_text(msg)

# === Main Bot Runner ===
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_tournament))
    app.add_handler(CommandHandler("list", list_tournaments))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
