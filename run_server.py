import argparse
import logging
import sys
import asyncio
from asyncio.streams import StreamReader, StreamWriter

from typing import Optional, Dict

from chat_storage import ChatStorage
from commands import ClientCommands
from constants import MAX_SIZE, GENERAL_CHAT
from file_storage import FileStorage
from subscribers import Subscribers


class ServerWorker:
    def __init__(self, reader, writer, chat_storage: ChatStorage, subscribers: Optional[Dict[str, StreamWriter]]):
        self.reader = reader
        self.writer = writer
        self.chat_storage = chat_storage
        self.current_chat = GENERAL_CHAT
        self.subscribers = subscribers
        self.username: Optional[str] = None

    async def init_user(self):
        username = await self.reader.read(1024)
        self.username = username.decode()
        self.subscribers[self.username] = self.writer
        await self.init_chat()

    async def read_client_data(self):
        while True:
            data: bytes = await self.reader.read(MAX_SIZE)
            if not data:
                break
            if data.startswith(ClientCommands.SWITCH_CHAT.encode()):
                logging.getLogger(__name__).info(f'Handling [{ClientCommands.SWITCH_CHAT}]')
                _, chat = data.split()
                self.current_chat = chat.decode()
                await self.init_chat()
            elif data.startswith(ClientCommands.UPLOAD_FILE.encode()):
                logging.getLogger(__name__).info(f'Handling [{ClientCommands.UPLOAD_FILE}]')
                _, file = data.split(maxsplit=1)
                filename = FileStorage.save(self.current_chat, file)
                await self.handle_new_message(f'Available file with file-id {filename}'
                                              f' Type "download", then follow instructions to download it')
            elif data.startswith(ClientCommands.DOWNLOAD_FILE.encode()):
                logging.getLogger(__name__).info(f'Handling [{ClientCommands.DOWNLOAD_FILE}]')
                _, file_id, filepath = data.split(maxsplit=2)
                self.writer.write(b' '.join((
                    b'$file',
                    filepath,
                    FileStorage.load(GENERAL_CHAT if self.is_general() else self.username, file_id.decode())
                )))

                await self.writer.drain()
            else:
                message = data.decode()
                logging.getLogger(__name__).info(f'Recieved message [{message}]')
                await self.handle_new_message(message)

    async def handle_new_message(self, message: str):
        message = self.render_message(self.username, message)
        self.chat_storage.put(message, self.current_chat)
        if self.is_general():
            recipients = self.subscribers.values()
        else:
            recipients = [self.subscribers[user] for user in {self.current_chat, self.username}]

        logging.getLogger(__name__).info(f'Sending message to {len(recipients)} users')
        for sub_writer in recipients:
            sub_writer.write(message.encode())
            await sub_writer.drain()

    async def init_chat(self):
        self.writer.write(self.chat_storage.read_chat(self.current_chat).encode())
        await self.writer.drain()

    def create_chat_key(self, recipient_user: str):
        if recipient_user == GENERAL_CHAT:
            return recipient_user
        return (self.username, recipient_user) if self.username > recipient_user else (recipient_user, self.username)

    def render_message(self, username: str, message: str) -> str:
        if self.is_general():
            return f'[{username}] {message}'
        return f'[{username}][private] {message}'

    def is_general(self) -> bool:
        return self.current_chat == GENERAL_CHAT


async def client_connected(reader: StreamReader, writer: StreamWriter):
    address = writer.get_extra_info('peername')
    logger.info('Start serving %s', address)
    worker = ServerWorker(reader, writer, ChatStorage.get_storage(), Subscribers.get_instance())
    await worker.init_user()
    await worker.read_client_data()

    logger.info('Stop serving %s', address)
    writer.close()
    Subscribers.get_instance().pop(worker.username, None)


async def main(host: str, port: int):
    ChatStorage.init_storage()
    srv = await asyncio.start_server(
        client_connected, host, port)

    addrs = ', '.join(str(sock.getsockname()) for sock in srv.sockets)
    logging.getLogger(__name__).info(f'Serving on {addrs}')
    async with (srv):
        await srv.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Chat Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host address to bind (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000, help='Port number to bind (default: 8000)')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(stream=sys.stdout))

    args = parser.parse_args()
    asyncio.run(main(args.host, args.port))
