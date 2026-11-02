import os
import random
import sqlite3
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = Path(os.getenv("DATABASE_PATH", "atlain.db"))


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                gold INTEGER NOT NULL DEFAULT 500,
                soldiers INTEGER NOT NULL DEFAULT 50,
                level INTEGER NOT NULL DEFAULT 1,
                wins INTEGER NOT NULL DEFAULT 0
            )
        """)


def get_player(user):
    with connect_db() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE user_id = ?", (user.id,)
        ).fetchone()
        if row is None:
            name = user.first_name or "فرمانده"
            conn.execute(
                "INSERT INTO players (user_id, name) VALUES (?, ?)",
                (user.id, name),
            )
            row = conn.execute(
                "SELECT * FROM players WHERE user_id = ?", (user.id,)
            ).fetchone()
        return dict(row)


def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 کشور من", callback_data="country"),
         InlineKeyboardButton("📊 آمار", callback_data="stats")],
        [InlineKeyboardButton("🪖 جذب نیرو", callback_data="recruit"),
         InlineKeyboardButton("🏗️ توسعه کشور", callback_data="upgrade")],
        [InlineKeyboardButton("🧭 مأموریت داستانی", callback_data="mission")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player = get_player(update.effective_user)
    await update.effective_message.reply_text(
        f"🌍 به **جنگ جهانی آتلاین** خوش آمدی، {player['name']}!\n\n"
        "تو فرمانده یک کشور خیالی هستی. منابع جمع کن، کشورت را توسعه بده "
        "و در مأموریت‌های داستانی شرکت کن.\n\n"
        "از دکمه‌های زیر شروع کن.",
        reply_markup=keyboard(),
        parse_mode="Markdown",
    )


async def show_country(query, player):
    text = (
        f"🏰 کشور {player['name']}\n\n"
        f"🪙 طلا: {player['gold']}\n"
        f"🪖 نیروها: {player['soldiers']}\n"
        f"⭐ سطح: {player['level']}\n"
        f"🏆 موفقیت‌ها: {player['wins']}"
    )
    await query.edit_message_text(text, reply_markup=keyboard())


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    player = get_player(query.from_user)
    uid = query.from_user.id

    if query.data in ("country", "stats"):
        await show_country(query, player)

    elif query.data == "recruit":
        cost = 100
        if player["gold"] < cost:
            text = f"❌ طلا کافی نیست. جذب نیرو {cost} طلا هزینه دارد."
        else:
            with connect_db() as conn:
                conn.execute(
                    "UPDATE players SET gold = gold - ?, soldiers = soldiers + 10 "
                    "WHERE user_id = ?", (cost, uid)
                )
            player = get_player(query.from_user)
            text = "🪖 ۱۰ نیروی جدید به کشور تو پیوستند! (هزینه: ۱۰۰ طلا)"
        await query.edit_message_text(text, reply_markup=keyboard())

    elif query.data == "upgrade":
        cost = player["level"] * 250
        if player["gold"] < cost:
            text = f"❌ برای توسعه سطح بعدی به {cost} طلا نیاز داری."
        else:
            with connect_db() as conn:
                conn.execute(
                    "UPDATE players SET gold = gold - ?, level = level + 1 "
                    "WHERE user_id = ?", (cost, uid)
                )
            player = get_player(query.from_user)
            text = f"🏗️ کشور تو توسعه پیدا کرد! سطح جدید: {player['level']}"
        await query.edit_message_text(text, reply_markup=keyboard())

    elif query.data == "mission":
        # A fictional, abstract, turn-based story encounter.
        if player["soldiers"] < 5:
            text = "❌ برای این مأموریت داستانی حداقل ۵ نیرو لازم داری."
        else:
            success = random.random() < min(0.9, 0.45 + player["level"] * 0.08)
            if success:
                reward = random.randint(80, 180)
                with connect_db() as conn:
                    conn.execute(
                        "UPDATE players SET gold = gold + ?, soldiers = soldiers - 5, "
                        "wins = wins + 1 WHERE user_id = ?",
                        (reward, uid),
                    )
                text = (
                    "🧭 مأموریت داستانی با موفقیت تمام شد!\n"
                    f"🪙 پاداش: {reward} طلا\n🪖 هزینه مأموریت: ۵ نیرو"
                )
            else:
                with connect_db() as conn:
                    conn.execute(
                        "UPDATE players SET soldiers = soldiers - 5 WHERE user_id = ?",
                        (uid,),
                    )
                text = "🌧️ مأموریت این بار موفق نبود؛ ۵ نیرو برای سفر و تدارکات مصرف شد."
        await query.edit_message_text(text, reply_markup=keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "دستورها:\n/start - شروع بازی\n/help - راهنما"
    )


def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است. آن را در متغیر محیطی BOT_TOKEN قرار بده."
        )
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(buttons))
    print("Atlain World War bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
