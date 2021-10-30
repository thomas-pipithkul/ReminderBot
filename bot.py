from __future__ import print_function
import os

# library for discord.py API
import discord
import asyncio
from discord.ext import commands

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

# library to parse natural language into datetime
import parsedatetime

# library for naive and aware datetime
# resource: https://vinta.ws/code/timezone-in-python-offset-naive-and-offset-aware-datetimes.html
# resource: https://stackoverflow.com/questions/13866926/is-there-a-list-of-pytz-timezones
import tzlocal

# Cog
import greet

# Load discord token from .env file
# load_dotenv()
# TOKEN = os.getenv('DISCORD_TOKEN')
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

    # Find the upcoming event
    # Call the Calendar API
    local_tz = tzlocal.get_localzone()  # get system timezone
    now = datetime.datetime.utcnow()
    # now_local_tz = now.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
    tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)
    events_result = service.events().list(calendarId='primary', timeMin=now.isoformat() + 'Z',   # 'Z' indicates UTC time
                                          timeMax=tomorrow.isoformat() + 'Z', singleEvents=True,
                                          orderBy='startTime', timeZone=local_tz).execute()
    events = events_result.get('items', [])

    import pytz
    channel = bot.guilds[0].text_channels[0]
    # dt = datetime.datetime(2020, month=6, day=30, hour=12, minute=42, second=0, tzinfo=datetime.timezone.utc)
    # dt = dt.astimezone(tz=pytz.timezone('America/New_York'))
    dt = datetime.datetime.now(pytz.timezone('America/New_York')) + datetime.timedelta(minutes=1)
    await discord.utils.sleep_until(dt)
    await channel.send("Done waiting {}".format(dt.strftime("%I:%M %p")))
    for i in range(5):
        dt = dt + datetime.timedelta(minutes=1)
        await discord.utils.sleep_until(dt)
        await channel.send("Done waiting {}".format(dt.strftime("%I:%M %p")))

    # If there is upcoming event in the calendar
    tasks = []
    for event in events:
        print(event['summary'])

        # Get the start time string from Google Calendar API (datetime or date obj)
        start = event['start'].get('dateTime')

        # convert ISO date str to datetime
        datetime_start = datetime.datetime.fromisoformat(start)

        # Make now aware datetime object
        now_local_tz = now.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
        # local_tz = tzlocal.get_localzone()  # get system timezone
        # now_local_tz = local_tz.localize(now)  # Make datetime aware to local timezone

        # TODO learn concurrent Coroutines to schedule reminders
        duration = datetime_start - now_local_tz
        if duration.total_seconds() >= 0:
            channel = bot.guilds[0].text_channels[0]
            task = asyncio.create_task(sleep(channel, event, int(duration.total_seconds())))
            tasks.append(task)
            # print("{} starting in {}".format(event['summary'], duration.total_seconds()))
            # await asyncio.create_task(sleep(channel, event, int(duration.total_seconds())))

    await asyncio.gather(*tasks)


    # TODO This activate every time a bot use outside module. Figure a new way to greet user
    # Send bot login message as chat in a first text channel
    # for guild in bot.guilds:  # A bot can be deployed in multiple server(guild), so iterate over every server
    #     await guild.text_channels[0].send('I\'m here mortal')

    # channels = client.get_all_channels()
    # for channel in channels.text_channels:
    #     await channel.send('You summon me?')


async def sleep(channel, event, duration: int):
    await asyncio.sleep(duration)
    await channel.send('**{}** is starting now!'.format(event['summary']), tts=True)


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


@bot.event
async def on_command_error(ctx, error):
    await ctx.send(error)
    print(error)


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


@bot.command()
async def sched(ctx):
    await ctx.send('sched')


@bot.command(name='test')
async def test(ctx, *args):
    await ctx.send('Did you {} say {} words: {}'.format(ctx.author, len(args), ', '.join(args)))
    await ctx.send('And that is in {} channel'.format(ctx.message.channel))


@bot.command()
async def delay(ctx, duration: int):
    await ctx.send('Got it wait for: {}s'.format(duration))
    await asyncio.sleep(duration)
    await ctx.send('Done waiting for {}s'.format(duration))


@bot.command()
async def add(ctx, num1: int, num2: int):
    await ctx.send(num1 + num2)


@bot.command()
async def here(ctx):
    await ctx.send('Still here', tts=True)


