__version__ = '0.1.0'

import os
import logging
import discord
from athena_bot.client import AthenaClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
channel = logging.StreamHandler()
channel.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
channel.setFormatter(formatter)
logger.addHandler(channel)

intents = discord.Intents.all()
intents.typing = False

def main():
    TOKEN = os.environ.get('DISCORD_TOKEN')
    if not TOKEN:
        logger.warn('TOKEN NOT FOUND! exiting...')
        exit()
    client = AthenaClient(intents=intents)
    client.run(TOKEN)