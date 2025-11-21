# cogs/luckyblock.py
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button
import aiosqlite

from constants import GUILD_ID, TIERS
from db import get_user_row, update_user, place_in_first_free, free_slots
from utils import fmt_compact, pull_once, base_value

DB_PATH = "luckyblock.db"

# ===== ティア別キャラ一覧 =====
CHARACTERS_BY_TIER = {
    "Mythic": [
        "Spioniro Golubiro", "Tigrilini Watermelini", "Zibra Zubra Zibralini",
        "Carrotini Brainini", "Bananito Bandito"
    ],
    "Brainrot God": [
        "Tigroligre Frutonni", "Orcalero Orcala", "Bulbito Bandito Traktorito",
        "Mastodontico Telepiedone", "Pop Pop Sahur"
    ],
    "Secret": [
        "Torrtuginni Dragonfrutini", "Pot Hotspot", "Esok Sekolah",
        "Spaghetti Tualetti", "La Secret Combinasion"
    ],
    "Admin": [
        "Carloo", "Alessio", "Los Bombinitos", "Crabbo Limonetta",
        "Blackhole Goat", "Guerriro Digitale", "67", "La Grande Combinasion"
    ],
    "Taco": [
        "Chihuanini Taconini", "Gattito Tacoto", "Los Tipi Tacos",
        "Quesadilla Crocodila", "Los Nooo My Hotspotsitos", "Burrito Bandito"
    ],
    "Los": [
        "Los Bombinitos", "Los Tungtungtungcitos", "Los Orcalitos",
        "Los Tipi Tacos", "Los Tortus", "Los Jobcitos",
        "Los Combinasionas", "Los 67"
    ],
    "Los Taco": [
        "Los Chihuahinis", "Los Gattitos", "Los Cucarachas",
        "Los Quesadillas", "Los Burritos"
    ],
    "Spooky": [
        "Mummy Ambalabu", "Cappucino Clownino", "Jackorilla",
        "Pumpkini Spyderini", "Trickolino", "Telemorte",
        "Los Spooky Combinasionas", "La Casa Boo"
    ],

    # === 新ティア ===
    "Cat": [
        "Gattatino Nyanino",
        "Gattatino Neonino",
        "Gattito Tacoto",
        "Los Gattitos",
        "Meowl",
    ],
    "Jandel vs Sammy": [
        "Raccooni Jandelini",
        "Sammyni Spyderini",
    ],
    "Hacker": [
        "1x1x1x1",
        "Guest 666",
    ],
    "Extinct": [
        "Extinct Ballerina",
        "Extinct Tralalero",
        "Extinct Matteo",
        "La Extinct Grande",
    ],
    "Witching Hour": [
        "Vampira Cappucina",
        "Zombie Tralala",
        "Frankentteo",
        "La Vacca Jacko Linterino",
        "La Spooky Grande",
    ],
    "Fishing": [
        "Zombie Tralala",
        "Los Tralaleritos",
        "Boatito Auratito",
        "Extinct Tralalero",
        "Las Tralaleritas",
        "Graipuss Medussi",
        "Tralaledon",
        "Eviledon",
        "Los Primos",
        "Orcaledon",
        "Capitano Moby",
    ],
}

def guild_decorator():
    return app_commands.guilds(discord.Object(id=int(GUILD_ID))) if GUILD_ID else (lambda f: f)

# ===== autosell テーブル操作 =====
async def get_autosell_list(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS autosell (user_id INTEGER, name TEXT, PRIMARY KEY(user_id, name))"
        )
        cur = await db.execute("SELECT name FROM autosell WHERE user_id=?", (uid,))
        rows = await cur.fetchall()
        return [r[0] for r in rows]