@bot.command()
async def upcoming(ctx, num: int = 5):
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

    # If there is no upcoming event in the calendar
    if not events:
        embed = discord.Embed(title='No upcoming events found',
                              color=DEFAULT_COLOR)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title='📃 Upcoming Events',
                              color=DEFAULT_COLOR)

        # Iterate through all specified number of events in primary Calendar
        today = datetime.datetime.today().date()
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        index = 0
        prev_date = None
        footer = ""
        for event in events:
            # Get the start time string from Google Calendar API (datetime or date obj)
            start = event['start'].get('dateTime', event['start'].get('date'))

            # convert ISO date str to datetime
            datetime_start = datetime.datetime.fromisoformat(start)

            # Format the display date string
            if datetime_start.date() == today:
                dt_str_formatted = "Today [{d:%b} {d:%d}]".format(d=datetime_start)
            elif datetime_start.date() == tomorrow:
                dt_str_formatted = "Tomorrow [{d:%b} {d:%d}]".format(d=datetime_start)
            else:
                dt_str_formatted = datetime_start.strftime("%a [%b %d, %Y]")

            # Format the display time string
            display_time_str = datetime_start.time().strftime("%I:%M%p")

            # display_time_str = '{d:%I}:{d.minute:02}{d:%p}'.format(d=datetime_start.time())
            print(datetime_start, event['summary'])

            # First date to insert
            if prev_date is None:
                embed.insert_field_at(index=index,
                                      name="{}".format(dt_str_formatted),
                                      value=">>> {} {}\n".format(display_time_str, event['summary']),
                                      inline=False)
            # Not the first date to insert
            else:
                # TODO This doesn't group all event on the same day, it only group 2 events on the same day
                # If it's the same date, group them together
                if prev_date == datetime_start.date():
                    try:
                        val = embed.fields[index - 1].value + "{} {}\n".format(display_time_str, event['summary'])
                        embed.set_field_at(index=index - 1,
                                           name=" {}".format(dt_str_formatted),
                                           value=val,
                                           inline=False)
                    except IndexError:
                        embed.insert_field_at(index=index,
                                              name="{}".format(dt_str_formatted),
                                              value=">>> {} {}\n".format(display_time_str, event['summary']),
                                              inline=False)
                else:
                    embed.insert_field_at(index=index,
                                          name="{}".format(dt_str_formatted),
                                          value=">>> {} {}\n".format(display_time_str, event['summary']),
                                          inline=False)
            index += 1
            footer = '🌐 {}'.format(datetime_start.strftime("%Z"))
            prev_date = datetime_start.date()
            # embed.insert_field_at(index, name='Event List', value=start)
            # await ctx.send('{} {}'.format(start, event['summary']))
        embed.set_footer(text=footer)
        await ctx.send(embed=embed)


@bot.command(name='create')
async def add_calendar_event(ctx, *, arg):
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
    # arg_str = ' '.join(arg)

    # find where is the time specify in the argument
    cal = parsedatetime.Calendar()
    ret = cal.nlp(arg)  # use natural language parsing

    # Check the return value from natural language parsing
    if ret is not None:
        parsed_datetime = ret[0][0]
        parse_status = ret[0][1]
        start_date_pos = ret[0][2]
        end_date_pos = ret[0][3]
        date_str = ret[0][4]

        # parse summary (message from beginning to the character before the date
        summary = arg[:start_date_pos].strip()  # remove leading + trailing whitespaces

        # add in timezone to the parsed_datetime
        # TODO could have issue with daylight saving time
        # https://stackoverflow.com/questions/7065164/how-to-make-an-unaware-datetime-timezone-aware-in-python
        # Check if parsed_datetime is naive
        if parsed_datetime.tzinfo is None or parsed_datetime.utcpffset(parsed_datetime) is None:
            # dt_local_tz = parsed_datetime.replace(tzinfo=datetime.timezone.utc)  # Make datetime aware to UTC
            local_tz = tzlocal.get_localzone()  # get system timezone
            dt_local_tz = local_tz.localize(parsed_datetime)  # Make datetime aware to local timezone

        # TODO check if the time is in the past

        print(date_str)
        print(dt_local_tz.isoformat())
        print(dt_local_tz.tzinfo)

        # create event dict for Google Calendar API
        event = {
            'summary': summary,
            'start': {
                'dateTime': dt_local_tz.isoformat(),
                'timeZone': 'America/New_York'
            },
            'end': {
                'dateTime': (dt_local_tz + datetime.timedelta(hours=1)).isoformat(),
                'timeZone': 'America/New_York'
            }
        }

        # Call the Calendar API
        e = service.events().insert(calendarId='primary', body=event).execute()

        # Notify discord with success embedded message
        time_str = dt_local_tz.strftime("%I:%M %p %a, %b %d, %Y %Z")
        embed = discord.Embed(title='🗓️ Event "{}" created'.format(e['summary']),
                              color=DEFAULT_COLOR)
        embed.add_field(name='Time', value=time_str, inline=False)
        embed.set_footer(text='Created by {}'.format(ctx.author.display_name))
        await ctx.send(embed=embed)
    else:  # the parsing fail (return None)
        # Notify discord with fail embedded message
        embed = discord.Embed(title='Event creation failed :(',
                              description="I don't understand the time of the event",
                              color=DEFAULT_COLOR)
        await ctx.send(embed=embed)

# TODO Delete calendar event command

# def day_of_week_index(day: str):
#     day_of_week = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
#                    'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
#                    'mo', 'tu', 'we', 'th', 'fr', 'sa', 'su',
#                    'm', 't', 'w', 'r', 'f', 's', 'u')
#     try:
#         print(day_of_week.index(day.lower()) % 7)
#         return day_of_week.index(day.lower()) % 7
#     except ValueError:
#         return -1


# Add Cog
bot.add_cog(greet.Greetings(bot))

# Run the bot
# client.run()
# TODO find a way to hide this token more securely
bot.run(TOKEN)
print('test')
