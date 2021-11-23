class Event:
    def __init__(self, title, start, tz, creator_id, attendee=None, create_msg=None, alert_msg=None):
        self.title = title
        self.start = start
        self.timeZone = tz
        self.creator_id = creator_id
        self.attendee = attendee if attendee else []
        self.create_msg = create_msg
        self.alert_msg = alert_msg

    def __repr__(self):
        return f'title={self.title} start={self.start} timeZone={self.timeZone} attendee={self.attendee} ' \
               f'create_msg={self.create_msg} alert_msg={self.alert_msg}'
