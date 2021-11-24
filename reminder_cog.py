import os
import pymongo
import discord
from discord.ext import tasks, commands
from event import Event

import asyncio

# Util
import json
from util import StringFmt, CustomEmbed, DateTimeFmt, GoogleCalendarHttp

# Date/Time library
import dateparser
import parsedatetime
import pytz
from datetime import datetime, date, time, timedelta


class ReminderCog(commands.Cog):
    def __init__(self, bot):
        # MongoDB
        self.eventsCollection = None
        self.connect_mongodb_atlas()

        # Discord Bot Info
        self.bot = bot
        self.tz = 'US/Eastern'  # default timezone
        # self.main_channel = bot.guilds[0].text_channels[0] if bot.guilds and bot.guilds[0].text_channels else None

        self.last_updated = None
        self.events = self.get_today_events()

        self.check_alert_events.start()

    @commands.Cog.listener()
    async def on_ready(self):
        pass
        # self.main_channel = self.bot.guilds[0].text_channels[0]

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        print('error: ', end='')

        cmd = ctx.invoked_with
        if isinstance(error, commands.MissingRequiredArgument):
            print('missing required arg')
        elif isinstance(error, commands.BadArgument):
            print('bad arg')
            if cmd == 'upcoming':
                embed = CustomEmbed.get_upcoming_error_embed()
                await ctx.send(embed=embed)
        else:
            print(error)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        emoji, user = payload.emoji, payload.member

        # Proceed if reaction didn't come from this bot
        if user == self.bot.user:
            return

        if str(emoji) == '✅':
            channel = self.bot.get_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            await msg.remove_reaction('✅', user)
        elif str(emoji) == '🗑️':
            await self.raw_react_delete_create_msg(payload)

    async def raw_react_delete_create_msg(self, payload):
        user = payload.member
        channel = self.bot.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)

        # Ignore if user didn't react to the bot message
        if msg.author != self.bot.user:
            return

        # Check DB if this message is the create_msg
        result = self.eventsCollection.find_one(filter={'create_msg.message_id': msg.id})
        if result and user.id == result.get('creator_id'):  # Creator of the event reacted to create_msg
            # Delete the event on DB & local list
            self.eventsCollection.delete_one(filter={'create_msg.message_id': msg.id})
            self.events = [e for e in self.events if not (e['_id'] == result['_id'])]

            # Modified created msg embed
            title = msg.embeds[0].title
            title = title.rstrip('✅') if title else ''
            value = msg.embeds[0].fields[0].value
            footer_str = msg.embeds[0].footer.text
            new_embed = CustomEmbed.get_create_embed(f'{title} ( 🚫 Cancelled )', f'~~{value}~~', footer_str)
            await msg.edit(embed=new_embed)
            await msg.clear_reactions()

            # Already alerted
            alert_msg = result.get('alert_msg')
            if alert_msg:
                alert_msg = await channel.fetch_message(alert_msg['message_id'])
                await alert_msg.delete()

    def connect_mongodb_atlas(self):
        # Load mongodb credentials from config file/heroku config vars
        if 'MONGODB_USER' in os.environ and 'MONGODB_PASS' in os.environ:
            username = os.environ.get('MONGODB_USER')
            password = os.environ.get('MONGODB_PASS')

            uri = f'mongodb+srv://{username}:{password}@reminderbot-cluster.wrdgt.mongodb.net/test?retryWrites=true&w=majority'
            client = pymongo.MongoClient(uri)
            db = client.reminderBot
            self.eventsCollection = db.events
        else:
            with open('./config.json', 'r') as f:
                config_dict = json.load(f)
                username, password = config_dict['username'], config_dict['password']

                uri = f'mongodb+srv://{username}:{password}@reminderbot-cluster.wrdgt.mongodb.net/test?retryWrites=true&w=majority'
                client = pymongo.MongoClient(uri)
                db = client.reminderBot
                self.eventsCollection = db.events

    def get_channel(self, channel_id):
        return discord.utils.get(self.bot.get_all_channels(), id=channel_id)

    async def get_message(self, channel_id, message_id):
        return await self.get_channel(channel_id).fetch_message(message_id)

    def get_today_events(self):
        now = pytz.utc.localize(datetime.utcnow())
        tmr = pytz.utc.localize(datetime.utcnow()) + timedelta(days=1)
        self.last_updated = now
        events_results = list(self.eventsCollection.find({'start': {'$gt': now, '$lte': tmr}}))
        events = []
        for event in events_results:
            event['start'] = pytz.utc.localize(event['start'])
            events.append(event)
        return events

    def remove_dup_events(self, events):
        seen_id = set()
        new_list = []
        for event in events:
            if event['_id'] not in seen_id:
                new_list.append(event)
                seen_id.add(event['_id'])
        return new_list

    async def calendar_event_react(self, ctx, msg, title, start, time_str):
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in '✅🗑️'

        footer_str = f'✅ Confirm | 🗑️ Delete | Created by {ctx.author.display_name}'
        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=60.0 * 1)

            # Insert it to MongoDB
            if str(reaction.emoji) == '✅':
                start = start.astimezone(pytz.utc)  # convert to UTC for db
                event = Event(title, start, self.tz, ctx.author.id)
                event.create_msg = {
                    'channel_id': ctx.channel.id,
                    'message_id': msg.id,
                    'jump_url': msg.jump_url
                }
                self.eventsCollection.insert_one(event.__dict__)
                self.events.append(event.__dict__)
                self.events = self.remove_dup_events(self.events)
                sorted(self.events, key=lambda e: e['start'])

                await msg.remove_reaction('✅', user)
                new_embed = CustomEmbed.get_create_embed(f'🗓️ {title} ✅', time_str, footer_str)
                await msg.edit(embed=new_embed)

            # Cancel the reaction
            elif str(reaction.emoji) == '🗑️':
                new_embed = CustomEmbed.get_create_embed(f'🗓️ {title} ( 🚫 Cancelled )', f'~~{time_str}~~', footer_str)
                await msg.edit(embed=new_embed)
                await msg.clear_reactions()

        except asyncio.TimeoutError:
            new_embed = CustomEmbed.get_create_embed(f'🗓️ {title} ( 🚫 Timed out )', f'~~{time_str}~~', footer_str)
            await msg.edit(embed=new_embed)
            await msg.clear_reactions()

    def parse_upcoming(self, arg):
        tz = pytz.timezone(self.tz)
        limit, flag, after = 5, 0, pytz.utc.localize(datetime.utcnow())  # default value
        now_local = datetime.now().astimezone(tz)

        # There is arg for limit
        if arg and arg[0].isnumeric():
            limit = int(arg[0])

        # There could be arg for datetime filter
        if arg:
            ret = parsedatetime.Calendar().nlp(' '.join(arg), now_local)  # use natural language parsing for datetime
            if ret:
                dt = ret[0]  # use first datetime found
                flag = dt[1]
                after = tz.localize(dt[0])
                after = after.astimezone(pytz.utc)
        return limit, flag, after

    @commands.command()
    async def parse(self, ctx, *, dt_str):
        tz = pytz.timezone(self.tz)
        now_local = datetime.now().astimezone(tz)

        # find where is the time specify in the argument
        cal = parsedatetime.Calendar()
        ret = cal.nlp(dt_str, now_local)  # use natural language parsing
        if ret is not None:
            ret = ret[0]
            parsed_datetime = ret[0]
            await ctx.send(parsed_datetime.strftime("%m/%d/%Y, %I:%M:%S %Z %z"))
        else:
            await ctx.send("I don't know")

    @commands.command()
    async def now(self, ctx):
        tz = pytz.timezone(self.tz)
        now_utc = pytz.utc.localize(datetime.utcnow()).strftime("%m/%d/%Y, %I:%M:%S %Z %z")
        now_local = datetime.now().astimezone(tz).strftime("%m/%d/%Y, %I:%M:%S %Z %z")
        await ctx.send(f'now utc: {now_utc}\nnow local: {now_local}')

    @commands.command()
    async def upcoming(self, ctx, *arg):
        limit, flag, after = self.parse_upcoming(arg)
        after = DateTimeFmt.re_parse(flag, after)

        # query data from MongoDB db
        events = (
            # get {limit} events that starts after now...
            self.eventsCollection.find(filter={'start': {'$gte': after}}, limit=limit)
        ).sort('start', pymongo.ASCENDING)  # ... in ascending order

        # Notify the Discord users accordingly
        events = list(events)  # convert events from pymongo cursor to list
        if not events:
            embed = discord.Embed(title='No upcoming events found.', color=discord.Color.blue())
            await ctx.send(embed=embed)
        else:
            embed = CustomEmbed.get_upcoming_embed(events, limit, after, self.tz)
            await ctx.send(embed=embed)

    @commands.command(name='create')
    async def add_calendar_event(self, ctx, *, arg):
        tz = pytz.timezone(self.tz)
        now_local = datetime.now().astimezone(tz)

        # find where is the time specify in the argument
        cal = parsedatetime.Calendar()
        ret = cal.nlp(arg, now_local)  # use natural language parsing assuming the bot tz

        # Check the return value from natural language parsing
        if ret is not None:
            ret = ret[0]
            parsed_datetime = ret[0]
            start_date_pos = ret[2]

            # parse title (message from beginning to the character before the date
            title = arg[:start_date_pos].strip()  # remove leading + trailing whitespaces

            # title found
            if title:
                # Add bot timezone to parsed_datetime
                tz = pytz.timezone(self.tz)
                local_parsed_dt = tz.localize(parsed_datetime)

                # Ask user to confirm the event on discord with embedded message
                # time_str = local_parsed_dt.strftime("%I:%M %p %a, %b %d, %Y %Z")
                time_str = StringFmt.get_time_str(title, local_parsed_dt)
                footer_str = f'✅ Confirm | 🗑️ Delete | Created by {ctx.author.display_name}'
                embed = CustomEmbed.get_create_embed(f'🗓️ {title}', time_str, footer_str)
                msg = await ctx.send(embed=embed)
                await msg.add_reaction('✅')
                await msg.add_reaction('🗑️')
                await self.calendar_event_react(ctx, msg, title, local_parsed_dt, time_str)
            else:  # No title found
                # Notify discord with fail embedded message
                embed = discord.Embed(title='Event creation failed :(',
                                      description="Missing title for the event",
                                      color=discord.Color.blue())
                await ctx.send(embed=embed)

        # the parsing datetime failed (return None)
        else:
            # Notify discord with fail embedded message
            embed = discord.Embed(title='Event creation failed :(',
                                  description="I don't understand the time of the event",
                                  color=discord.Color.blue())
            await ctx.send(embed=embed)

    async def send_alert_msg(self, event, new_embed):
        channel_id = event['create_msg']['channel_id']
        channel = self.bot.get_channel(channel_id)
        msg = await channel.send(embed=new_embed)

        # update runtime event object & the database
        event['alert_msg'] = {
            'channel_id': event['create_msg']['channel_id'],
            'message_id': msg.id,
            'jump_url': msg.jump_url
        }
        self.eventsCollection.update_one({'_id': event['_id']}, {'$set': event})

    async def update_alert_msg(self, emoji, event, timer_str, discord_color):
        desc = f"**[Event Detail]({event['create_msg']['jump_url']})**"
        new_embed = discord.Embed(title=f"{emoji} **{event['title']}** {timer_str}",
                                  description=desc,
                                  color=discord_color)

        # Send an embed if this event hasn't been alert, else update the embed
        if not event['alert_msg']:
            await self.send_alert_msg(event, new_embed)
        else:
            channel_id = event['alert_msg']['channel_id']
            message_id = event['alert_msg']['message_id']
            try:
                msg = await self.get_message(channel_id, message_id)
                await msg.edit(embed=new_embed)
            except discord.NotFound:
                await self.send_alert_msg(event, new_embed)

    @tasks.loop(seconds=1.0)
    async def check_alert_events(self):
        now = pytz.utc.localize(datetime.utcnow())

        # If last updated was more than a day, get today's events
        if not self.last_updated and self.last_updated < now + timedelta(days=1):
            self.events += self.get_today_events()
            self.events = self.remove_dup_events(self.events)
            sorted(self.events, key=lambda e: e['start'])

        # Check the events and process it if it's the start time
        now = now.astimezone(pytz.timezone(self.tz))  # convert utc time to bot timezone
        for event in list(self.events):
            start = event['start'].astimezone(pytz.timezone(event['timeZone']))
            delta = timedelta(minutes=1)

            # Event is starting in delta time
            if start - delta <= now <= start:
                # time_str = StringFmt.format_start_str(start - now)
                epoch = int(start.timestamp())
                time_str = f'<t:{epoch}:R>'  # relative unix time displayed
                await self.update_alert_msg('⏰', event, f"starts {time_str}", discord.Color.gold())

            # Event has started
            elif start < now <= start + delta:
                await self.update_alert_msg('🔔', event, f" is starting!!", discord.Color.red())

            # Event started long ago
            elif start + delta < now:
                self.events.remove(event)

    @check_alert_events.before_loop
    async def before_alert(self):
        await self.bot.wait_until_ready()
        print('Reminder Cog is ready')
