from __future__ import print_function
import os

import discord
import asyncio
from discord.ext import commands

# library to work with .env files
from dotenv import load_dotenv

# library for Google Calendar API
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# library to parse natural language into datetime
import parsedatetime

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# create an instance of client (connect it to Discord WebSocket API)
# client = discord.Client()

bot = commands.Bot(command_prefix='-')

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

creds = None
service = None


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

    global creds, service
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('CalendarAPITest/token.pickle'):
        with open('CalendarAPITest/token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('CalendarAPITest/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Send bot login message as chat in a first text channel
    for guild in bot.guilds:  # A bot can be deployed in multiple server(guild), so iterate over every server
        await guild.text_channels[0].send('I\'m here mortal')

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
        await channel.send('That\'s awesome {.author}!)'.format(msg))

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
        embed.add_field(name='Mmmmmmm', value='bruh this is hmmmmmmmmmmmmmm', inline=True)
        embed.add_field(name='Mmmmmmm2', value='bruh this is hmmmmmmmmmmmmm2', inline=False)
        embed.set_footer(text='Footerlrlrlr')
        await channel.send(embed=embed)

    if "smart" in message.content and "not" not in message.content:
        await message.add_reaction('\N{THUMBS UP SIGN}')
        await message.channel.send('Thank you')

    await bot.process_commands(message)


@bot.command(name='test')
async def test(ctx, *args):
    await ctx.send('Did you {} say {} words: {}'.format(ctx.author, len(args), ', '.join(args)))
    await ctx.send('And that is in {} channel'.format(ctx.message.channel))


@bot.command()
async def add(ctx, num1: int, num2: int):
    await ctx.send(num1 + num2)


@bot.command()
async def here(ctx):
    await ctx.send('Still here')


@bot.command()
async def upcoming(ctx, num: int):
    global creds, service

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('CalendarAPITest/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming {} events'.format(num))
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=num, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])
        await ctx.send('{} {}'.format(start, event['summary']))


@bot.command(name='create')
async def add_calendar_event(ctx, *arg):
    global creds, service

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('CalendarAPITest/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # parse the argument
    # make arg into 1 string instead of tuple
    arg_str = ' '.join(arg)

    # find where is the time specify in the argument
    cal = parsedatetime.Calendar()
    ret = cal.nlp(arg_str)  # use natural language parsing

    # Check the return value from natural language parsing
    if ret is not None:
        parsed_datetime = ret[0][0]
        parse_status = ret[0][1]
        start_date_pos = ret[0][2]
        end_date_pos = ret[0][3]
        date_str = ret[0][4]

        # parse summary (message from beginning to the character before the date
        summary = arg_str[:start_date_pos].strip()  # remove leading + trailing whitespaces

        # add in timezone to the parsed_datetime
        # TODO make datetime aware with timezone
        print(parsed_datetime.tzinfo)

        # create event dict for Google Calendar API
        event = {
            'summary': summary,
            'start': {
                'dateTime': '2020-06-18T09:00:00-04:00'
            },
            'end': {
                'dateTime': '2020-06-18T11:00:00-04:00'
            }
        }

        # Call the Calendar API
        # e = service.events().insert(calendarId='primary', body=event).execute()

        # Notify discord with success embedded message
        embed = discord.Embed(title='🗓️ Event "{}" created'.format(event['summary']),
                              color=discord.Color.blue())
        embed.add_field(name='Event Time', value=parsed_datetime)
        await ctx.send(embed=embed)
    else:  # the parsing fail (return None)
        # Notify discord with fail embedded message
        embed = discord.Embed(title='Event creation failed :(',
                              description="I don't understand the time of the event",
                              color=discord.Color.blue())
        await ctx.send(embed=embed)


def day_of_week_index(day: str):
    day_of_week = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                   'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
                   'mo', 'tu', 'we', 'th', 'fr', 'sa', 'su',
                   'm', 't', 'w', 'r', 'f', 's', 'u')
    try:
        print(day_of_week.index(day.lower()) % 7)
        return day_of_week.index(day.lower()) % 7
    except ValueError:
        return -1


# Run the bot
# client.run()
# TODO find a way to hide this token more securely
bot.run(TOKEN)
