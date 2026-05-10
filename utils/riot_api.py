# utils/riot_api.py — Async wrapper for the Riot Games API.
#
# This class handles all communication with Riot's API.
# Each method = one API endpoint.
#
# Usage in a cog:
#   from utils.riot_api import RiotAPI
#   riot = RiotAPI()
#   account = await riot.get_account_by_riot_id("Faker", "KR1", "kr")
#
# Riot API docs: https://developer.riotgames.com/apis
# Remember: Dev API keys expire every 24 hours!

import aiohttp
import os


class RiotAPI:

    # =====================================================
    # REGION MAPPINGS
    # =====================================================
    #
    # Riot has two types of routing:
    #   - Platform routes (euw1, na1, kr...) — used for game-specific data
    #   - Regional routes (europe, americas, asia...) — used for account/match data
    #
    # When a user says "euw", we need to know both.

    # Maps short server name → platform route (for summoner, mastery, ranked, etc.)
    PLATFORM_ROUTES = {
        "euw": "euw1",
        "eune": "eun1",
        "na": "na1",
        "kr": "kr",
        "jp": "jp1",
        "br": "br1",
        "lan": "la1",
        "las": "la2",
        "oce": "oc1",
        "tr": "tr1",
        "ru": "ru",
    }

    # Maps short server name → regional route (for account lookups, match history)
    REGIONAL_ROUTES = {
        "euw": "europe",
        "eune": "europe",
        "na": "americas",
        "br": "americas",
        "lan": "americas",
        "las": "americas",
        "kr": "asia",
        "jp": "asia",
        "oce": "sea",
        "tr": "europe",
        "ru": "europe",
    }

    def __init__(self):
        # Read the API key from .env
        self.api_key = os.getenv("RIOT_API_KEY")
        # We reuse one session for all requests (more efficient)
        self.session = None

    async def _get_session(self):
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close the session. Call this when the cog unloads."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(self, url: str) -> dict | None:
        """
        Make a GET request to the Riot API.

        Returns:
            dict — the JSON response if status is 200
            None — if the request fails for any reason

        Every request is printed to your terminal so you can debug.
        """
        session = await self._get_session()
        headers = {"X-Riot-Token": self.api_key}

        async with session.get(url, headers=headers) as resp:
            # Print every request — super helpful for debugging
            print(f"[{resp.status}] {url}")

            if resp.status == 200:
                return await resp.json()
            else:
                # Print the error so you can see what went wrong
                print(f"  Error: {await resp.text()}")
                return None

    # =====================================================
    # API ENDPOINTS
    # =====================================================
    #
    # Each method below calls one Riot API endpoint.
    # The pattern is always:
    #   1. Build the URL with the right region
    #   2. Call self._request(url)
    #   3. Return the result
    #
    # Add more methods here as you explore the API docs!

    async def get_account_by_riot_id(self, game_name: str, tag_line: str, server: str = "euw") -> dict | None:
        """
        Look up an account by Riot ID (name#tag).
        Returns: { puuid, gameName, tagLine }
        Docs: https://developer.riotgames.com/apis#account-v1
        """
        region = self.REGIONAL_ROUTES.get(server, "europe")
        url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return await self._request(url)

    async def get_summoner_by_puuid(self, puuid: str, server: str = "euw") -> dict | None:
        """
        Get summoner data by PUUID.
        Returns: { puuid, profileIconId, summonerLevel, revisionDate }
        Docs: https://developer.riotgames.com/apis#summoner-v4
        """
        platform = self.PLATFORM_ROUTES.get(server, "euw1")
        url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        return await self._request(url)

    async def get_match_history(self, puuid: str, count: int = 10, server: str = "euw") -> list:
        """
        Get a list of recent match IDs.
        Returns: ["EUW1_1234567890", "EUW1_1234567891", ...]
        Docs: https://developer.riotgames.com/apis#match-v5
        """
        region = self.REGIONAL_ROUTES.get(server, "europe")
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
        return await self._request(url) or []

    async def get_match(self, match_id: str, server: str = "euw") -> dict | None:
        """
        Get full data for a single match.
        Returns: a big dict with all match data (participants, teams, etc.)
        Docs: https://developer.riotgames.com/apis#match-v5
        """
        region = self.REGIONAL_ROUTES.get(server, "europe")
        url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return await self._request(url)

    async def get_champion_masteries(self, puuid: str, server: str = "euw", count: int = 5) -> list:
        """
        Get top champion masteries for a player.
        Returns: [{ championId, championLevel, championPoints, ... }, ...]
        Docs: https://developer.riotgames.com/apis#champion-mastery-v4
        """
        platform = self.PLATFORM_ROUTES.get(server, "euw1")
        url = f"https://{platform}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count={count}"
        return await self._request(url) or []
    
    async def get_ranked_stats(self, puuid: str, server: str = "euw") -> dict | None:
        """
        Get ranked stats in a .json-format.
        Docs: https://developer.riotgames.com/apis#league-v4/GET_getChallengerLeague
        """
        platform = self.PLATFORM_ROUTES.get(server, "euw1")
        url = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        return await self._request(url)


    # =====================================================
    # ADD MORE ENDPOINTS HERE
    # =====================================================
    #
    # Example — ranked stats:
    #
    # The ranked endpoint needs a summoner ID, not a PUUID.
    # But Riot recently removed the "id" field from summoner-v4.
    # Check the docs to see which endpoints work with your key:
    # https://developer.riotgames.com/apis#league-v4
    #
    # async def get_ranked_stats(self, puuid: str, server: str = "euw") -> list:
    #     platform = self.PLATFORM_ROUTES.get(server, "euw1")
    #     url = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    #     return await self._request(url) or []