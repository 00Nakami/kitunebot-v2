# cogs/english.py
import json, os, random, asyncio, discord
from discord.ext import commands
from discord import app_commands
from db import get_user_row, update_user
from constants import GUILD_ID, QUIZ_REWARD_MIN, QUIZ_REWARD_MAX
from utils import fmt_compact, sanitize_to_hiragana_core, is_hiragana_strict_after_sanitize

# 実行パスに関係なく読み込めるよう、絶対パスを使用
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "english_easy.json")

def guild_decorator():
    return app_commands.guilds(discord.Object(id=int(GUILD_ID))) if GUILD_ID else (lambda f: f)

class EnglishCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.qa = self._load_data()

    def _load_data(self):
        """data/english_easy.json から単語データをロード"""
        try:
            full_path = os.path.abspath(DATA_PATH)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                valid = [q for q in data if isinstance(q, dict) and "en" in q and "ja" in q]
                if valid:
                    print(f"[EnglishCog] Loaded {len(valid)} entries from {full_path}")
                    return valid
            print(f"[EnglishCog] ⚠️ ファイルが存在しないか形式不正: {full_path}")
        except Exception as e:
            print(f"[EnglishCog] ⚠️ JSON読み込み失敗: {e}")

        # フォールバック
        return [
            {"en": "apple", "ja": "りんご"},
            {"en": "dog", "ja": "いぬ"},
            {"en": "cat", "ja": "ねこ"},
            {"en": "water", "ja": "みず"},
            {"en": "milk", "ja": "みるく"},
        ]

    @app_commands.command(
        name="english",
        description="英語の問題に正解したら cats をゲット！"
    )
    @guild_decorator()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def english(self, interaction: discord.Interaction):
        if not interaction.client.intents.message_content:
            await interaction.response.send_message(
                "⚠️ Botの **Message Content Intent** が無効です。Dev PortalでONにして再起動してください。",
                ephemeral=True
            )
            return

        user = interaction.user
        uid = user.id
        q = random.choice(self.qa)
        word, hira = q["en"], q["ja"]

        await interaction.response.send_message(
            f"🇬🇧 **英単語クイズ**\n"
            f"「**{word}**」を**ひらがな**で答えてください。30秒以内！"
        )

        try:
            question_msg = await interaction.original_response()
        except Exception:
            question_msg = None

        def check(m: discord.Message):
            return (m.author == user) and (m.channel == interaction.channel)

        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            is_timeout = False
        except asyncio.TimeoutError:
            msg = None
            is_timeout = True

        if question_msg:
            try:
                await question_msg.delete()
            except Exception:
                pass

        if is_timeout:
            await interaction.channel.send(f"⏰ 時間切れ！")
            return

        if msg.content == "":
            await interaction.channel.send("⚠️ メッセージ本文を取得できません")
            return

        # sanitize
        user_san = sanitize_to_hiragana_core(msg.content)
        hira_san = sanitize_to_hiragana_core(hira)

        if not is_hiragana_strict_after_sanitize(msg.content):
            await interaction.channel.send(f"❗ ひらがなで答えてね。")
            return

        if user_san == hira_san:
            reward = random.randint(QUIZ_REWARD_MIN, QUIZ_REWARD_MAX)
            c, _, _ = await get_user_row(uid)
            await update_user(uid, credits=c + reward)
            await interaction.channel.send(
                f"✅ **正解！** {user.mention} に **+{fmt_compact(reward)} cats** を付与。"
                f" 新残高：**{fmt_compact(c + reward)} cats**"
            )
        else:
            await interaction.channel.send(f"❌ **不正解！** 正解は **{hira}** でした。")

async def setup(bot: commands.Bot):
    await bot.add_cog(EnglishCog(bot))
