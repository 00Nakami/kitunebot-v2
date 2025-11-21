# cogs/base.py
import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

from constants import GUILD_ID
from db import get_user_row, update_user, list_base, remove_from_slot
from utils import fmt_compact, base_value

DB_PATH = "luckyblock.db"


def guild_decorator():
    return app_commands.guilds(discord.Object(id=int(GUILD_ID))) if GUILD_ID else (lambda f: f)


# ===== お気に入りスロット用テーブル =====
async def ensure_favorite_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                slot    INTEGER NOT NULL,
                PRIMARY KEY(user_id, slot)
            )
            """
        )
        await db.commit()


async def get_favorites(uid: int):
    await ensure_favorite_table()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT slot FROM favorites WHERE user_id=?", (uid,))
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def add_favorite(uid: int, slot: int):
    await ensure_favorite_table()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO favorites(user_id, slot) VALUES(?, ?)",
            (uid, slot),
        )
        await db.commit()


async def remove_favorite(uid: int, slot: int):
    await ensure_favorite_table()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM favorites WHERE user_id=? AND slot=?",
            (uid, slot),
        )
        await db.commit()


async def clear_favorites(uid: int):
    await ensure_favorite_table()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM favorites WHERE user_id=?", (uid,))
        await db.commit()


class BaseCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- /base : ベース表示（公開・価値つき・⭐はお気に入り） ---
    @app_commands.command(
        name="base",
        description="ベース（1〜25スロット）を表示します。"
    )
    @app_commands.describe(user="相手）")
    @guild_decorator()
    async def base(self, interaction: discord.Interaction, user: discord.Member | None = None):
        target = user or interaction.user
        uid = target.id

        rows = await list_base(uid)  # [(slot, name), ...]
        favs = await get_favorites(uid)

        total_value = 0
        lines = []
        empty_count = 0

        for slot, name in rows:
            fav_mark = "⭐" if slot in favs else ""
            if name:
                val = base_value(name)
                total_value += val
                lines.append(f"{slot:>2}. **{name}** {fav_mark} 〔{fmt_compact(val)} cats〕")
            else:
                empty_count += 1
                lines.append(f"{slot:>2}. （空） {fav_mark}")

        embed = discord.Embed(
            title=f"🏠 {target.display_name} のベース",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"合計価値：{fmt_compact(total_value)} cats｜空き：{empty_count}/25")
        # 公開送信
        await interaction.response.send_message(embed=embed, ephemeral=False)

    # --- /favorite : スロットをお気に入り登録 ---
    @app_commands.command(
        name="favorite",
        description="好きなブレインロットをお気に入り登録します。"
    )
    @app_commands.describe(slot="お気に入り登録したいスロット番号（1〜25）")
    @guild_decorator()
    async def favorite(self, interaction: discord.Interaction, slot: int):
        uid = interaction.user.id
        if not (1 <= slot <= 25):
            await interaction.response.send_message(
                "❌ スロット番号は **1〜25** で指定してください。", ephemeral=True
            )
            return

        rows = await list_base(uid)
        name_by_slot = {s: n for s, n in rows}
        name = name_by_slot.get(slot)
        if not name:
            await interaction.response.send_message(
                "❌ そのスロットは空です。ブレインロットが入っているスロットを指定してください。",
                ephemeral=True,
            )
            return

        await add_favorite(uid, slot)
        await interaction.response.send_message(
            f"⭐ スロット {slot}（{name}）をお気に入り登録しました。\n"
            f"このスロットにいるキャラクターは `/sell` や `/sell_all` では売却されません。",
            ephemeral=True,
        )

    # --- /unfavorite : お気に入り解除 ---
    @app_commands.command(
        name="unfavorite",
        description="指定したスロットにいるブレインロットのお気に入り登録を解除します。"
    )
    @app_commands.describe(slot="解除したいスロット番号（1〜25）")
    @guild_decorator()
    async def unfavorite(self, interaction: discord.Interaction, slot: int):
        uid = interaction.user.id
        favs = await get_favorites(uid)
        if slot not in favs:
            await interaction.response.send_message(
                "⚠️ そのスロットにいるブレインロットはお気に入り登録されていません。",
                ephemeral=True,
            )
            return

        await remove_favorite(uid, slot)
        await interaction.response.send_message(
            f"🗑️ スロット {slot} にいるブレインロットのお気に入り登録を解除しました。",
            ephemeral=True,
        )

    # --- /sell : 単体売却（お気に入りは売れない） ---
    @app_commands.command(
        name="sell",
        description="指定したスロットのブレインロットを売却します。"
    )
    @app_commands.describe(slot="売却したいスロット番号（1〜25）")
    @guild_decorator()
    async def sell(self, interaction: discord.Interaction, slot: int):
        uid = interaction.user.id
        if not (1 <= slot <= 25):
            await interaction.response.send_message(
                "❌ スロット番号は **1〜25** で指定してください。",
                ephemeral=True,
            )
            return

        favs = await get_favorites(uid)
        if slot in favs:
            await interaction.response.send_message(
                "🚫 このブレインロットはお気に入り登録されているため売却できません。",
                ephemeral=True,
            )
            return

        rows = await list_base(uid)
        name_by_slot = {s: n for s, n in rows}
        name = name_by_slot.get(slot)
        if not name:
            await interaction.response.send_message(
                "❌ このスロットは空です。",
                ephemeral=True,
            )
            return

        val = base_value(name)
        await remove_from_slot(uid, slot)
        credits, _, _ = await get_user_row(uid)
        new_credits = credits + val
        await update_user(uid, credits=new_credits)

        await interaction.response.send_message(
            f"✅ **{name}** を売却しました。\n"
            f"受取：**{fmt_compact(val)} cats**\n"
            f"新残高：**{fmt_compact(new_credits)} cats**",
            ephemeral=True,
        )

    # --- /sell_all : お気に入り以外を一括売却 ---
    @app_commands.command(
        name="sell_all",
        description="お気に入り登録されていないブレインロットを全て売却します。"
    )
    @guild_decorator()
    async def sell_all(self, interaction: discord.Interaction):
        uid = interaction.user.id
        rows = await list_base(uid)
        favs = await get_favorites(uid)

        total_value = 0
        sold_names = []

        for slot, name in rows:
            if not name:
                continue
            if slot in favs:
                continue  # お気に入りはスキップ
            total_value += base_value(name)
            sold_names.append(name)
            await remove_from_slot(uid, slot)

        if not sold_names:
            await interaction.response.send_message(
                "⚠️ 売却できるブレインロットがありません（すべて空 or お気に入り）。",
                ephemeral=True,
            )
            return

        credits, _, _ = await get_user_row(uid)
        new_credits = credits + total_value
        await update_user(uid, credits=new_credits)

        listed = ", ".join(sold_names[:10])
        if len(sold_names) > 10:
            listed += " 他..."

        embed = discord.Embed(
            title="💸 一括売却完了",
            description=(
                f"お気に入りを除くブレインロットを売却しました。\n"
                f"合計：**{fmt_compact(total_value)} cats** を獲得\n"
                f"新残高：**{fmt_compact(new_credits)} cats**"
            ),
            color=discord.Color.gold(),
        )
        embed.add_field(name="売却したブレインロット", value=listed, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(BaseCog(bot))
