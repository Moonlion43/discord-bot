import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils.riot_api import RiotAPI
from utils.player import FakePlayer

class QueueView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.players = []

    def _build_embed(self):
        player_list = "\n".join(p.display_name for p in self.players) or "No players yet"
        embed = discord.Embed(title="Fearless Draft Queue", color=discord.Color.dark_purple())
        embed.add_field(name=f"Players ({len(self.players)}/10)", value=player_list)
        return embed

    @discord.ui.button(label="Join Queue",style=discord.ButtonStyle.primary)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            return await interaction.response.send_message("You're already in the queue.", ephemeral=True)
        self.players.append(interaction.user)

        # Fill remaining slots with fake players for testing
        fake_names = ["Faker", "Chovy", "Zeus", "Keria", "Gumayusi",
                    "Caps", "Jankos", "Oner", "Deft", "Ruler"]
        while len(self.players) < 10:
            self.players.append(FakePlayer(fake_names[len(self.players)]))

        vote_view = TeamSelectionVote(self.players)
        await interaction.response.edit_message(embed=vote_view.build_embed(), view=vote_view)
        vote_view.message = await interaction.original_response()

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.primary)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            return await interaction.response.send_message("You're not in the queue.", ephemeral=True)
        self.players.remove(interaction.user)
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

class TeamSelectionVote(discord.ui.View):
    def __init__(self, players: list):
        super().__init__(timeout=10)
        self.players = players
        self.votes = {"random": set(), "captains": set(), "balanced": set()}

    def build_embed(self):
        embed = discord.Embed(title="How should teams be picked?", color=discord.Color.gold())
        for method, voters in self.votes.items():
            embed.add_field(name=f"{method.capitalize()} ({len(voters)})", value="\u200b", inline=True)
        embed.set_footer(text="Vote below! Most votes after 60 s wins.")
        return embed

    async def _handle_vote(self, interaction: discord.Interaction, choice: str):
        if interaction.user not in self.players:
            return await interaction.response.send_message("You're not in this game.", ephemeral=True)
        # Remove previous vote
        for v in self.votes.values():
            v.discard(interaction.user)
        self.votes[choice].add(interaction.user)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Random", style=discord.ButtonStyle.primary, emoji="🎲")
    async def vote_random(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, "random")

    @discord.ui.button(label="Captains", style=discord.ButtonStyle.primary, emoji="👑")
    async def vote_captains(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, "captains")

    @discord.ui.button(label="Balanced", style=discord.ButtonStyle.primary, emoji="⚖️")
    async def vote_balanced(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, "balanced")

    async def on_timeout(self):
        # Pick the winner and move to team creation
        winner = max(self.votes, key=lambda k: len(self.votes[k]))
        teams = self._make_teams(winner)
        embed = self._build_teams_embed(teams, winner)
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        # We need the message to edit it — store it when sending
        if hasattr(self, "message"):
            await self.message.edit(embed=embed, view=self)

    def _make_teams(self, method: str) -> dict:
        import random
        shuffled = self.players.copy()
        random.shuffle(shuffled)
        # For now just split randomly — expand captains/balanced later
        return {
            "gromp": shuffled[:5],
            "krug": shuffled[5:]
        }

    def _build_teams_embed(self, teams: dict, method: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"Teams (picked by {method})",
            color=discord.Color.green()
        )
        gromp_names = "\n".join(p.display_name for p in teams["gromp"])
        krug_names = "\n".join(p.display_name for p in teams["krug"])
        embed.add_field(name="Team Gromp <:gromp:1503093471676858428>", value=gromp_names, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Team Krug <:krug:1503094259744510196>", value=krug_names, inline=True)
        return embed


class Fearless(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="fearless", description="Start a fearless draft queue")
    async def fearless_slash(self, interaction: discord.Interaction):
        view = QueueView()
        await interaction.response.send_message(embed=view._build_embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Fearless(bot))