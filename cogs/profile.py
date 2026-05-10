# cogs/profile.py — League of Legends profile commands.
#
# Each command exists twice:
#   - !profile Name#TAG   → prefix command (@commands.command)
#   - /profile riot_id:   → slash command (@app_commands.command)
#
# Both versions call the same helper method (_do_profile, _do_mastery)
# so you only write the logic once.
#
# The difference:
#   - Prefix commands use `ctx` and `ctx.send()`
#   - Slash commands use `interaction` and `interaction.response.send_message()`
#
# To avoid duplicating code, the helper methods just return an embed,
# and the command methods handle sending it.

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils.riot_api import RiotAPI


class Profile(commands.Cog):
    """Commands for looking up League of Legends profiles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Create one RiotAPI instance that all commands share
        self.riot = RiotAPI()
        self._ddragon_version = None

    async def cog_unload(self):
        """Called when the cog is unloaded. Clean up the HTTP session."""
        await self.riot.close()

    async def get_latest_version(self):
        if self._ddragon_version is None:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://ddragon.leagueoflegends.com/api/versions.json") as resp:
                    versions = await resp.json()
                    self._ddragon_version = versions[0]
        return self._ddragon_version

    # =====================================================
    # HELPER METHODS (shared logic)
    # =====================================================
    # These do the actual work and return an embed (or an error string).
    # The command methods below just call these and send the result.

    async def _do_profile(self, riot_id: str) -> discord.Embed | str:
        """
        Look up a player's profile. Returns an embed or an error string.
        """

        version = await self.get_latest_version()

        # Parse the Riot ID
        if "#" not in riot_id:
            return "Use the format `Name#TAG` (e.g. `Faker#KR1`)"

        name, tag = riot_id.split("#", 1)

        # Step 1: Riot ID → PUUID
        account = await self.riot.get_account_by_riot_id(name, tag)
        if not account:
            return f"Could not find **{riot_id}**"

        puuid = account["puuid"]

        # Step 2: PUUID → Summoner data
        summoner = await self.riot.get_summoner_by_puuid(puuid)

        # Step 3: Build embed
        level = summoner.get("summonerLevel", "?") if summoner else "?"
        icon_id = summoner.get("profileIconId", 1) if summoner else 1

        embed = discord.Embed(
            title=f"{name}#{tag}",
            description=f"Level {level}",
            color=discord.Color.dark_purple(),
        )
        embed.set_thumbnail(
            url=f"https://ddragon.leagueoflegends.com/cdn/{version}/img/profileicon/{icon_id}.png"
        )

        return embed

    async def _do_mastery(self, riot_id: str) -> discord.Embed | str:
        """
        Look up a player's top 5 masteries. Returns an embed or an error string.
        """
        if "#" not in riot_id:
            return "Use the format `Name#TAG`"

        name, tag = riot_id.split("#", 1)

        # Step 1: Get PUUID
        account = await self.riot.get_account_by_riot_id(name, tag)
        if not account:
            return f"Could not find **{riot_id}**"

        puuid = account["puuid"]

        # Step 2: Get top 5 masteries
        masteries = await self.riot.get_champion_masteries(puuid)
        if not masteries:
            return f"No mastery data found for **{riot_id}**"

        # Step 3: Build embed
        embed = discord.Embed(
            title=f"Top Masteries — {name}#{tag}",
            color=discord.Color.dark_purple(),
        )

        for i, m in enumerate(masteries, 1):
            champ_id = m["championId"]
            points = m["championPoints"]
            level = m["championLevel"]
            embed.add_field(
                name=f"#{i} — Champion ID {champ_id}",
                value=f"Level {level} - {points:,} pts",
                inline=False,
            )

        return embed

    # =====================================================
    # SLASH COMMANDS (/profile, /mastery)
    # =====================================================
    # These do the same thing but use interaction instead of ctx.
    # interaction.response.defer() = "bot is thinking..." (you get 15 seconds)
    # interaction.followup.send()  = send the actual response after deferring

    @app_commands.command(name="profile", description="Look up a League of Legends player")
    @app_commands.describe(riot_id="Riot ID in the format name#TAG")
    async def profile_slash(self, interaction: discord.Interaction, riot_id: str):
        await interaction.response.defer()  # shows "Bot is thinking..."
        try:
            result = await self._do_profile(riot_id)
            if isinstance(result, discord.Embed):
                await interaction.followup.send(embed=result)
            else:
                await interaction.followup.send(result)
        except Exception as e:
            await interaction.followup.send(f"Something went wrong: `{e}`")

    @app_commands.command(name="mastery", description="Show top champion masteries")
    @app_commands.describe(riot_id="Riot ID in the format Name#TAG")
    async def mastery_slash(self, interaction: discord.Interaction, riot_id: str):
        await interaction.response.defer()
        try:
            result = await self._do_mastery(riot_id)
            if isinstance(result, discord.Embed):
                await interaction.followup.send(embed=result)
            else:
                await interaction.followup.send(result)
        except Exception as e:
            await interaction.followup.send(f"Something went wrong: `{e}`")

    # =====================================================
    # ADD MORE COMMANDS HERE
    # =====================================================
    #
    # 1. Write a _do_something() helper that returns an embed
    # 2. Add a @commands.command() for !something
    # 3. Add a @app_commands.command() for /something
    # Both call the same helper — no duplicated logic.


# REQUIRED: discord.py calls this to load the cog
async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))