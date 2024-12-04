import os
import re
from enum import Enum
from typing import Dict, List, Optional, Set
import logging
import yaml
from pathlib import Path

class ConfigType(Enum):
    ENV = "environment"
    INI = "ini"
    CFG = "config"
    YAML = "yaml"
    UNKNOWN = "unknown"

class ConfigInfo:
    def __init__(self, config_type: ConfigType, data: Dict):
        self.config_type = config_type
        self.data = data

class ConfigFileParser:
    def __init__(self):
        self.env_pattern = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')
        self.ini_section_pattern = re.compile(r'^\[([^\]]+)\]$')
        self.ini_value_pattern = re.compile(r'^([^=\s]+)\s*=\s*(.*)$')
        self.import_pattern = re.compile(r'^(?:from\s+(\S+)\s+)?import\s+(.+)$')
        
    def parse_config_file(self, file_path: str) -> Optional[ConfigInfo]:
        """Parse configuration files and return structured data."""
        try:
            config_type = self._determine_config_type(file_path)
            if config_type == ConfigType.UNKNOWN:
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if config_type == ConfigType.ENV:
                data = self._parse_env(content)
            elif config_type in (ConfigType.INI, ConfigType.CFG):
                data = self._parse_ini(content)
            elif config_type == ConfigType.YAML:
                data = self._parse_yaml(content)
            else:
                return None
                
            return ConfigInfo(config_type, data)
            
        except Exception as e:
            logging.error(f"Error parsing config file {file_path}: {str(e)}")
            return None
            
    def _determine_config_type(self, file_path: str) -> ConfigType:
        """Determine the type of configuration file based on extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.env':
            return ConfigType.ENV
        elif ext == '.ini':
            return ConfigType.INI
        elif ext == '.cfg':
            return ConfigType.CFG
        elif ext in ('.yaml', '.yml'):
            return ConfigType.YAML
        return ConfigType.UNKNOWN
        
    def _parse_env(self, content: str) -> Dict:
        """Parse .env file content."""
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                match = self.env_pattern.match(line)
                if match:
                    key, value = match.groups()
                    result[key] = value.strip("'").strip('"')
        return result
        
    def _parse_ini(self, content: str) -> Dict:
        """Parse .ini/.cfg file content."""
        result = {}
        current_section = None
        
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            section_match = self.ini_section_pattern.match(line)
            if section_match:
                current_section = section_match.group(1)
                result[current_section] = {}
                continue
                
            value_match = self.ini_value_pattern.match(line)
            if value_match:
                key, value = value_match.groups()
                if current_section:
                    result[current_section][key] = value
                else:
                    result[key] = value
                    
        return result
        
    def _parse_yaml(self, content: str) -> Dict:
        """Parse YAML file content."""
        try:
            return yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML content: {str(e)}")
            return {}
            
    def map_directory_structure(self, directory: str) -> Dict:
        """Map the directory structure and identify relationships."""
        structure = {}
        imports = set()
        
        for root, dirs, files in os.walk(directory):
            current_dir = structure
            parts = os.path.relpath(root, directory).split(os.sep)
            
            for part in parts:
                if part == '.':
                    continue
                current_dir.setdefault(part, {})
                current_dir = current_dir[part]
                
            for file in files:
                if file.endswith('.py'):
                    file_imports = self._extract_imports(os.path.join(root, file))
                    imports.update(file_imports)
                    current_dir[file] = list(file_imports)
                    
        return {
            'structure': structure,
            'imports': list(imports)
        }
        
    def _extract_imports(self, file_path: str) -> Set[str]:
        """Extract import statements from a Python file."""
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    match = self.import_pattern.match(line)
                    if match:
                        module_from, imported = match.groups()
                        if module_from:
                            imports.add(module_from)
                        imports.update(imp.strip() for imp in imported.split(','))
        except Exception as e:
            logging.error(f"Error extracting imports from {file_path}: {str(e)}")
        return imports
