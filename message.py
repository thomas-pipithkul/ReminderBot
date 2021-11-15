class Message:
    def __init__(self, event, created_msg, alert_msg=None):
        self.event = event
        self.created_msg = created_msg
        self.alert_msg = alert_msg
        self.eid = event['id']
