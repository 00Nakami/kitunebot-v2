# cogs/trade.py
import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

from constants import GUILD_ID
from db import get_slot_name, set_slot_value
from utils import base_value, fmt_compact  # base_value が utils にある前提

DB_PATH = "luckyblock.db"


def guild_decorator():
    return app_commands.guilds(discord.Object(id=int(GUILD_ID))) if GUILD_ID else (lambda f: f)


# ===== お気に入り解除用（base.py と同じテーブルを使う） =====
async def remove_favorite(uid: int, slot: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # 念のためテーブルが無い場合に備えて作成
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                slot    INTEGER NOT NULL,
                PRIMARY KEY(user_id, slot)
            )
            """
        )
        await db.execute(
            "DELETE FROM favorites WHERE user_id=? AND slot=?",
            (uid, slot),
        )
        await db.commit()


# ====== 受信者側の承認ビュー ======
class TradeExecuteView(discord.ui.View):
    def __init__(self, requester: discord.User, target: discord.User,
                 req_slot: int, tgt_slot: int,
                 req_name: str, tgt_name: str):
        super().__init__(timeout=60)
        self.requester = requester
        self.target = target
        self.req_slot = req_slot
        self.tgt_slot = tgt_slot
        self.req_name = req_name
        self.tgt_name = tgt_name

    @discord.ui.button(label="承認する", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                "❌ このトレードの承認権限があるのは招待された相手のみです。",
                ephemeral=True
            )
            return

        # 最新のスロット状況を確認（途中で変わっていないかチェック）
        cur_req_name = await get_slot_name(self.requester.id, self.req_slot)
        cur_tgt_name = await get_slot_name(self.target.id, self.tgt_slot)

        if cur_req_name is None or cur_tgt_name is None:
            for c in self.children:
                c.disabled = True
            await interaction.response.edit_message(
                content="⚠️ いずれかのスロットが空になってしまいました。トレードをキャンセルします。",
                view=self
            )
            self.stop()
            return

        # スワップ実行
        await set_slot_value(self.requester.id, self.req_slot, cur_tgt_name)
        await set_slot_value(self.target.id, self.tgt_slot, cur_req_name)

        # お気に入り解除（仕様：交換後はそのキャラのお気に入りが外れる）
        await remove_favorite(self.requester.id, self.req_slot)
        await remove_favorite(self.target.id, self.tgt_slot)

        for c in self.children:
            c.disabled = True

        # 結果表示
        desc = (
            f"✅ トレード成立！\n\n"
            f"👤 {self.requester.mention}\n"
            f"　スロット {self.req_slot}: **{cur_req_name}** → **{cur_tgt_name}** を受け取り\n\n"
            f"👤 {self.target.mention}\n"
            f"　スロット {self.tgt_slot}: **{cur_tgt_name}** → **{cur_req_name}** を受け取り\n\n"
            f"※ 両スロットの「お気に入り」は解除されました。"
        )

        embed = discord.Embed(
            title="🔁 トレード完了",
            description=desc,
            color=discord.Color.green()
        )

        await interaction.response.edit_message(embed=embed, content=None, view=self)
        self.stop()

    @discord.ui.button(label="拒否する", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                "❌ このトレードの承認権限があるのは招待された相手のみです。",
                ephemeral=True
            )
            return

        for c in self.children:
            c.disabled = True

        await interaction.response.edit_message(
            content="❌ トレードは拒否されました。",
            view=self
        )
        self.stop()


# ====== 送信者側の確認ビュー ======
class TradeConfirmView(discord.ui.View):
    """送信者に、内容を確認させてから相手へ正式なトレードリクエストを送るビュー"""

    def __init__(self, requester: discord.User, target: discord.User,
                 req_slot: int, tgt_slot: int,
                 req_name: str, tgt_name: str):
        super().__init__(timeout=60)
        self.requester = requester
        self.target = target
        self.req_slot = req_slot
        self.tgt_slot = tgt_slot
        self.req_name = req_name
        self.tgt_name = tgt_name

    @discord.ui.button(label="この内容でリクエスト送信", style=discord.ButtonStyle.success)
    async def send_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message(
                "❌ この確認はトレード発行者専用です。",
                ephemeral=True
            )
            return

        # 送信者向けビューを無効化
        for c in self.children:
            c.disabled = True

        await interaction.response.edit_message(
            content="✅ トレードリクエストを相手に送信しました。",
            view=self
        )

        # 相手向けの承認ビューをチャンネルに送信
        desc = (
            f"🔁 **トレードリクエスト**\n\n"
            f"👤 発行者: {self.requester.mention}\n"
            f"👤 相手: {self.target.mention}\n\n"
            f"**{self.requester.display_name} が出すもの**\n"
            f"- スロット {self.req_slot}: **{self.req_name}** 〔{fmt_compact(base_value(self.req_name))} cats〕\n\n"
            f"**{self.target.display_name} が出すもの**\n"
            f"- スロット {self.tgt_slot}: **{self.tgt_name}** 〔{fmt_compact(base_value(self.tgt_name))} cats〕\n\n"
            f"👉 {self.target.mention}、このトレードを承認しますか？"
        )

        embed = discord.Embed(
            title="🔁 トレードリクエスト",
            description=desc,
            color=discord.Color.blurple()
        )

        view = TradeExecuteView(
            requester=self.requester,
            target=self.target,
            req_slot=self.req_slot,
            tgt_slot=self.tgt_slot,
            req_name=self.req_name,
            tgt_name=self.tgt_name
        )

        await interaction.channel.send(embed=embed, view=view)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message(
                "❌ この確認はトレード発行者専用です。",
                ephemeral=True
            )
            return

        for c in self.children:
            c.disabled = True

        await interaction.response.edit_message(
            content="🚫 トレードリクエストをキャンセルしました。",
            view=self
        )
        self.stop()


class TradeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="trade",
        description="他のユーザーとブレインロットを交換します。"
    )
    @app_commands.describe(
        user="交換したい相手",
        my_slot="自分のベーススロット番号（1〜25）",
        their_slot="相手のベーススロット番号（1〜25）"
    )
    @guild_decorator()
    async def trade(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        my_slot: int,
        their_slot: int
    ):
        requester = interaction.user
        target = user

        # 基本チェック
        if requester.id == target.id:
            await interaction.response.send_message(
                "❌ 自分自身とはトレードできません。",
                ephemeral=True
            )
            return
        if target.bot:
            await interaction.response.send_message(
                "❌ BOTとはトレードできません。",
                ephemeral=True
            )
            return
        if not (1 <= my_slot <= 25 and 1 <= their_slot <= 25):
            await interaction.response.send_message(
                "❌ スロット番号は **1〜25** の範囲で指定してください。",
                ephemeral=True
            )
            return

        # スロット内容取得
        my_name = await get_slot_name(requester.id, my_slot)
        their_name = await get_slot_name(target.id, their_slot)

        if not my_name:
            await interaction.response.send_message(
                f"❌ あなたのスロット {my_slot} は空です。",
                ephemeral=True
            )
            return
        if not their_name:
            await interaction.response.send_message(
                f"❌ 相手のスロット {their_slot} は空です。",
                ephemeral=True
            )
            return

        # 送信者向けの確認メッセージ（ephemeral）
        desc = (
            "以下の内容でトレードリクエストを送信しますか？\n\n"
            f"👤 あなた（{requester.display_name}）が出すもの\n"
            f"- スロット {my_slot}: **{my_name}** 〔{fmt_compact(base_value(my_name))} cats〕\n\n"
            f"👤 相手（{target.display_name}）が出すもの\n"
            f"- スロット {their_slot}: **{their_name}** 〔{fmt_compact(base_value(their_name))} cats〕\n\n"
            "※ この確認は **あなたにしか見えません**。\n"
            "「この内容でリクエスト送信」を押すと、相手に承認用メッセージが送られます。"
        )

        embed = discord.Embed(
            title="🔁 トレード内容の確認",
            description=desc,
            color=discord.Color.orange()
        )

        view = TradeConfirmView(
            requester=requester,
            target=target,
            req_slot=my_slot,
            tgt_slot=their_slot,
            req_name=my_name,
            tgt_name=their_name
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TradeCog(bot))
