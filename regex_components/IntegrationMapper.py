# regex_components/IntegrationMapper.py

import re
from typing import List, Dict, Any

class IntegrationMapper:
    """
    IntegrationMapper extracts information about external integrations within Python codebases.
    It identifies API endpoints, URLs, SDK configurations, service connections, and external library usages.
    """

    def __init__(self):
        # Precompile regex patterns for efficiency
        self.url_pattern = re.compile(
            r"""(?i)\b(?:https?://|ftp://|file://|mailto:|tel:|data:)[^\s'"]+"""
        )
        self.api_key_pattern = re.compile(
            r"""(?i)(?:api_key|apikey|apiKey|API_KEY)\s*[:=]\s*['"]([A-Za-z0-9-_]{20,})['"]"""
        )
        self.import_pattern = re.compile(
            r"""^\s*import\s+([a-zA-Z0-9_.]+)|^\s*from\s+([a-zA-Z0-9_.]+)\s+import\s+"""
        )
        self.sdk_init_pattern = re.compile(
            r"""(?:initialize|init|setup)\s*\(\s*['"]([a-zA-Z0-9_.]+)['"]\s*,\s*(?:api_key\s*=\s*['"]([^'"]+)['"])?"""
        )
        self.service_connection_pattern = re.compile(
            r"""(?:connect|setup_connection|configure)\s*\(\s*['"]([a-zA-Z0-9_.]+)['"]\s*,\s*['"]([a-zA-Z0-9_.:/\-]+)['"]"""
        )
        self.credentials_pattern = re.compile(
            r"""(?i)(?:username|user|password|pwd|secret|token)\s*[:=]\s*['"]([^'"]+)['"]"""
        )
        self.external_libs = set([
            'requests', 'boto3', 'django', 'flask', 'sqlalchemy', 'celery',
            'stripe', 'twilio', 'firebase', 'pandas', 'numpy', 'torch', 'tensorflow',
            'google', 'aws', 'azure', 'slack_sdk', 'discord', 'facebook', 'twitter'
        ])

    def extract_integrations(self, content: str) -> List[Dict[str, Any]]:
        """
        Extracts integration information from the given file content.

        :param content: The content of the file to analyze.
        :return: A list of dictionaries containing integration details.
        """
        integrations = []

        # Extract URLs
        urls = self.url_pattern.findall(content)
        for url in urls:
            integrations.append({
                'type': 'URL',
                'value': url
            })

        # Extract API keys
        api_keys = self.api_key_pattern.findall(content)
        for key in api_keys:
            integrations.append({
                'type': 'API Key',
                'value': key
            })

        # Extract imported external libraries
        imports = self.import_pattern.findall(content)
        for imp in imports:
            module = imp[0] if imp[0] else imp[1]
            if module.split('.')[0] in self.external_libs:
                integrations.append({
                    'type': 'External Library',
                    'value': module
                })

        # Extract SDK initialization
        sdk_inits = self.sdk_init_pattern.findall(content)
        for sdk_init in sdk_inits:
            sdk_name, api_key = sdk_init
            integration = {
                'type': 'SDK Initialization',
                'sdk_name': sdk_name
            }
            if api_key:
                integration['api_key'] = api_key
            integrations.append(integration)

        # Extract service connections
        service_connections = self.service_connection_pattern.findall(content)
        for connection in service_connections:
            service_name, endpoint = connection
            integrations.append({
                'type': 'Service Connection',
                'service_name': service_name,
                'endpoint': endpoint
            })

        # Extract credentials
        credentials = self.credentials_pattern.findall(content)
        for credential in credentials:
            integrations.append({
                'type': 'Credential',
                'value': credential
            })

        # Remove duplicates by converting list of dicts to a set of tuples and back
        unique_integrations = []
        seen = set()
        for integration in integrations:
            integration_tuple = tuple(sorted(integration.items()))
            if integration_tuple not in seen:
                seen.add(integration_tuple)
                unique_integrations.append(integration)

        return unique_integrations
