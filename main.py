# main.py (Render用)
import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

from db import init_db
from constants import GUILD_ID

# Render用 keep-alive
from keep_alive import keep_alive

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("環境変数 DISCORD_TOKEN を設定してください。")

# ===== Intents =====
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

def guild_decorator():
    return app_commands.guilds(discord.Object(id=int(GUILD_ID))) if GUILD_ID else (lambda f: f)

@bot.event
async def on_ready():
    await init_db()

    await bot.load_extension("cogs.base")
    await bot.load_extension("cogs.luckyblock")
    await bot.load_extension("cogs.daily")
    await bot.load_extension("cogs.math")
    await bot.load_extension("cogs.english")
    await bot.load_extension("cogs.battle")
    await bot.load_extension("cogs.leaderboard")
    await bot.load_extension("cogs.trade")

    if GUILD_ID:
        await bot.tree.sync(guild=discord.Object(id=int(GUILD_ID)))
        print(f"Synced to guild {GUILD_ID}")
    else:
        await bot.tree.sync()
        print("Synced globally")

    print(f"Logged in as {bot.user}")

if __name__ == "__main__":
    keep_alive()   # ← Renderで bot が寝ないようにする
    bot.run(TOKEN)
