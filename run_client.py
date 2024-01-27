import argparse
import asyncio
from asyncio import StreamReader, StreamWriter
from pathlib import Path

import aioconsole

from commands import UserCommands, ServerCommands
from constants import MAX_SIZE
from run_server import ClientCommands


class ClientHandler:
    def __init__(self, reader: StreamReader, writer: StreamWriter, username: str):
        self.reader = reader
        self.writer = writer
        self.username = username
        self.lock = asyncio.Lock()

    async def client_exit(self):
        await self.writer.wait_closed()

    async def handle_command(self):
        while True:
            command = await aioconsole.ainput()
            if command.strip() == UserCommands.EXIT:
                await self.client_exit()
                break
            elif command.strip() == UserCommands.UPLOAD:
                await self.upload_file()
            elif command.strip() == UserCommands.DOWNLOAD:
                await self.download_file()
            else:
                await self.handle_message(command)

    async def handle_message(self, message: str):
        self.writer.write(message.encode())
        await self.writer.drain()

    async def handle_server(self):
        while True:
            data = await self.reader.read(MAX_SIZE)
            if data.startswith(ServerCommands.FILE.encode()):
                _, filepath, file = data.split(maxsplit=2)
                Path(filepath.decode()).write_bytes(file)
                print('File downloaded')
            else:
                print(data.decode())

    async def register(self):
        self.writer.write(self.username.encode())
        await self.writer.drain()

    async def upload_file(self):
        filepath = await aioconsole.ainput('Please, enter full path to file. '
                                           'It will be sent to your current chat\n')
        self.writer.write(b' '.join((
            ClientCommands.UPLOAD_FILE.encode(),
            Path(filepath).read_bytes()
        )))

        await self.writer.drain()

    async def download_file(self):
        data = await aioconsole.ainput(
            'Type "{file-id} {filepath}", example: "53ec6720-a488-41c4-8617-9e0ab4c0f2de ./my_downloaded_file" \n')
        file_id, filepath = data.split(maxsplit=1)
        self.writer.write(f'{ClientCommands.DOWNLOAD_FILE} {file_id} {filepath}'.encode())
        await self.writer.drain()


async def tcp_echo_client():
    args = parse_args()
    reader, writer = await asyncio.open_connection(
        args.host, args.port)
    handler = ClientHandler(reader, writer, args.username)
    await asyncio.gather(
        handler.register(),
        handler.handle_command(),
        handler.handle_server()
    )


def parse_args():
    parser = argparse.ArgumentParser(description='Async Chat Client')
    parser.add_argument('--username', required=True, help='Your username for the chat')
    parser.add_argument('--host', default='127.0.0.1', help='Host address to bind (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000, help='Port number to bind (default: 8000)')
    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(tcp_echo_client())
