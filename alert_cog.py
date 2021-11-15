import os
import json

import discord
from discord.ext import tasks, commands
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from message import Message

import asyncio

# Date/Time library
import tzlocal
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

import parsedatetime

from itertools import filterfalse

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


class AlertCog(commands.Cog):
    def __init__(self, bot, service):
        # Google Calendar Credentials
        self.creds = None
        self.service = service
        self.connect_google_calendar()

        # Discord Bot Info
        self.bot = bot
        self.main_channel = bot.guilds[0].text_channels[0]

        self.last_updated = None
        self.events = self.get_today_events()
        self.create_messages = []
        self.alert_messages = []

        self.messages = {}

        self.check_alert_events.start()
        self.update_created_msg.start()

    def get_creds(self):
        if os.path.exists('token.json'):
            with open('token.json', 'r') as stream:
                creds_json = json.load(stream)
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            self.creds.token = creds_json['token']
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

    def get_service(self):
        if not self.service:
            self.service = build('calendar', 'v3', credentials=self.creds)

    def connect_google_calendar(self):
        self.get_creds()
        self.get_service()

    def cog_unload(self):
        self.check_alert_events.cancel()
        self.update_created_msg.cancel()

    def get_event_json(self, summary, start, end, tz):
        return {
            'summary': summary,
            'start': {
                'dateTime': start.isoformat(),
                'timeZone': tz
            },
            'end': {
                'dateTime': end.isoformat(),
                'timeZone': tz
            }
        }

    def remove_dup_events(self, events):
        seen_id = set()
        new_list = []
        for event in events:
            if event['id'] not in seen_id:
                new_list.append(event)
                seen_id.add(event['id'])
        return new_list

    def get_create_embed(self, title, time_str, author):
        embed = discord.Embed(title=title, color=discord.Color.blue())
        embed.add_field(name='Time', value=time_str, inline=False)
        embed.set_footer(text=f'✅ Confirm | 🗑️ Delete | Created by {author}')
        return embed

    def get_today_events(self):
        now = datetime.utcnow()
        tmr = datetime.utcnow() + timedelta(days=1)
        self.last_updated = now
        events_results = self.service.events().list(calendarId='primary',
                                                    timeMin=now.isoformat() + 'Z',
                                                    timeMax=tmr.isoformat() + 'Z',
                                                    singleEvents=True,
                                                    orderBy='startTime').execute()
        return events_results.get('items', [])

    @commands.command(name='create')
    async def add_calendar_event(self, ctx, *, arg):
        self.connect_google_calendar()

        # find where is the time specify in the argument
        cal = parsedatetime.Calendar()
        ret = cal.nlp(arg)  # use natural language parsing

        # Check the return value from natural language parsing
        if ret is not None:
            ret = ret[0]
            parsed_datetime = ret[0]
            start_date_pos = ret[2]

            # parse summary (message from beginning to the character before the date
            summary = arg[:start_date_pos].strip()  # remove leading + trailing whitespaces

            # add in timezone to the parsed_datetime
            if parsed_datetime.tzinfo is None or parsed_datetime.utcpffset(parsed_datetime) is None:
                local_tz = tzlocal.get_localzone()  # get system timezone
                parsed_datetime = local_tz.localize(parsed_datetime)  # Make datetime aware to local timezone

            event = self.get_event_json(summary, parsed_datetime, parsed_datetime + timedelta(hours=1), 'America/New_York')

            # Notify discord with success embedded message
            time_str = parsed_datetime.strftime("%I:%M %p %a, %b %d, %Y %Z")
            embed = self.get_create_embed(f'🗓️ {summary}', time_str, ctx.author.display_name)
            msg = await ctx.send(embed=embed)
            await msg.add_reaction('✅')
            await msg.add_reaction('🗑️')

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in '✅🗑️'

            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=60.0 * 1)

                # Insert it to Google Calendar & Add to event list
                if str(reaction.emoji) == '✅':
                    # Call the Calendar API
                    e = self.service.events().insert(calendarId='primary', body=event).execute()

                    self.events.append(e)
                    self.events = self.remove_dup_events(self.events)
                    sorted(self.events, key=lambda ev: ev['start'].get('dateTime'))

                    await msg.remove_reaction('✅', user)
                    new_embed = self.get_create_embed(f'🗓️ {summary} ✅', time_str, ctx.author.display_name)
                    await msg.edit(embed=new_embed)
                # Do nothing
                elif str(reaction.emoji) == '🗑️':
                    await msg.remove_reaction('🗑️', user)

            except asyncio.TimeoutError:
                new_embed = self.get_create_embed(f'🗓️ {summary} ( 🚫 Timed out )', f'~~{time_str}~~', ctx.author.display_name)
                await msg.edit(embed=new_embed)
                await msg.clear_reactions()
            # self.messages[e['id']] = Message(e, msg)

        # the parsing fail (return None)
        else:
            # Notify discord with fail embedded message
            embed = discord.Embed(title='Event creation failed :(',
                                  description="I don't understand the time of the event",
                                  color=discord.Color.blue())
            await ctx.send(embed=embed)

    @tasks.loop(seconds=1.0)
    async def update_created_msg(self):
        now = datetime.utcnow()
        now = now.replace(tzinfo=timezone.utc).astimezone(tz=None)

        # for msg in self.messages:
        #     start = msg.event['start'].get('dateTime')
        #     start = datetime.fromisoformat(start)
        #
        #     embed = discord.Embed(title=f"🔔 Event \"{msg.event['summary']}\"",
        #                           description=f"starts in {start - now}",
        #                           color=discord.Color.gold())
        #     await msg.created_msg.edit(embed=embed)

    @update_created_msg.before_loop
    async def before_created(self):
        await self.bot.wait_until_ready()
        print('Finished waiting2')

    @tasks.loop(seconds=1.0)
    async def check_alert_events(self):
        now = datetime.utcnow()

        # If last updated was more than a day, get today's events
        if not self.last_updated and self.last_updated < now + timedelta(days=1):
            self.events += self.get_today_events()
            self.events = self.remove_dup_events(self.events)
            sorted(self.events, key=lambda e: e['start'].get('dateTime'))

        now = now.replace(tzinfo=timezone.utc).astimezone(tz=None)

        # Check the events and process it if it's the start time
        for event in list(self.events):
            start = event['start'].get('dateTime')
            start = datetime.fromisoformat(start)
            end = event['end'].get('dateTime')
            end = datetime.fromisoformat(end)
            delta = timedelta(minutes=15)

            if start - delta <= now <= start:
                print('{} is starting in less than {} minutes'.format(event['summary'], 15))
                self.events.remove(event)
                embed = discord.Embed(title=f"🔔 {event['summary']}",
                                      description=f"starts in {start - now}",
                                      color=discord.Color.gold())
                msg = await self.main_channel.send(embed=embed)
                self.alert_messages.append(msg)
                # self.messages[event['id']].alert_msg = msg

            elif start < now < end:
                print('{} is happening'.format(event['summary']))
                self.events.remove(event)
                embed = discord.Embed(title=f"🔔 {event['summary']}",
                                      description=f"is happening",
                                      color=discord.Color.red())
                msg = await self.main_channel.send(embed=embed)
                # self.messages[event['id']].alert_msg = msg

            elif end < now:
                print('{} ended'.format(event['summary']))
                self.events.remove(event)

    @check_alert_events.before_loop
    async def before_alert(self):
        await self.bot.wait_until_ready()
        print('Finished waiting')
