# cogs/math.py
import random, asyncio, discord
from discord.ext import commands
from discord import app_commands
from db import get_user_row, update_user
from constants import GUILD_ID, QUIZ_REWARD_MIN, QUIZ_REWARD_MAX
from utils import fmt_compact, parse_int_loose

def guild_decorator():
    return app_commands.guilds(discord.Object(id=int(GUILD_ID))) if GUILD_ID else (lambda f: f)

class MathCog(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="math",
        description="計算問題に正解したら cats がもらえる！"
    )
    @guild_decorator()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    async def math(self, interaction:discord.Interaction):
        if not interaction.client.intents.message_content:
            await interaction.response.send_message(
                "⚠️ Botの **Message Content Intent** が無効です。Dev PortalでONにして再起動してください。",
                ephemeral=True
            )
            return

        user = interaction.user
        uid = user.id

        kind = random.choice(["add", "sub", "mul"])
        if kind == "add":
            a, b = random.randint(10, 99), random.randint(10, 99)
            q = f"{a}+{b}"
            ans = a + b
        elif kind == "sub":
            a, b = sorted([random.randint(10, 99), random.randint(10, 99)], reverse=True)
            q = f"{a}-{b}"
            ans = a - b
        else:
            a, b = random.randint(1, 9), random.randint(1, 9)
            q = f"{a}×{b}"
            ans = a * b

        await interaction.response.send_message(
            f"🧮 **計算問題**\n```\n{q} = ?\n```\n"
            f"15秒以内に **数字** を送ってください！"
        )
        try:
            question_msg = await interaction.original_response()
        except Exception:
            question_msg = None

        def check(m: discord.Message):
            return (m.author == user) and (m.channel == interaction.channel)

        try:
            msg = await self.bot.wait_for("message", timeout=15.0, check=check)
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

        answered = parse_int_loose(msg.content)
        if answered is None:
            await interaction.channel.send(f"❗ 数字で回答してね")
            return

        if answered == ans:
            reward = random.randint(QUIZ_REWARD_MIN, QUIZ_REWARD_MAX)
            c, _, _ = await get_user_row(uid)
            await update_user(uid, credits=c + reward)
            await interaction.channel.send(
                f"✅ **正解！** {user.mention} に **+{fmt_compact(reward)} cats** を付与。"
                f" 新残高：**{fmt_compact(c + reward)} cats**"
            )
        else:
            await interaction.channel.send(f"❌ **不正解！** 正解は **{ans}** でした。")

async def setup(bot:commands.Bot):
    await bot.add_cog(MathCog(bot))
