from discord.ext import commands
from discord import app_commands
import aiohttp
import discord
from utils.riot_api import RiotAPI


class Ranked(commands.Cog):
    def __init__(self, bot: commands.Bot, riot: RiotAPI):
        self.bot = bot
        self.riot = riot