# cogs/leaderboard.py
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from constants import GUILD_ID
from db import top_base_values, top_credits
from utils import fmt_compact

def guild_decorator():
    return app_commands.guilds(discord.Object(id=int(GUILD_ID))) if GUILD_ID else (lambda f: f)

async def resolve_display_name(bot: commands.Bot, guild: Optional[discord.Guild], user_id: int) -> Optional[str]:
    if guild:
        member = guild.get_member(user_id)
        if member:
            if member.bot:  # BOT除外
                return None
            return member.display_name
        try:
            member = await guild.fetch_member(user_id)
            if member and not member.bot:
                return member.display_name
            return None
        except Exception:
            pass

    user = bot.get_user(user_id)
    if user:
        if user.bot:
            return None
        return user.name
    try:
        user = await bot.fetch_user(user_id)
        if user and not user.bot:
            return user.name
        return None
    except Exception:
        return None

class LeaderboardCog(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard_base", description="ベースの合計価値ランキング")
    @guild_decorator()
    async def leaderboard_base(self, interaction:discord.Interaction):
        rows = await top_base_values(20)
        embed = discord.Embed(title="🏆 Base Value TOP10", color=discord.Color.blurple())

        desc_lines=[]; rank=0
        for uid, total in rows:
            name = await resolve_display_name(self.bot, interaction.guild, uid)
            if not name: continue
            rank += 1
            desc_lines.append(f"{rank}. **{name}**\n{fmt_compact(total)} cats")
            if rank >= 10: break

        embed.description = "\n".join(desc_lines) if desc_lines else "（Bot以外のデータなし）"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard_cats", description="所持 cats ランキング")
    @guild_decorator()
    async def leaderboard_kits(self, interaction:discord.Interaction):
        rows = await top_credits(20)
        embed = discord.Embed(title="💰 Cats TOP10", color=discord.Color.gold())

        desc_lines=[]; rank=0
        for uid, bal in rows:
            name = await resolve_display_name(self.bot, interaction.guild, uid)
            if not name: continue
            rank += 1
            desc_lines.append(f"{rank}. **{name}**\n{fmt_compact(bal)} cats")
            if rank >= 10: break

        embed.description = "\n".join(desc_lines) if desc_lines else "（Bot以外のデータなし）"
        await interaction.response.send_message(embed=embed)

async def setup(bot:commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
