import discord

import logging
from logging.handlers import RotatingFileHandler
import os

from midibot import Config, Commands


os.makedirs("data/logs", exist_ok=True)
filehandler = RotatingFileHandler(filename="data/logs/scrimbot.log", mode="w", maxBytes=1024 * 50, backupCount=4)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s:%(message)s",
                    handlers=[filehandler])

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Bot(intents=intents)

bot.add_cog(Commands(bot))

bot.run(Config().token)