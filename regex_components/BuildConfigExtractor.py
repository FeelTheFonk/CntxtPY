# BuildConfigExtractor.py

import re
import os
from typing import List, Dict, Any
import yaml
import configparser
import toml
import logging

class BuildConfigExtractor:
    """
    Processes build configuration files to extract build and installation commands,
    environment variables, package metadata, and YAML configurations from CI/CD pipelines.
    """

    def __init__(self):
        # Initialize any required variables or data structures
        self.setup_py_patterns = {
            'install_requires': re.compile(r'install_requires\s*=\s*\[(.*?)\]', re.DOTALL),
            'packages': re.compile(r'packages\s*=\s*\[(.*?)\]', re.DOTALL),
            'entry_points': re.compile(r'entry_points\s*=\s*\{(.*?)\}', re.DOTALL),
        }
        self.dockerfile_patterns = {
            'commands': re.compile(r'^\s*(RUN|CMD|ENTRYPOINT|ENV|EXPOSE|VOLUME|WORKDIR)\s+(.*)', re.MULTILINE),
        }
        self.makefile_patterns = {
            'target': re.compile(r'^([a-zA-Z0-9_-]+)\s*:\s*(.*)'),
        }
        logging.basicConfig(level=logging.INFO)

    def extract_setup_py(self, file_content: str) -> Dict[str, Any]:
        """
        Extracts package metadata from setup.py files.
        """
        metadata = {}
        for key, pattern in self.setup_py_patterns.items():
            match = pattern.search(file_content)
            if match:
                metadata[key] = self._clean_list_string(match.group(1))
        return metadata

    def extract_setup_cfg(self, file_content: str) -> Dict[str, Any]:
        """
        Extracts package metadata from setup.cfg files.
        """
        config = configparser.ConfigParser()
        config.read_string(file_content)
        metadata = {}
        if 'options' in config:
            if 'install_requires' in config['options']:
                metadata['install_requires'] = self._clean_list_string(config['options']['install_requires'])
            if 'packages' in config['options']:
                metadata['packages'] = self._clean_list_string(config['options']['packages'])
        return metadata

    def extract_tox_ini(self, file_content: str) -> Dict[str, Any]:
        """
        Extracts environment configurations from tox.ini files.
        """
        config = configparser.ConfigParser()
        config.read_string(file_content)
        envs = {}
        for section in config.sections():
            if section.startswith('testenv'):
                env_name = section.split(':')[-1]
                envs[env_name] = dict(config[section])
        return envs

    def extract_dockerfile(self, file_content: str) -> List[Dict[str, str]]:
        """
        Extracts commands and environment variables from Dockerfile.
        """
        commands = []
        for match in self.dockerfile_patterns['commands'].finditer(file_content):
            command_type = match.group(1)
            command_value = match.group(2)
            commands.append({'type': command_type, 'value': command_value})
        return commands

    def extract_makefile(self, file_content: str) -> Dict[str, str]:
        """
        Extracts targets and associated commands from Makefile.
        """
        targets = {}
        lines = file_content.splitlines()
        current_target = None
        for line in lines:
            target_match = self.makefile_patterns['target'].match(line)
            if target_match:
                current_target = target_match.group(1)
                targets[current_target] = []
            elif current_target and line.startswith('\t'):
                targets[current_target].append(line.strip())
        return targets

    def extract_yaml_config(self, file_content: str) -> Dict[str, Any]:
        """
        Extracts configurations from YAML files (e.g., CI/CD pipeline configs).
        """
        try:
            config = yaml.safe_load(file_content)
            return config
        except yaml.YAMLError as e:
            logging.error(f"YAML parsing error: {e}")
            return {}

    def extract_pyproject_toml(self, file_content: str) -> Dict[str, Any]:
        """
        Extracts configurations from pyproject.toml files.
        """
        try:
            config = toml.loads(file_content)
            return config
        except toml.TomlDecodeError as e:
            logging.error(f"TOML parsing error: {e}")
            return {}

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Processes the given build/configuration file and extracts relevant information.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            filename = os.path.basename(file_path)
            if filename == 'setup.py':
                return self.extract_setup_py(content)
            elif filename == 'setup.cfg':
                return self.extract_setup_cfg(content)
            elif filename == 'tox.ini':
                return self.extract_tox_ini(content)
            elif filename == 'Dockerfile':
                return self.extract_dockerfile(content)
            elif filename == 'Makefile':
                return self.extract_makefile(content)
            elif filename.endswith(('.yml', '.yaml')):
                return self.extract_yaml_config(content)
            elif filename == 'pyproject.toml':
                return self.extract_pyproject_toml(content)
            else:
                logging.warning(f"Unrecognized file type: {filename}")
                return {}
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")
            return {}

    def _clean_list_string(self, list_string: str) -> List[str]:
        """
        Cleans and splits a string representation of a list into an actual list.
        """
        # Remove quotes and split by comma
        items = re.split(r',\s*', list_string.strip('[]()'))
        return [item.strip('\'"') for item in items if item]

    def extract_pipfile_dependencies(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts dependencies from Pipfile.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            config = toml.loads(content)
            dependencies = []
            for section in ['packages', 'dev-packages']:
                if section in config:
                    for package, version in config[section].items():
                        dependencies.append({'name': package, 'version': version})
            return dependencies
        except Exception as e:
            logging.error(f"Error extracting Pipfile dependencies: {e}")
            return []

    def extract_requirements(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts dependencies from requirements.txt.
        """
        dependencies = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '==' in line:
                        name, version = line.split('==')
                        dependencies.append({'name': name.strip(), 'version': version.strip()})
                    else:
                        dependencies.append({'name': line.strip(), 'version': None})
            return dependencies
        except Exception as e:
            logging.error(f"Error extracting requirements.txt dependencies: {e}")
            return []

    def extract_setup_dependencies(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts dependencies from setup.py.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            metadata = self.extract_setup_py(content)
            dependencies = []
            if 'install_requires' in metadata:
                for dep in metadata['install_requires']:
                    if '==' in dep:
                        name, version = dep.split('==')
                        dependencies.append({'name': name.strip(), 'version': version.strip()})
                    else:
                        dependencies.append({'name': dep.strip(), 'version': None})
            return dependencies
        except Exception as e:
            logging.error(f"Error extracting setup.py dependencies: {e}")
            return []

    def extract_pyproject_dependencies(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts dependencies from pyproject.toml (e.g., Poetry).
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            config = toml.loads(content)
            dependencies = []
            if 'tool' in config and 'poetry' in config['tool']:
                poetry_config = config['tool']['poetry']
                if 'dependencies' in poetry_config:
                    for package, version in poetry_config['dependencies'].items():
                        if package != 'python':
                            dependencies.append({'name': package, 'version': version})
                if 'dev-dependencies' in poetry_config:
                    for package, version in poetry_config['dev-dependencies'].items():
                        dependencies.append({'name': package, 'version': version})
            return dependencies
        except Exception as e:
            logging.error(f"Error extracting pyproject.toml dependencies: {e}")
            return []

    def get_build_tool(self):
        """
        Returns the build tool used by the project based on the configuration files.
        The method looks at setup.py, Pipfile, pyproject.toml, etc.
        """
        if os.path.exists('pyproject.toml'):
            return 'poetry'
        elif os.path.exists('Pipfile'):
            return 'pipenv'
        elif os.path.exists('setup.py'):
            return 'setuptools'
        else:
            return 'unknown'  # If no build tool is found
