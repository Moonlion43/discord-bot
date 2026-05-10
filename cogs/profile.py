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

        ranked_entries = await self.riot.get_ranked_stats(puuid)
        print(f"PUUID: {puuid}")
        print(f"Ranked response: {ranked_entries}")

        # Step 3: Build embed
        level = summoner.get("summonerLevel", "?") if summoner else "?"
        icon_id = summoner.get("profileIconId", 1) if summoner else 1

        solo = None
        if ranked_entries:
            for entry in ranked_entries:
                if entry["queueType"] == "RANKED_SOLO_5x5":
                    solo = entry
                    break
        
        flex = None
        if ranked_entries:
            for entry in ranked_entries:
                if entry["queueType"] == "RANKED_FLEX_SR":
                    flex = entry
                    break
        
        if solo:
            rank = solo.get("tier", "Unknown") # the actual rank, so emerald/dia
            tier = solo.get("rank", "?") # the tier, so I, II, III or IV
            lp = solo.get("leaguePoints", 0)
            wins = solo.get("wins", 0)
            losses = solo.get("losses", 0)
            total_games_played = wins + losses
            winrate = round((wins/total_games_played)*100, 0) if total_games_played > 0 else 0
        
        if flex:
            flex_rank = flex.get("tier", "Unknown")
            flex_tier = flex.get("rank", "?")
            flex_lp = flex.get("leaguePoints", 0)
            flex_wins = flex.get("wins", 0)
            flex_losses = flex.get("losses", 0)
            flex_total_games_played = flex_wins + flex_losses
            flex_winrate = round((flex_wins/flex_total_games_played)*100, 0) if flex_total_games_played > 0 else 0

        embed = discord.Embed(
            title=f"{name}#{tag}",
            description=f"Level {level}",
            color=discord.Color.dark_purple(),
        )
        embed.set_thumbnail(
            url=f"https://ddragon.leagueoflegends.com/cdn/{version}/img/profileicon/{icon_id}.png"
        )

        # solo/duo
        if solo:
            embed.add_field(name="Ranked Solo/Duo ", 
                            value=f"""Rank: {rank.lower().capitalize()} {self.ranked_tiers[tier]} {lp} LP
                            Winratio: {wins}W {losses}L, {winrate}%
                            Total games played: {total_games_played}""", inline=False)
        else:
            embed.add_field(name="Ranked Solo/Duo", value="Unranked",inline=False)

        # flex
        if flex:
            embed.add_field(name="Ranked Flex ", 
                            value=f"""Rank: {flex_rank.lower().capitalize()} {self.ranked_tiers[flex_tier]} {flex_lp} LP
                            Winratio: {flex_wins}W {flex_losses}L, {flex_winrate}% 
                            Total games played: {flex_total_games_played}""", inline=False)
        else:
            embed.add_field(name="Ranked Flex", value="Unranked",inline=False)

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
                value=f"Mastery {level} - {points:,} pts",
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