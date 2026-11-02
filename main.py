import os
import random
import sqlite3
from pathlib import Path

from bale import Bot, Message
from bale.handlers import CommandHandler

TOKEN = os.getenv("BALE_BOT_TOKEN")
DB_PATH = Path(os.getenv("DATABASE_PATH", "atlain_bale.db"))


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                gold INTEGER NOT NULL DEFAULT 500,
                soldiers INTEGER NOT NULL DEFAULT 50,
                level INTEGER NOT NULL DEFAULT 1,
                wins INTEGER NOT NULL DEFAULT 0
            )
        """)


def get_player(user):
    uid = str(user.id)
    with connect_db() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE user_id = ?", (uid,)
        ).fetchone()
        if row is None:
            name = getattr(user, "first_name", None) or "فرمانده"
            conn.execute(
                "INSERT INTO players (user_id, name) VALUES (?, ?)",
                (uid, name),
            )
            row = conn.execute(
                "SELECT * FROM players WHERE user_id = ?", (uid,)
            ).fetchone()
        return dict(row)


def country_text(player):
    return (
        f"🏰 کشور {player['name']}\n\n"
        f"🪙 طلا: {player['gold']}\n"
        f"🪖 نیروها: {player['soldiers']}\n"
        f"⭐ سطح: {player['level']}\n"
        f"🏆 موفقیت‌ها: {player['wins']}"
    )


def uid_of(message):
    return str(message.author.id)


def change_player(uid, sql, values=()):
    with connect_db() as conn:
        conn.execute(sql, (*values, uid))


bot = Bot(token=TOKEN or "TOKEN_NOT_SET")


@bot.handle(CommandHandler("start"))
async def start_command(message: Message):
    player = get_player(message.author)
    await message.reply(
        f"🌍 به جنگ جهانی آتلاین خوش آمدی، {player['name']}!\n\n"
        "تو فرمانده یک کشور خیالی هستی. طلا جمع کن، کشورت را توسعه بده "
        "و مأموریت‌های داستانی انجام بده.\n\n"
        "دستورها:\n"
        "/country - نمایش کشور\n"
        "/stats - آمار کشور\n"
        "/recruit - جذب نیرو (۱۰۰ طلا برای ۱۰ نیرو)\n"
        "/upgrade - توسعه کشور\n"
        "/mission - مأموریت داستانی\n"
        "/help - راهنما"
    )


@bot.handle(CommandHandler("help"))
async def help_command(message: Message):
    await message.reply(
        "📘 راهنمای جنگ جهانی آتلاین\n"
        "/start - شروع بازی\n"
        "/country یا /stats - آمار کشور\n"
        "/recruit - خرید ۱۰ نیرو با ۱۰۰ طلا\n"
        "/upgrade - ارتقای سطح کشور\n"
        "/mission - انجام مأموریت داستانی"
    )


@bot.handle(CommandHandler("country"))
async def country_command(message: Message):
    player = get_player(message.author)
    await message.reply(country_text(player))


@bot.handle(CommandHandler("stats"))
async def stats_command(message: Message):
    player = get_player(message.author)
    await message.reply(country_text(player))


@bot.handle(CommandHandler("recruit"))
async def recruit_command(message: Message):
    player = get_player(message.author)
    uid = uid_of(message)
    cost = 100
    if player["gold"] < cost:
        await message.reply(f"❌ طلا کافی نیست؛ جذب نیرو {cost} طلا هزینه دارد.")
        return

    change_player(
        uid,
        "UPDATE players SET gold = gold - ?, soldiers = soldiers + 10 WHERE user_id = ?",
        (cost,),
    )
    player = get_player(message.author)
    await message.reply(
        "🪖 ۱۰ نیروی جدید به کشور تو پیوستند! (هزینه: ۱۰۰ طلا)\n\n"
        + country_text(player)
    )


@bot.handle(CommandHandler("upgrade"))
async def upgrade_command(message: Message):
    player = get_player(message.author)
    uid = uid_of(message)
    cost = player["level"] * 250
    if player["gold"] < cost:
        await message.reply(f"❌ برای توسعه سطح بعدی به {cost} طلا نیاز داری.")
        return

    change_player(
        uid,
        "UPDATE players SET gold = gold - ?, level = level + 1 WHERE user_id = ?",
        (cost,),
    )
    player = get_player(message.author)
    await message.reply(
        f"🏗️ کشور تو توسعه پیدا کرد! سطح جدید: {player['level']}\n\n"
        + country_text(player)
    )


@bot.handle(CommandHandler("mission"))
async def mission_command(message: Message):
    player = get_player(message.author)
    uid = uid_of(message)
    if player["soldiers"] < 5:
        await message.reply("❌ برای این مأموریت داستانی حداقل ۵ نیرو لازم داری.")
        return

    success = random.random() < min(0.9, 0.45 + player["level"] * 0.08)
    if success:
        reward = random.randint(80, 180)
        change_player(
            uid,
            "UPDATE players SET gold = gold + ?, soldiers = soldiers - 5, "
            "wins = wins + 1 WHERE user_id = ?",
            (reward,),
        )
        result = (
            "🧭 مأموریت داستانی با موفقیت تمام شد!\n"
            f"🪙 پاداش: {reward} طلا\n🪖 هزینه مأموریت: ۵ نیرو"
        )
    else:
        change_player(
            uid,
            "UPDATE players SET soldiers = soldiers - 5 WHERE user_id = ?",
        )
        result = "🌧️ این مأموریت داستانی موفق نبود؛ ۵ نیرو برای سفر و تدارکات مصرف شد."

    player = get_player(message.author)
    await message.reply(result + "\n\n" + country_text(player))


def main():
    if not TOKEN:
        raise RuntimeError(
            "توکن بله تنظیم نشده است. متغیر BALE_BOT_TOKEN را تنظیم کن."
        )
    init_db()
    print("Atlain World War Bale bot is starting...")
    bot.run()


if __name__ == "__main__":
    main()
