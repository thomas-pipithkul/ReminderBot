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
import alert_cog
import reminder_cog

# Load discord token from config file/heroku config vars
is_heroku = os.environ.get('IS_HEROKU', None)
if is_heroku:
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

    global creds, service
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        with open('token.json', 'r') as stream:
            creds_json = json.load(stream)
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        creds.token = creds_json['token']
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    # bot.add_cog(alert_cog.AlertCog(bot, service))


    # TODO This activate every time a bot use outside module. Figure a new way to greet user
    # Send bot login message as chat in a first text channel
    # for guild in bot.guilds:  # A bot can be deployed in multiple server(guild), so iterate over every server
    #     await guild.text_channels[0].send('I\'m here mortal')

    # channels = client.get_all_channels()
    # for channel in channels.text_channels:
    #     await channel.send('You summon me?')


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
