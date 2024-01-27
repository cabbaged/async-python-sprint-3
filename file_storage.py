from constants import SOURCE_PATH
import uuid


class FileStorage:
    STORAGE = SOURCE_PATH / 'file_storage'

    @classmethod
    def save(cls, reciever: str, data: bytes) -> str:
        cls._ensure_dir(reciever)
        filename = str(uuid.uuid4())
        destination_file = cls.STORAGE / reciever / filename
        destination_file.write_bytes(data)
        print(f'Saved file to {destination_file}')
        return filename

    @classmethod
    def load(cls, reciever: str, filename: str) -> bytes:
        file = cls.STORAGE / reciever / filename
        print(f'Reading file from {file}')
        return file.read_bytes()

    @classmethod
    def _ensure_dir(cls, reciever: str):
        dir = cls.STORAGE / reciever
        if not dir.exists():
            dir.mkdir(parents=True)
