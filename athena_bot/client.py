import discord
import re
import os
import pickle
import logging
from athena_bot import utils
from datetime import datetime, timedelta
from inspect import ismethod
from athena_bot.overwatch import Overwatch

logger = logging.getLogger(__name__)

class AthenaClient(discord.Client):
    DATA_FILE = os.environ.get('DATA_FILE', './athena-data.p')
    BOT_NAME='Athena'

    async def on_ready(self):
        logger.info(f'Logged in as {self.user}')
        self.overwatch = Overwatch()
        self.battletag_re = re.compile(r'([^#\s]+#\d+)')
        self.command_tree = {
            'save': self.__create_command(
                self.save_user, 
                ['register', 'save', 'store', 'remember', 'set', 'modify', 'link']
            ),
            'show': self.__create_command(
                self.show_user, 
                ['show', 'stats', 'data', 'get']
            ),
            'remove': self.__create_command(
                self.remove_user, 
                ['remove', 'stop', 'forget', 'delete', 'purge', 'unlink']
            ),
            'ezmode': self.__create_command(
                self.easy_mode,
                ['ez', 'easy mode']
            )
        }
        self.data = utils.read_datafile(self.DATA_FILE)

    # creates a response from a set of trigger words
    def __create_command(self, function, words):
        pattern = re.compile(r'\b'+r'|'.join(words)+r'\b')
        return (function, pattern)

    # on a new message, check for command
    async def on_message(self, message):
        if message.author == self.user:
            return
        is_command = self.__is_command(message)
        if is_command:
            command, battletag = self.__infer_command(message.content)
            if ismethod(command):
                await command(message, battletag)
            else:
                await message.channel.send(
                    f'Sorry {message.author.mention}, I did not understand your request.'
                )

    # check if the context of the message is a command
    def __is_command(self, message: discord.Message):
        content = message.content.lower()
        if content.startswith(self.BOT_NAME.lower()):
            return True
        if (content.startswith(self.user.mention) and 
            len(message.mentions) <= 2 and 
            not message.mention_everyone and
            self.user in message.mentions):
            return True
        return False

    # find the command in the command tree
    def __infer_command(self, raw_content:str):
        infered_command = None
        battletag = None
        for command_name, com_tuple in self.command_tree.items():
            method, pattern = com_tuple
            match = pattern.search(raw_content)
            if match:
                infered_command = method
                break
        match = self.battletag_re.search(raw_content)
        if match:
            battletag = match.group(1)
        return (infered_command, battletag)

    async def save_user(self, message: discord.Message, battletag):
        member = message.author
        mentions = message.mentions
        if not battletag:
            return await message.channel.send(f'I did not detect a battletag in your message, {message.author.mention}.')
        if len(mentions) > 0 and len(mentions) <= 2:
            if not self.user in mentions:
                member = next(filter(lambda m: m is not self.user, mentions))
                if not member:
                    return await message.channel.send('There was an error storing that data.')
        users = self.data.get('users', dict())
        users.update({member.id: battletag})
        tags = self.data.get('tags', dict())
        tags.update({battletag: member.id})
        self.data.update({'users': users, 'tags': tags})
        utils.write_datafile(self.DATA_FILE, self.data)
        await message.channel.send(
            f'Acknowledge, {member.mention} will now be identified with the battletag "{battletag}".')

    async def remove_user(self, message, battletag):
        await message.channel.send(f'I\'m not ready to remove an user...')

    async def show_user(self, message: discord.Message, battletag):
        member = message.author
        mentions = message.mentions
        if len(mentions) > 0 and len(mentions) <= 2:
            if not self.user in mentions:
                member = next(filter(lambda m: m is not self.user, mentions))
                if not member:
                    return await message.channel.send('I don\'t have that user in my database.')
        member_tag = self.data.get('users').get(member.id)
        if not battletag:
            battletag = member_tag
            if not battletag:
                return await message.channel.send(f'I couldn\'t find the data you requested. Maybe {member.mention} is not on the database.')
        refresh = re.search(r'\brefresh|reload|cached\b', message.content) is not None
        if refresh:
            await message.channel.send('Reloading data...')
        path = await self.overwatch.get_profile_path(battletag, refresh=refresh)
        with open(path, 'rb') as profile:
            badge = discord.File(profile, 'badge.png')
            await message.channel.send(file=badge)

    async def easy_mode(self, message: discord.Message, battletag):
        dva = discord.utils.get(self.emojis, name='dva')
        return await message.channel.send(str(dva))
