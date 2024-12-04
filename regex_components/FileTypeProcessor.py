# FileTypeProcessor.py

import os
import chardet
from typing import Optional
from enum import Enum


class FileType(Enum):
    SOURCE_CODE = 'source_code'
    BINARY = 'binary'
    TEXT = 'text'
    IMAGE = 'image'
    VIDEO = 'video'
    AUDIO = 'audio'
    ARCHIVE = 'archive'
    DOCUMENTATION = 'documentation'
    CONFIG = 'config'
    DATA = 'data'
    TEST_CODE = 'test_code'
    EXAMPLE_CODE = 'example_code'
    OTHER = 'other'


class FileInfo:
    def __init__(self, type: FileType, encoding: Optional[str], extension: str, purpose: str):
        self.type = type
        self.encoding = encoding
        self.extension = extension
        self.purpose = purpose


class FileTypeProcessor:
    def __init__(self):
        # Define known file extensions and their types
        self.extension_map = {
            '.py': FileType.SOURCE_CODE,
            '.txt': FileType.TEXT,
            '.md': FileType.DOCUMENTATION,
            '.rst': FileType.DOCUMENTATION,
            '.cfg': FileType.CONFIG,
            '.ini': FileType.CONFIG,
            '.json': FileType.CONFIG,
            '.yaml': FileType.CONFIG,
            '.yml': FileType.CONFIG,
            '.jpg': FileType.IMAGE,
            '.jpeg': FileType.IMAGE,
            '.png': FileType.IMAGE,
            '.gif': FileType.IMAGE,
            '.bmp': FileType.IMAGE,
            '.svg': FileType.IMAGE,
            '.mp4': FileType.VIDEO,
            '.avi': FileType.VIDEO,
            '.mp3': FileType.AUDIO,
            '.wav': FileType.AUDIO,
            '.zip': FileType.ARCHIVE,
            '.tar': FileType.ARCHIVE,
            '.gz': FileType.ARCHIVE,
            '.csv': FileType.DATA,
            '.tsv': FileType.DATA,
            '.xls': FileType.DATA,
            '.xlsx': FileType.DATA,
            '.pickle': FileType.DATA,
            '.pkl': FileType.DATA,
            # Add more extensions as needed
        }

    def process_file(self, file_path: str) -> Optional[FileInfo]:
        """
        Determines the file type, encoding, extension, and purpose.
        """
        if not os.path.isfile(file_path):
            return None

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        file_type = self.extension_map.get(ext, FileType.OTHER)

        encoding = self.detect_file_encoding(file_path)
        if encoding is None and file_type == FileType.OTHER:
            file_type = FileType.BINARY

        purpose = self.determine_file_purpose(file_path, file_type)

        file_info = FileInfo(
            type=file_type,
            encoding=encoding,
            extension=ext,
            purpose=purpose
        )

        return file_info

    def detect_file_encoding(self, file_path: str) -> Optional[str]:
        """
        Detects the file encoding using chardet library.
        """
        try:
            with open(file_path, 'rb') as f:
                rawdata = f.read(10000)  # Read first 10KB
            if b'\x00' in rawdata:
                # Null byte detected, likely a binary file
                return None
            result = chardet.detect(rawdata)
            encoding = result['encoding']
            return encoding
        except Exception:
            return None

    def determine_file_purpose(self, file_path: str, file_type: FileType) -> str:
        """
        Determines the file's purpose based on its type, location, and content.
        """
        purpose = file_type.value

        # Infer purpose from file path
        path_lower = file_path.lower()
        if 'test' in path_lower or 'tests' in path_lower:
            purpose = 'test_code'
        elif 'doc' in path_lower or 'docs' in path_lower:
            purpose = 'documentation'
        elif 'example' in path_lower or 'examples' in path_lower:
            purpose = 'example_code'
        elif file_type == FileType.CONFIG:
            purpose = 'configuration'
        elif file_type == FileType.DATA:
            purpose = 'data'
        elif file_type == FileType.IMAGE:
            purpose = 'asset'
        elif file_type == FileType.SOURCE_CODE:
            purpose = 'source_code'
        else:
            purpose = 'other'

        # Check for shebang line to identify scripts
        if file_type == FileType.SOURCE_CODE:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if first_line.startswith('#!'):
                        purpose = 'executable_script'
            except Exception:
                pass

        return purpose
