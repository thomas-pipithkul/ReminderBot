import os

from discord.ext import tasks, commands
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Date/Time library
import tzlocal
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

from itertools import filterfalse

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


class AlertCog(commands.Cog):
    def __init__(self, bot, service):
        self.bot = bot
        self.service = service if service else self.get_service()
        self.last_updated = None
        self.events = self.get_today_events()

        self.check_alert_events.start()

    def get_service(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
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

        return build('calendar', 'v3', credentials=creds)

    def cog_unload(self):
        self.check_alert_events.cancel()

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

    @tasks.loop(seconds=1.0)
    async def check_alert_events(self):
        now = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(tz=None)
        channel = self.bot.guilds[0].text_channels[0]

        for event in list(self.events):
            start = event['start'].get('dateTime')
            start = datetime.fromisoformat(start)
            end = event['end'].get('dateTime')
            end = datetime.fromisoformat(end)
            delta = timedelta(minutes=15)
            # if now - start <= delta:
            if start <= now + delta:
                print('{} is starting in less than {} minutes'.format(event['summary'], 15))
                self.events.remove(event)
                await channel.send('{} is starting in {} minutes'.format(event['summary'], 15))
            elif start < now < end:
                print('{} is happening'.format(event['summary']))
                self.events.remove(event)
                await channel.send('{} is happening'.format(event['summary']))
            elif end < now:
                print('{} ended'.format(event['summary']))
                self.events.remove(event)

    @check_alert_events.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        print('Finished waiting')
