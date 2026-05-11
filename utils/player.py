from discord.ext import commands
from discord import app_commands
import aiohttp
import discord
from utils.riot_api import RiotAPI


class FakePlayer:
    def __init__(self, name):
        self.display_name = name
        self.id = hash(name)
        
    def __eq__(self, other):
        return self.id == getattr(other, 'id', None)

    def __hash__(self):
        return self.id