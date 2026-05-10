import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils.riot_api import RiotAPI

class Fearless(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.riot = RiotAPI()
        self._ddragon_version = None

    async def cog_unload(self):
        """Called when the cog is unloaded. Clean up the HTTP session."""
        await self.riot.close()
    
    async def _build_draft_embed(self, draft_info: dict) -> discord.Embed:
        """Assemble the draft into an embed."""
        embed = discord.Embed(title="Fearless Draft", color=discord.Color.gold())
        embed.add_field(name="Team Gromp <:gromp:1503093471676858428>", value="some value 1", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # invisible spacer
        embed.add_field(name="Right Column", value="some value 2", inline=True)
        return embed
    
    async def _do_fearless_draft(self, team_data: str) -> discord.Embed | str:
        """Orchestrator: calls all helpers in order."""
        # Validate input
        if not team_data:
            return "Please provide team data"
        
        # Call small helpers
        # champs = await self._get_champion_data(...)
        # bans = await self._calculate_bans(champs)
        embed = await self._build_draft_embed({"picks": 1, "bans": 4})
        
        return embed

    @app_commands.command(name="fearless", description="Create a fearless draft")
    @app_commands.describe(team_data="Your team composition")
    async def fearless_slash(self, interaction: discord.Interaction, team_data: str):
        await interaction.response.defer()
        try:
            result = await self._do_fearless_draft(team_data)
            if isinstance(result, discord.Embed):
                await interaction.followup.send(embed=result)
            else:
                await interaction.followup.send(result)
        except Exception as e:
            await interaction.followup.send(f"Error: `{e}`")

async def setup(bot):
    await bot.add_cog(Fearless(bot))