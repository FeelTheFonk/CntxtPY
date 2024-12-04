# regex_components/LocalizationProcessor.py

import re
from typing import List, Dict, Any
import os

class LocalizationProcessor:
    """
    LocalizationProcessor handles the mapping and extraction of localization and internationalization data.
    It identifies localization files, extracts translation keys and messages, and detects supported languages and locale patterns.
    """

    def __init__(self):
        # Precompile regex patterns
        self.locale_identifier_pattern = re.compile(
            r"""['"]([a-z]{2}_[A-Z]{2})['"]"""
        )
        self.gettext_pattern = re.compile(
            r"""_\(\s*['"](.+?)['"]\s*\)"""
        )
        self.po_entry_pattern = re.compile(
            r"""^msgid\s+['"](.+?)['"]\s*\nmsgstr\s+['"](.+?)['"]"""
        )
        self.mo_entry_pattern = re.compile(
            r"""^\x95\x04\x12\xde"""  # MO file magic number
        )

    def extract_localizations(self, content: str) -> List[Dict[str, Any]]:
        """
        Extracts localization usage from the given file content.

        :param content: The content of the Python file to analyze.
        :return: A list of dictionaries containing localization usage details.
        """
        localizations = []

        # Extract gettext messages
        gettext_messages = self.gettext_pattern.findall(content)
        for message in gettext_messages:
            localizations.append({
                'type': 'gettext_message',
                'message': message
            })

        return localizations

    def extract_locale(self, relative_path: str) -> str:
        """
        Extracts locale information based on the file path.

        :param relative_path: The relative path of the localization file.
        :return: The locale identifier if found, else 'unknown_locale'.
        """
        # Attempt to extract locale from file name, e.g., 'en_US', 'fr_FR'
        match = self.locale_identifier_pattern.search(relative_path)
        if match:
            return match.group(1)
        else:
            # Default or unknown locale
            return 'unknown_locale'

    def parse_po_file(self, content: str) -> List[Dict[str, str]]:
        """
        Parses a .po file content and extracts translation entries.

        :param content: The content of the .po file.
        :return: A list of dictionaries containing msgid and msgstr.
        """
        translations = []
        for match in self.po_entry_pattern.finditer(content):
            msgid, msgstr = match.groups()
            translations.append({
                'msgid': msgid,
                'msgstr': msgstr
            })
        return translations

    def is_mo_file(self, content: bytes) -> bool:
        """
        Checks if the given content corresponds to a .mo file based on magic numbers.

        :param content: The byte content of the file.
        :return: True if it's a .mo file, else False.
        """
        return bool(self.mo_entry_pattern.match(content.decode('latin1', errors='ignore')))

    def extract_localization_files(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts localization information from a localization file (.po or .mo).

        :param file_path: The path to the localization file.
        :return: A dictionary containing localization details.
        """
        localization_info = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if file_path.endswith('.po'):
                translations = self.parse_po_file(content)
                localization_info['type'] = 'po_file'
                localization_info['translations'] = translations
            elif file_path.endswith('.mo'):
                # For .mo files, parsing is non-trivial with regex; placeholder for actual parsing
                localization_info['type'] = 'mo_file'
                localization_info['info'] = 'Binary .mo files require specialized parsing.'
            else:
                localization_info['type'] = 'unknown'
        except Exception as e:
            localization_info['error'] = str(e)

        return localization_info
