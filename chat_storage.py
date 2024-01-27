import datetime

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict


@dataclass
class ChatMessage:
    message: str
    ttl: datetime.timedelta
    created: datetime.datetime = datetime.datetime.now()

    def is_expired(self):
        return datetime.datetime.now() - self.created > self.ttl


class ChatStorage:
    instance: 'ChatStorage'

    @classmethod
    def init_storage(cls, *args, **kwargs):
        cls.instance = cls(*args, **kwargs)

    @classmethod
    def get_storage(cls):
        return cls.instance

    def __init__(self, message_num: int = 20, ttl: datetime.timedelta = datetime.timedelta(hours=1)):
        self.ttl: datetime.timedelta = ttl
        self.storage: Dict[str, Deque[ChatMessage]] = defaultdict(lambda: deque(maxlen=message_num))

    def put(self, message: str, chat: str):
        self.storage[chat].append(ChatMessage(message, self.ttl))

    def read_chat(self, chat: str) -> str:
        return '\n'.join(
            msg.message for msg in self.storage[chat] if not msg.is_expired()
        )
