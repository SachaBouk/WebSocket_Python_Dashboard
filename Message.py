import json

class ENVOI_TYPE:
    TEXT = "ENVOI_TEXT"
    IMAGE = "ENVOI_IMAGE"
    AUDIO = "ENVOI_AUDIO"
    VIDEO = "ENVOI_VIDEO"
    CLIENT_LIST = "ENVOI_CLIENT_LIST"

class RECEPTION_TYPE:
    TEXT = "RECEPTION_TEXT"
    IMAGE = "RECEPTION_IMAGE"
    AUDIO = "RECEPTION_AUDIO"
    VIDEO = "RECEPTION_VIDEO"
    CLIENT_LIST = "RECEPTION_CLIENT_LIST"

class ADMIN_TYPE:
    ROUTING_LOG = "ADMIN_ROUTING_LOG"
    CLIENT_CONNECTED = "ADMIN_CLIENT_CONNECTED"
    CLIENT_DISCONNECTED = "ADMIN_CLIENT_DISCONNECTED"
    CLIENT_LIST_FULL = "ADMIN_CLIENT_LIST_FULL"

class MessageType:
    DECLARATION = "DECLARATION"
    ENVOI = ENVOI_TYPE
    RECEPTION = RECEPTION_TYPE
    ADMIN = ADMIN_TYPE
    WARNING = "WARNING"
    SYS_MESSAGE = "SYS_MESSAGE"

class Message:
    def __init__(self, message_type: MessageType, value, emitter, receiver=None):
        self.message_type = message_type
        self.value = value
        self.emitter = emitter
        self.receiver = receiver

    @staticmethod
    def default_message():
        return Message(MessageType.DECLARATION, "System", "This is a default message", "All")

    @staticmethod
    def from_json(json_data):
        data = json.loads(json_data)
        message_type = data['message_type']
        emitter = data['data']['emitter']
        receiver = data['data'].get('receiver', None)
        value = data['data']['value']
        return Message(message_type, value, emitter, receiver)

    def to_json(self):
        data = {
            'message_type': self.message_type,
            'data': {
                'emitter': self.emitter,
                'receiver': self.receiver,
                'value': self.value
            }
        }

        return json.dumps(data)

message = Message(MessageType.DECLARATION, emitter="System", receiver="All", value="This is a test message")
messageRebuild = Message.from_json(message.to_json())