async def add_autosell(uid: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO autosell(user_id, name) VALUES(?, ?)", (uid, name))
        await db.commit()

async def remove_autosell(uid: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM autosell WHERE user_id=? AND name=?", (uid, name))
        await db.commit()

async def clear_autosell(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM autosell WHERE user_id=?", (uid,))
        await db.commit()

# ===== 追加UI（/autosell） =====
class TierSelect(Select):
    def __init__(self, user_id: int):
        options = [
            discord.SelectOption(label=tier, description=f"{tier} のブレインロットから追加")
            for tier in CHARACTERS_BY_TIER.keys()
        ]
        super().__init__(placeholder="ラッキーブロックを選択（自動売却に追加）", options=options)
        self.uid = user_id

    async def callback(self, interaction: discord.Interaction):
        tier = self.values[0]
        view = AutoSellAddView(self.uid, tier)
        await interaction.response.edit_message(
            content=f"🎯 **{tier}** ラッキーブロック のキャラを選んでください。",
            view=view
        )

class AutoSellAddSelect(Select):
    def __init__(self, user_id: int, tier: str):
        chars = CHARACTERS_BY_TIER.get(tier, [])
        options = [discord.SelectOption(label=name, description=f"{name} を自動売却に追加") for name in chars]
        super().__init__(placeholder="ブレインロットを選択（追加）", options=options)
        self.uid = user_id

    async def callback(self, interaction: discord.Interaction):
        name = self.values[0]
        await add_autosell(self.uid, name)
        current = await get_autosell_list(self.uid)
        embed = discord.Embed(
            title="🧾 自動売却設定",
            description=f"**{name}** を追加しました。\n現在の対象: {', '.join(current) if current else 'なし'}",
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class AutoSellAddView(View):
    def __init__(self, user_id: int, tier: str):
        super().__init__(timeout=60)
        self.add_item(AutoSellAddSelect(user_id, tier))

class TierSelectView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.add_item(TierSelect(user_id))

# ===== 解除UI（/autosell_disable） =====
class TierSelectDisable(Select):
    """ユーザーが現在登録しているキャラが存在するティアだけを選ばせる"""
    def __init__(self, user_id: int, enabled_by_tier: dict[str, list[str]]):
        options = []
        for tier, names in enabled_by_tier.items():
            if names:  # そのティアに有効な登録がある場合のみ表示
                options.append(discord.SelectOption(label=tier, description=f"{tier} の自動売却を解除"))
        if not options:
            # 何も無いとセレクトが出せないのでダミーを入れる（押せない）
            options = [
                discord.SelectOption(
                    label="（解除対象なし）",
                    description="現在、自動売却に登録されたブレインロットはありません。",
                    default=True
                )
            ]
        super().__init__(placeholder="ラッキーブロックを選択（解除）", options=options)
        self.uid = user_id
        self.enabled_by_tier = enabled_by_tier

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        if chosen == "（解除対象なし）":
            await interaction.response.send_message("解除できる対象がありません。", ephemeral=True)
            return
        view = AutoSellDisableView(self.uid, chosen, self.enabled_by_tier[chosen])
        await interaction.response.edit_message(
            content=f"🧹 **{chosen}** ラッキーブロック の中から解除するブレインロットを選んでください。",
            view=view
        )

class AutoSellDisableSelect(Select):
    """指定ティアのうち、ユーザーが登録しているキャラ名だけを並べる"""
    def __init__(self, user_id: int, tier: str, enabled_names: list[str]):
        options = [discord.SelectOption(label=name, description=f"{name} の自動売却を解除") for name in enabled_names]
        super().__init__(placeholder="ブレインロットを選択（解除）", options=options)
        self.uid = user_id

    async def callback(self, interaction: discord.Interaction):
        name = self.values[0]
        await remove_autosell(self.uid, name)
        current = await get_autosell_list(self.uid)
        embed = discord.Embed(
            title="🧾 自動売却設定",
            description=f"**{name}** の自動売却を解除しました。\n現在の対象: {', '.join(current) if current else 'なし'}",
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class AutoSellDisableAllButton(Button):
    def __init__(self, user_id: int):
        super().__init__(label="全解除", style=discord.ButtonStyle.danger)
        self.uid = user_id

    async def callback(self, interaction: discord.Interaction):
        await clear_autosell(self.uid)
        embed = discord.Embed(
            title="🧾 自動売却設定",
            description="✅ すべての自動売却設定を解除しました。",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class AutoSellDisableView(View):
    def __init__(self, user_id: int, tier: str, enabled_names: list[str]):
        super().__init__(timeout=60)
        # 該当ティアに登録済みのキャラだけを表示
        self.add_item(AutoSellDisableSelect(user_id, tier, enabled_names))
        # 「全解除」ボタンも添える
        self.add_item(AutoSellDisableAllButton(user_id))

class TierSelectDisableView(View):
    def __init__(self, user_id: int, enabled_by_tier: dict[str, list[str]]):
        super().__init__(timeout=60)
        self.add_item(TierSelectDisable(user_id, enabled_by_tier))

# ===== Cog 本体 =====
class LuckyBlockCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- /autosell（追加：ティア→キャラ） ---
    @app_commands.command(
        name="autosell",
        description="ラッキーブロック別に自動売却対象を選択（追加）します。"
    )
    @guild_decorator()
    async def autosell(self, interaction: discord.Interaction):
        view = TierSelectView(interaction.user.id)
        await interaction.response.send_message(
            "🧾 ラッキーブロックを選んでください。",
            view=view,
            ephemeral=True
        )

    # --- /autosell_disable（解除：ティア→キャラ） ---
    @app_commands.command(
        name="autosell_disable",
        description="ラッキーブロック別に自動売却の対象を選択して解除します。"
    )
    @guild_decorator()
    async def autosell_disable(self, interaction: discord.Interaction):
        uid = interaction.user.id
        current = await get_autosell_list(uid)
        # ユーザーが登録しているキャラをティアにマッピング
        enabled_by_tier: dict[str, list[str]] = {t: [] for t in CHARACTERS_BY_TIER.keys()}
        for tier, names in CHARACTERS_BY_TIER.items():
            enabled_by_tier[tier] = [n for n in names if n in current]

        view = TierSelectDisableView(uid, enabled_by_tier)
        await interaction.response.send_message(
            "🧹 ラッキーブロックを選んでください。",
            view=view,
            ephemeral=True
        )

    # 任意：全部一発解除したいときのコマンド
    @app_commands.command(
        name="autosell_disable_all",
        description="自動売却設定をすべて解除します。"
    )
    @guild_decorator()
    async def autosell_disable_all(self, interaction: discord.Interaction):
        await clear_autosell(interaction.user.id)
        await interaction.response.send_message(
            "✅ すべての自動売却設定を解除しました。",
            ephemeral=True
        )

    # --- /luckyblock（自動売却反映、本番結果のみ表示） ---
    @app_commands.command(
        name="luckyblock",
        description="ラッキーブロックを開けます（最大10連）。"
    )
    @app_commands.describe(tier="ラッキーブロックを選択", count="開ける数（1〜10）")
    @app_commands.choices(
        tier=[
            app_commands.Choice(
                name=f"{n} ({fmt_compact(TIERS[n]['cost'])} cats)",
                value=n
            )
            for n in TIERS.keys()
        ]
    )
    @guild_decorator()
    async def luckyblock(
        self,
        interaction: discord.Interaction,
        tier: app_commands.Choice[str],
        count: int = 1
    ):
        tier_name = tier.value
        count = max(1, min(10, count))
        uid = interaction.user.id
        user = interaction.user

        cats, _, _ = await get_user_row(uid)

        # ベース空きチェック
        slots = await free_slots(uid)
        free_count = len(slots)
        if free_count < count:
            await interaction.response.send_message(
                f"📦 ベースの空きが足りません！\n"
                f"空きスロット：{free_count} / 必要スロット：{count}",
                ephemeral=True
            )
            return

        cost = TIERS[tier_name]["cost"] * count
        if cats < cost:
            await interaction.response.send_message(
                f"💸 残高不足：必要 **{fmt_compact(cost)} cats** / "
                f"所持 **{fmt_compact(cats)} cats**",
                ephemeral=True
            )
            return

        # ここで即座にコストを引く
        await update_user(uid, credits=cats - cost)

        autosell_list = await get_autosell_list(uid)
        obtained, sold, total_value, sold_value = [], [], 0, 0

        for _ in range(count):
            name = pull_once(tier_name)
            val = base_value(name)
            if name in autosell_list:
                sold.append((name, val))
                sold_value += val
            else:
                slot = await place_in_first_free(uid, name)
                if slot is not None:
                    obtained.append((name, slot, val))
                    total_value += val

        if sold_value > 0:
            cur, _, _ = await get_user_row(uid)
            await update_user(uid, credits=cur + sold_value)

        # 最終残高（表示用）
        cats_after = cats - cost + sold_value

        # 結果 embed（最初から結果だけ表示）
        embed = discord.Embed(
            title=f"🎁 {user.display_name} の Lucky Block: {tier_name} ×{count}",
            color=TIERS[tier_name]["color"]
        )
        embed.set_thumbnail(url=TIERS[tier_name]["thumbnail"])

        lines = []
        for name, slot, val in obtained:
            lines.append(f"- #{slot:>2} **{name}** 〔{fmt_compact(val)} cats〕")

        if sold:
            lines.append("\n💰 **自動売却:**")
            for name, val in sold:
                lines.append(f"- **{name}** → 売却 +{fmt_compact(val)} cats")

        embed.description = "\n".join(lines) if lines else "（ベース収納なし：すべて自動売却）"
        embed.set_footer(
            text=f"消費: {fmt_compact(cost)} cats / 残高: {fmt_compact(cats_after)} cats"
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(LuckyBlockCog(bot))
