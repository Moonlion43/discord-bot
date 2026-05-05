import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

# Set up the bot with a command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# A simple command: !hello
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hey {ctx.author.name}!")

# A simple ping command: !ping
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! Latency: {round(bot.latency * 1000)}ms")

bot.run(os.getenv("DISCORD_TOKEN"))