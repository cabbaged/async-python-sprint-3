from asyncio import StreamWriter
from typing import Optional, Dict


class Subscribers(dict):
    instance: Optional[Dict[str, StreamWriter]] = None

    @classmethod
    def get_instance(cls) -> Dict[str, StreamWriter]:
        if not cls.instance:
            cls.instance = Subscribers()
        return cls.instance
