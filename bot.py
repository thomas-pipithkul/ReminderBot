from __future__ import print_function
import os

# library for discord.py API
import discord
import asyncio
from discord.ext import commands, tasks

# library for file I/O
from dotenv import load_dotenv
import json

# library for Google Calendar API
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# library to parse natural language into datetime
import parsedatetime

# library for naive and aware datetime
# resource: https://vinta.ws/code/timezone-in-python-offset-naive-and-offset-aware-datetimes.html
# resource: https://stackoverflow.com/questions/13866926/is-there-a-list-of-pytz-timezones
import tzlocal

# Cog
import greet
import reminder_cog

# Load discord token from config file/heroku config vars
if 'DISCORD_TOKEN' in os.environ:
    TOKEN = os.environ.get('DISCORD_TOKEN')
else:
    with open('./config.json', 'r') as f:
        config_dict = json.load(f)
        TOKEN = config_dict['token']

# create an instance of client (connect it to Discord WebSocket API)
# client = discord.Client()

bot = commands.Bot(command_prefix='.')

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

creds = None
service = None
DEFAULT_COLOR = discord.Color.blue()


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))


@bot.event
async def on_message(message):
    # check if the message send is not from the bot
    if message.author == bot.user:
        return

    print(message.content)

    if message.content.startswith('hello'):
        channel = message.channel
        await channel.send('Hello!')
        await channel.send('How are you?')

        def check(m):
            return m.content.startswith('good') and m.channel == channel

        msg = await bot.wait_for('message', check=check)
        await msg.add_reaction('\N{THUMBS UP SIGN}')
        await channel.send('That\'s awesome {.author}!'.format(msg))

    if message.content.startswith('thumb'):
        channel = message.channel
        await channel.send('gimme that 👍 reaction, mate')

        def check(reaction, user):
            return user == message.author and str(reaction.emoji) == '👍'

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await channel.send('👎')
        else:
            await channel.send('thank you 👍')

    if message.content.startswith('em'):
        channel = message.channel

        embed = discord.Embed(title='Sample Title lol',
                              description='This is a long description\n ipsum lol mao',
                              color=discord.Color.blue())
        embed.insert_field_at(0, name='name1', value='bruh this is hmmmmmmmmmmmmmm', inline=False)
        embed.insert_field_at(1, name='name2', value='bruh this is hmmmmmmmmmmmmm2', inline=False)
        embed.insert_field_at(2, name='name3', value='>>> inside', inline=False)
        embed.insert_field_at(3, name="name4", value='> inside', inline=False)
        val = ""
        for i in range(3):
            val = (embed.fields[2].value + "\nnext{}".format(i))
            embed.set_field_at(2, name='name3', value=val, inline=False)

        embed.set_footer(text='Footerlrlrlr')
        await channel.send(embed=embed)

    if "smart" in message.content and "not" not in message.content:
        await message.add_reaction('\N{THUMBS UP SIGN}')
        await message.channel.send('Thank you')

    await bot.process_commands(message)


# @bot.event
# async def on_command_error(ctx, error):
#     # await ctx.send(error)
#     print(error)


# Testing converter for function
# def to_upper(argument):
#     return argument.upper()
#
#
# @bot.command()
# async def up(ctx, *, content: to_upper):
#     await ctx.send(content)

# Testing Converter concept for user defined class
# import random
#
#
# class Slapper(commands.Converter):
#     async def convert(self, ctx, argument):
#         to_slap = random.choice(ctx.guild.members)
#         return '{.author.display_name} slapped {.display_name} because *{}*'.format(ctx, to_slap, argument)
#
#
# @bot.command()
# async def slap(ctx, *, reason: Slapper):
#     await ctx.send(reason)

@bot.command(name='test')
async def test(ctx, *args):
    await ctx.send('Did you {} say {} words: {}'.format(ctx.author, len(args), ', '.join(args)))
    await ctx.send('And that is in {} channel'.format(ctx.message.channel))


@bot.command()
async def here(ctx):
    await ctx.send('Still here', tts=True)

# TODO Delete calendar event command

# Add Cog
bot.add_cog(greet.Greetings(bot))
bot.add_cog(reminder_cog.ReminderCog(bot))

# Run the bot
bot.run(TOKEN)
