# cogs/battle.py
import discord, random
from discord.ext import commands
from discord import app_commands

from constants import GUILD_ID, TIERS
from db import get_user_row, update_user
from utils import fmt_compact, pull_once, base_value

def guild_decorator():
    return app_commands.guilds(discord.Object(id=int(GUILD_ID))) if GUILD_ID else (lambda f: f)

# ティア選択時に「名前（価格）」が表示されるようにする
TIER_CHOICES = []
for name, data in TIERS.items():
    cost = data["cost"]
    label = f"{name} ({fmt_compact(cost)} cats)"  # 例: Mythic (2.5m cats)
    TIER_CHOICES.append(app_commands.Choice(name=label, value=name))

MODE_CHOICES = [
    app_commands.Choice(name="NPC", value="npc"),
    app_commands.Choice(name="Player", value="player"),
]


class BattleRequestView(discord.ui.View):
    """Playerモードの対戦承認用ビュー"""
    def __init__(self, requester: discord.User, opponent: discord.User, state: dict):
        super().__init__(timeout=60)
        self.requester = requester
        self.opponent = opponent
        self.state = state

    @discord.ui.button(label="対戦を承認", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "このボタンは招待された相手のみ操作できます。",
                ephemeral=True
            )
            return
        self.state["accepted"] = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(
            content="✅ 対戦が承認されました。結果が出るまでお待ちください…",
            view=self
        )

    @discord.ui.button(label="拒否", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "このボタンは招待された相手のみ操作できます。",
                ephemeral=True
            )
            return
        self.state["accepted"] = False
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(
            content="❌ 対戦は拒否されました。",
            view=self
        )


class BattleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="luckyblock_battle",
        description="ラッキーブロックを開けて、出たブレインロットの価値で競います"
    )
    @app_commands.describe(
        mode="対戦相手の種類（NPC / Player）",
        tier="開けるラッキーブロック",
        count="開ける数（1〜10）",
        opponent="対戦相手"
    )
    @app_commands.choices(mode=MODE_CHOICES, tier=TIER_CHOICES)
    @guild_decorator()
    async def luckyblock_battle(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
        tier: app_commands.Choice[str],
        count: int = 1,
        opponent: discord.User | None = None
    ):
        mode_val = mode.value            # "npc" or "player"
        tier_name = tier.value
        count = max(1, min(10, count))
        user = interaction.user
        uid = user.id

        # ---- 入力検証（モード別） ----------------------------------------
        if mode_val == "player":
            if opponent is None:
                await interaction.response.send_message(
                    "❗ Playerモードでは `opponent` が必須です。",
                    ephemeral=True
                )
                return
            if opponent.bot:
                await interaction.response.send_message(
                    "❗ BOTとは対戦できません。",
                    ephemeral=True
                )
                return
            if opponent.id == uid:
                await interaction.response.send_message(
                    "❗ 自分自身とは対戦できません。",
                    ephemeral=True
                )
                return

        # ---- コスト確認（自分） ------------------------------------------
        my_cats, _, _ = await get_user_row(uid)
        cost_each = TIERS[tier_name]["cost"] * count
        if my_cats < cost_each:
            await interaction.response.send_message(
                f"💸 あなたの残高不足：必要 **{fmt_compact(cost_each)} cats** / 所持 **{fmt_compact(my_cats)} cats**",
                ephemeral=True
            )
            return

        # ---- NPC モード ---------------------------------------------------
        if mode_val == "npc":
            # 先に自分のコストだけ徴収
            await update_user(uid, credits=my_cats - cost_each)

            # 開封（ベースには入れない。対戦用の一時結果）
            my_list  = [pull_once(tier_name) for _ in range(count)]
            npc_list = [pull_once(tier_name) for _ in range(count)]
            my_total  = sum(base_value(n) for n in my_list)
            npc_total = sum(base_value(n) for n in npc_list)
            pot = my_total + npc_total

            # 決着
            if my_total > npc_total:
                cur, _, _ = await get_user_row(uid)
                await update_user(uid, credits=cur + pot)
                result = f"🏆 **{user.display_name} の勝ち！** 〔+{fmt_compact(pot)} cats〕"
            elif my_total < npc_total:
                result = f"🤖 **NPC の勝ち！** あなたのお金は没収されました！"
            else:
                # 引き分け：半分返金（NPCは受け取りなし）
                half = pot // 2
                cur, _, _ = await get_user_row(uid)
                await update_user(uid, credits=cur + half)
                result = f"🤝 **引き分け**：あなたに **{fmt_compact(half)} cats** を返金"

            # 表示
            def fmt_lines(owner, names, total):
                head = f"**{owner}**（合計 {fmt_compact(total)} cats）"
                body = "\n".join([f"- {n} 〔{fmt_compact(base_value(n))}〕" for n in names])
                return head + "\n" + body

            desc = (
                f"{fmt_lines(user.display_name, my_list, my_total)}\n\n"
                f"{fmt_lines('NPC', npc_list, npc_total)}\n\n"
                f"{result}"
            )
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"⚔️ LuckyBlock Battle — NPC / {tier_name} ×{count}",
                    description=desc, color=0x2ecc71
                )
            )
            return

        # ---- Player モード ------------------------------------------------
        # 相手側の所持確認（事前照会）
        opp_id = opponent.id
        opp_name = opponent.display_name if interaction.guild else opponent.name
        opp_cats, _, _ = await get_user_row(opp_id)
        if opp_cats < cost_each:
            await interaction.response.send_message(
                f"💸 相手の残高不足（{opp_name}）：必要 **{fmt_compact(cost_each)} cats** / 所持 **{fmt_compact(opp_cats)} cats**",
                ephemeral=True
            )
            return

        # 対戦リクエスト（承認UI）
        state = {"accepted": False}
        view = BattleRequestView(user, opponent, state)

        await interaction.response.send_message(
            content=(
                f"🎮 **{user.mention}** が **{opponent.mention}** を対戦に招待しました！\n"
                f"ルール：{tier_name} ×{count}（参加費：各 **{fmt_compact(cost_each)} cats**）\n"
                f"※60秒以内に承認してください"
            ),
            view=view
        )
        await view.wait()

        if not state["accepted"]:
            # 未承認 or 拒否 or タイムアウト
            await interaction.edit_original_response(
                content="⌛ キャンセル：未承認/拒否/タイムアウト。",
                view=None
            )
            return

        # 最終チェック（承認中に残高が動いていないか）
        my_cats, _, _ = await get_user_row(uid)
        opp_cats, _, _ = await get_user_row(opp_id)
        if my_cats < cost_each:
            await interaction.edit_original_response(
                content="❗ あなたの残高が不足しました。対戦をキャンセルします。",
                view=None
            )
            return
        if opp_cats < cost_each:
            await interaction.edit_original_response(
                content=f"❗ {opp_name} の残高が不足しました。対戦をキャンセルします。",
                view=None
            )
            return

        # 両者から参加費を徴収
        await update_user(uid, credits=my_cats - cost_each)
        await update_user(opp_id, credits=opp_cats - cost_each)

        # 開封（ベースには入れない）
        def do_open():
            names = [pull_once(tier_name) for _ in range(count)]
            total = sum(base_value(n) for n in names)
            return names, total

        my_list,  my_total  = do_open()
        opp_list, opp_total = do_open()
        pot = my_total + opp_total

        # 勝敗・配分
        if my_total > opp_total:
            cur, _, _ = await get_user_row(uid)
            await update_user(uid, credits=cur + pot)
            result = f"🏆 **{user.display_name} の勝ち！** 〔+{fmt_compact(pot)} cats〕"
        elif my_total < opp_total:
            cur, _, _ = await get_user_row(opp_id)
            await update_user(opp_id, credits=cur + pot)
            result = f"🏆 **{opp_name} の勝ち！** 〔+{fmt_compact(pot)} cats〕"
        else:
            half = pot // 2
            cur, _, _ = await get_user_row(uid)
            await update_user(uid, credits=cur + half)
            cur, _, _ = await get_user_row(opp_id)
            await update_user(opp_id, credits=cur + (pot - half))
            result = f"🤝 **引き分け**：両者に **{fmt_compact(half)} cats** を返金"

        # 表示
        def fmt_lines(owner, names, total):
            head = f"**{owner}**（合計 {fmt_compact(total)} cats）"
            body = "\n".join([f"- {n} 〔{fmt_compact(base_value(n))}〕" for n in names])
            return head + "\n" + body

        embed = discord.Embed(
            title=f"⚔️ LuckyBlock Battle — Player / {tier_name} ×{count}",
            description=(
                f"{fmt_lines(user.display_name, my_list, my_total)}\n\n"
                f"{fmt_lines(opp_name, opp_list, opp_total)}\n\n"
                f"{result}"
            ),
            color=0x9b59b6
        )
        await interaction.edit_original_response(content=None, view=None, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(BattleCog(bot))
