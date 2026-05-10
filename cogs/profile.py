# To avoid duplicating code, the helper methods just return an embed,
# and the command methods handle sending it.

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils.riot_api import RiotAPI

class Profile(commands.Cog):

    ranked_tiers = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4
    }

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
    # HELPER METHODS - DATA EXTRACTION
    # =====================================================

    def _extract_ranked_queue(self, ranked_entries: list, queue_type: str) -> dict | None:
        """Extract a specific ranked queue (RANKED_SOLO_5x5 or RANKED_FLEX_SR) from entries."""
        if not ranked_entries:
            return None
        for entry in ranked_entries:
            if entry["queueType"] == queue_type:
                return entry
        return None

    def _parse_rank_stats(self, rank_entry: dict) -> dict:
        """Parse rank entry into readable stats."""
        tier = rank_entry.get("rank", "?")
        rank = rank_entry.get("tier", "Unknown")
        lp = rank_entry.get("leaguePoints", 0)
        wins = rank_entry.get("wins", 0)
        losses = rank_entry.get("losses", 0)
        total_games = wins + losses
        winrate = round((wins / total_games) * 100, 0) if total_games > 0 else 0

        return {
            "tier": tier,
            "rank": rank,
            "lp": lp,
            "wins": wins,
            "losses": losses,
            "total_games": total_games,
            "winrate": int(winrate),
        }

    # =====================================================
    # HELPER METHODS - EMBED BUILDING
    # =====================================================

    async def _build_profile_embed(self, name: str, tag: str, level: int, icon_id: int, solo: dict | None, flex: dict | None) -> discord.Embed:
        """Build the profile embed from processed data."""
        version = await self.get_latest_version()

        embed = discord.Embed(
            title=f"{name}#{tag}",
            description=f"Level {level}",
            color=discord.Color.dark_purple(),
        )
        embed.set_thumbnail(
            url=f"https://ddragon.leagueoflegends.com/cdn/{version}/img/profileicon/{icon_id}.png"
        )

        # Solo/Duo
        if solo:
            stats = self._parse_rank_stats(solo)
            embed.add_field(
                name="Ranked Solo/Duo",
                value=f"""Rank: {stats['rank'].lower().capitalize()} {self.ranked_tiers[stats['tier']]} {stats['lp']} LP
                        Winratio: {stats['wins']}W {stats['losses']}L, {stats['winrate']}%
                        Total games played: {stats['total_games']}""",
                inline=False,
            )
        else:
            embed.add_field(name="Ranked Solo/Duo", value="Unranked", inline=False)

        # Flex
        if flex:
            stats = self._parse_rank_stats(flex)
            embed.add_field(
                name="Ranked Flex",
                value=f"""Rank: {stats['rank'].lower().capitalize()} {self.ranked_tiers[stats['tier']]} {stats['lp']} LP
                        Winratio: {stats['wins']}W {stats['losses']}L, {stats['winrate']}%
                        Total games played: {stats['total_games']}""",
                inline=False,
            )
        else:
            embed.add_field(name="Ranked Flex", value="Unranked", inline=False)

        return embed

    async def _build_mastery_embed(self, name: str, tag: str, masteries: list) -> discord.Embed:
        """Build the mastery embed from mastery data."""
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
                value=f"Mastery {level} - {points:,} pts",
                inline=False,
            )

        return embed

    # =====================================================
    # ORCHESTRATOR METHODS
    # =====================================================

    async def _do_profile(self, riot_id: str) -> discord.Embed | str:
        """
        Orchestrator: Fetch all data and build profile embed.
        """
        # Validate input
        if "#" not in riot_id:
            return "Use the format `Name#TAG` (e.g. `Faker#KR1`)"

        name, tag = riot_id.split("#", 1)

        # Fetch PUUID
        account = await self.riot.get_account_by_riot_id(name, tag)
        if not account:
            return f"Could not find **{riot_id}**"

        puuid = account["puuid"]

        # Fetch summoner and ranked data
        summoner = await self.riot.get_summoner_by_puuid(puuid)
        ranked_entries = await self.riot.get_ranked_stats(puuid)

        print(f"PUUID: {puuid}")
        print(f"Ranked response: {ranked_entries}")

        # Extract ranked queues
        solo = self._extract_ranked_queue(ranked_entries, "RANKED_SOLO_5x5")
        flex = self._extract_ranked_queue(ranked_entries, "RANKED_FLEX_SR")

        # Build embed
        level = summoner.get("summonerLevel", "?") if summoner else "?"
        icon_id = summoner.get("profileIconId", 1) if summoner else 1

        embed = await self._build_profile_embed(name, tag, level, icon_id, solo, flex)
        return embed

    async def _do_mastery(self, riot_id: str) -> discord.Embed | str:
        """
        Orchestrator: Fetch mastery data and build embed.
        """
        if "#" not in riot_id:
            return "Use the format `Name#TAG`"

        name, tag = riot_id.split("#", 1)

        # Fetch PUUID
        account = await self.riot.get_account_by_riot_id(name, tag)
        if not account:
            return f"Could not find **{riot_id}**"

        puuid = account["puuid"]

        # Fetch masteries
        masteries = await self.riot.get_champion_masteries(puuid)
        if not masteries:
            return f"No mastery data found for **{riot_id}**"

        # Build embed
        embed = await self._build_mastery_embed(name, tag, masteries)
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