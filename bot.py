# bot.py — Entry point. Run this file to start the bot.
#
# This file does 3 things:
#   1. Loads your secrets from .env
#   2. Creates the bot
#   3. Loads all cogs (command files) from the cogs/ folder

import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Load .env file so we can use os.getenv() to read secrets
load_dotenv()

# Intents = what events your bot listens to
# default() gives you most things, message_content lets you read message text
intents = discord.Intents.default()
intents.message_content = True

# command_prefix="!" means commands start with !
# e.g. !ping, !profile, etc.
bot = commands.Bot(command_prefix="!", intents=intents)


# =====================================================
# CHANGE THIS to your Discord server ID
# Right-click your server icon → Copy Server ID
# (Enable Developer Mode in Settings → Advanced first)
# =====================================================
GUILD_ID = 1153780504370348143  # <-- paste your server ID here


@bot.event
async def on_ready():
    """This runs once when the bot connects to Discord."""
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Sync slash commands to your server (instant, no waiting)
    # Global sync (without guild) can take up to an hour
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print("Slash commands synced to server!")
    else:
        print("WARNING: Set GUILD_ID in bot.py to enable slash commands!")


async def main():
    """Load cogs and start the bot."""

    # Loop through every .py file in the cogs/ folder
    # and load it as a cog (a group of commands)
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"Loaded cog: {filename}")

    # Start the bot with your Discord token from .env
    await bot.start(os.getenv("DISCORD_TOKEN"))


# Run it
asyncio.run(main())