import discord
import pytz
from datetime import datetime, timedelta


class StringFmt:
    @staticmethod
    def get_time_str(title: str, start: datetime):
        url = GoogleCalendarHttp.get_event_url(title, start)
        epoch = int(start.timestamp())
        return f'<t:{epoch}:F> [[Add]]({url} "Add {title} to Google Calendar")'

    @staticmethod
    def field_date_format(start_date, tz_str):
        today = datetime.now(pytz.timezone(tz_str)).today().date()
        tomorrow = today + timedelta(days=1)
        if today == start_date:
            return f'Today [{start_date:%b} {start_date:%d}]'
        elif tomorrow == start_date:
            return f'Tomorrow [{start_date:%b} {start_date:%d}]'
        elif today.year == start_date.year:
            return f"{start_date:%A} [{start_date:%b} {start_date:%d}]"
        else:
            return f"{start_date:%A} [{start_date:%b} {start_date:%d}, {start_date:%Y}]"

    @staticmethod
    def format_start_str(delta):
        td_d, td_h, td_m = timedelta(days=1), timedelta(hours=1), timedelta(minutes=1)

        # hours & minutes left
        if timedelta(hours=1) < delta:
            return f'{(delta % td_d) // td_h} hours {(delta % td_h) // td_m} minutes'
        # minutes left
        elif td_m <= delta:
            return f'{(delta % td_h) // td_m + 1} minutes'
        # 1 minute left
        elif timedelta(minutes=0) < delta < td_m:
            return '1 minute'
        else:
            return '0 minute'


class GoogleCalendarHttp:
    @staticmethod
    def get_event_url(title: str, start: datetime):
        start = start.astimezone(pytz.utc)  # convert to UTC
        base_url = 'http://www.google.com/calendar/event?'
        action = 'action=TEMPLATE'
        end = start + timedelta(hours=1)
        start = start.strftime('%Y%m%dT%H%M%SZ')
        end = end.strftime('%Y%m%dT%H%M%SZ')
        title = title.replace(' ', '%20')
        return f"{base_url}{action}&text={title}&dates={start}/{end}"


class DateTimeFmt:
    @staticmethod
    def re_parse(flag, utc_dt: datetime):
        dt_flags = {'invalid': 0, 'date': 1, 'time': 2, 'datetime': 3}
        if flag == dt_flags['date']:
            return datetime.combine(utc_dt.date(), datetime.min.time())
        elif flag == dt_flags['time']:
            return utc_dt
        elif flag == dt_flags['datetime']:
            return utc_dt
        else:
            return pytz.utc.localize(datetime.utcnow())


class CustomEmbed:
    @staticmethod
    def get_create_embed(title, time_str, footer_str):
        embed = discord.Embed(title=title, color=discord.Color.blue())
        embed.add_field(name='Time', value=time_str, inline=False)
        embed.set_footer(text=f'{footer_str}')
        return embed

    @staticmethod
    def get_upcoming_error_embed():
        embed = discord.Embed(title="Upcoming Events: `Invalid Argument :(`", color=discord.Color.blue())
        embed.add_field(name='!upcoming', value=f'List upcoming 5 events\n> `.upcoming`', inline=False)
        embed.add_field(name='!upcoming [amount]', value=f'List upcoming [amount] events\n> `.upcoming 10`',
                        inline=False)
        embed.add_field(name='!upcoming [date]',
                        value=f'List upcoming 5 events after [date]\n> `.upcoming tomorrow`',
                        inline=False)
        embed.add_field(name='!upcoming [amount] [date]',
                        value=f'List upcoming [amount] events after [date]\n> `.upcoming 2 next week`',
                        inline=False)
        return embed

    @staticmethod
    def get_upcoming_embed(events, limit: int, after: datetime, tz_str: str):
        epoch = int(after.timestamp())
        embed = discord.Embed(title='📃 Upcoming Events',
                              description=f'List up to **`{limit}`** upcoming events\nfrom <t:{epoch}>',
                              color=discord.Color.blue())

        prev_date = None
        for event in events:
            # Inject UTC timezone & convert to bot timezone
            start = pytz.utc.localize(event['start'])
            start = start.astimezone(pytz.timezone(tz_str))
            s_epoch = int(start.timestamp())
            start, time = start.date(), start.time()

            title = event['title']
            field_title = StringFmt.field_date_format(start, tz_str)
            jump_url = event['create_msg'].get('jump_url')

            # Insert start time on the same date into the same field, else new field
            if prev_date and start == prev_date:
                i = len(embed.fields) - 1  # index to insert => last index since events are sorted
                value = embed.fields[i].value + f"\n`{time:%I:%M%p}` **[{title}]({jump_url})** <t:{s_epoch}:R>"
                embed.set_field_at(index=i, name=field_title, value=value, inline=False)
            else:
                embed.add_field(name=field_title,
                                value=f">>> `{time:%I:%M%p}` **[{title}]({jump_url})** <t:{s_epoch}:R>",
                                inline=False)
                prev_date = start

        tz = pytz.timezone(tz_str)
        now_local = datetime.now().astimezone(tz)
        utc_offset = now_local.strftime('%z')
        utc_offset = f"{utc_offset[:-2]}:{utc_offset[-2:]}"
        embed.set_footer(text=f'🌐 {tz_str} (UTC{utc_offset})')
        return embed

































































