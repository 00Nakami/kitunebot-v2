# cogs/daily.py
import time, discord
from discord.ext import commands
from discord import app_commands
from constants import DAILY_COOLDOWN_SECONDS, DAILY_BASE_INC, GUILD_ID, GIVE_MIN_AMOUNT
from db import get_user_row, update_user, get_daily_count, increment_daily_count
from utils import fmt_remain, fmt_compact

def guild_decorator():
    return app_commands.guilds(discord.Object(id=int(GUILD_ID))) if GUILD_ID else (lambda f: f)

class DailyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="daily",
        description="12時間ごとに受け取り可能"
    )
    @guild_decorator()
    async def daily(self, interaction: discord.Interaction):
        uid = interaction.user.id
        cats, _, last = await get_user_row(uid)
        now = int(time.time())

        # クールダウン判定
        if (last + DAILY_COOLDOWN_SECONDS) > now:
            await interaction.response.send_message(
                f"⏳ 次は {fmt_remain(last + DAILY_COOLDOWN_SECONDS - now)} 後に受取できます。",
                ephemeral=True
            )
            return

        # 受取回数に応じて増える報酬
        current_count = await get_daily_count(uid)
        reward = (current_count + 1) * DAILY_BASE_INC

        new_cats = cats + reward
        await update_user(uid, credits=new_cats, last_daily=now)
        new_count = await increment_daily_count(uid)

        await interaction.response.send_message(
            f"✅ デイリー受取（{new_count} 回目）！ **+{fmt_compact(reward)} cats** を付与。\n"
            f"💳 新残高：**{fmt_compact(new_cats)} cats**"
        )

    @app_commands.command(name="give", description="他のユーザーに cats を送れます（最低100M cats）")
    @app_commands.describe(user="送り先", amount="送る金額（100M以上）")
    @guild_decorator()
    async def give(self, interaction:discord.Interaction, user:discord.User, amount:int):
        if amount < GIVE_MIN_AMOUNT:
            await interaction.response.send_message(f"❗ 最低送金額は {fmt_compact(GIVE_MIN_AMOUNT)} cats です。", ephemeral=True); return

        sender = interaction.user

        # ★ 追加：BOT には送れない
        if user.bot:
            await interaction.response.send_message("❗ BOTには送金できません。", ephemeral=True)
            return

        if user.id == sender.id:
            await interaction.response.send_message("❗ 自分自身には送れません。", ephemeral=True); return

        s_bal,_,_ = await get_user_row(sender.id)
        if s_bal < amount:
            await interaction.response.send_message(
                f"💳 残高不足（所持 {fmt_compact(s_bal)} cats < 送金 {fmt_compact(amount)} cats）",
                ephemeral=True
            )
            return

        r_bal,_,_ = await get_user_row(user.id)
        await update_user(sender.id, credits=s_bal-amount)
        await update_user(user.id, credits=r_bal+amount)

        await interaction.response.send_message(
            f"✅ {user.mention} に {fmt_compact(amount)} cats を送金しました。\n"
            f"あなた残高：{fmt_compact(s_bal-amount)} cats / 相手残高：{fmt_compact(r_bal+amount)} cats",
            ephemeral=True
        )

    @app_commands.command(
        name="cats",
        description="持っている cats を確認します。"
    )
    @app_commands.describe(
        user="相手"
    )
    @guild_decorator()
    async def cats(self, interaction: discord.Interaction, user: discord.User | None = None):
        target = user or interaction.user
        bal, _, _ = await get_user_row(target.id)

        # 公開で表示（ephemeral=False）
        await interaction.response.send_message(
            f"💰 **{target.display_name}** の所持金：**{fmt_compact(bal)} cats**"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(DailyCog(bot))
