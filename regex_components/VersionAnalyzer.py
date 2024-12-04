# VersionAnalyzer.py

import re
from typing import Dict, Any, List, Optional
import os


class VersionAnalyzer:
    def __init__(self, directory: str):
        """Initialize the VersionAnalyzer with the directory to analyze."""
        self.directory = directory

    def extract_version_constraints(self, content: str) -> Dict[str, Any]:
        """
        Extracts version constraints from the given content.
        Returns a dictionary with keys as version types and values as constraints.
        """
        version_info = {}

        # Pattern to find version constraints like '>=3.6', '==2.7'
        version_pattern = re.compile(r'(>=|<=|==|!=|>|<)\s*(\d+\.\d+(?:\.\d+)?)')
        matches = version_pattern.findall(content)
        if matches:
            version_constraints = []
            for operator, version in matches:
                version_constraints.append(f"{operator}{version}")
            version_info['python_version_constraints'] = version_constraints

        # Find Requires-Python in setup.cfg or similar files
        requires_python_pattern = re.compile(r'Requires-Python\s*[:=]\s*([^\n]+)')
        requires_python_match = requires_python_pattern.findall(content)
        if requires_python_match:
            version_info['requires_python'] = [v.strip() for v in requires_python_match]

        # Find deprecation decorators like '@deprecated' or '@deprecated(reason)'
        deprecated_pattern = re.compile(r'@deprecated(?:\((.*?)\))?')
        deprecated_matches = deprecated_pattern.findall(content)
        if deprecated_matches:
            version_info['deprecated'] = [dm.strip() for dm in deprecated_matches if dm]

        # Find version constraints in comments (e.g., '# Requires Python >=3.6')
        comment_version_pattern = re.compile(r'#.*?(Python\s*(\d+\.\d+(?:\.\d+)?))')
        comment_version_matches = comment_version_pattern.findall(content)
        if comment_version_matches:
            comment_versions = [match[0] for match in comment_version_matches]
            version_info['comment_versions'] = comment_versions

        # Find deprecation warnings using warnings.warn with DeprecationWarning
        deprecation_warning_pattern = re.compile(r'warnings\.warn\([\'"]([^\'"]+)[\'"].*DeprecationWarning')
        deprecation_warnings = deprecation_warning_pattern.findall(content)
        if deprecation_warnings:
            version_info['deprecation_warnings'] = deprecation_warnings

        return version_info

    def extract_python_version(self) -> Optional[str]:
        """
        Extracts the Python version compatibility from the codebase.
        Looks into common configuration files.
        """
        python_version = None

        # Look for pyproject.toml, setup.cfg, setup.py, or Pipfile
        config_files = ['pyproject.toml', 'setup.cfg', 'setup.py', 'Pipfile']
        for config_file in config_files:
            file_path = os.path.join(self.directory, config_file)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Try to find python_requires in setup.py
                if config_file == 'setup.py':
                    python_requires_pattern = re.compile(r'python_requires\s*=\s*[\'"]([^\'"]+)[\'"]')
                    match = python_requires_pattern.search(content)
                    if match:
                        python_version = match.group(1).strip()
                        return python_version

                # Try to find Requires-Python in setup.cfg
                if config_file == 'setup.cfg':
                    requires_python_pattern = re.compile(r'Requires-Python\s*=\s*([^\n]+)')
                    match = requires_python_pattern.search(content)
                    if match:
                        python_version = match.group(1).strip()
                        return python_version

                # Try to find requires-python in pyproject.toml
                if config_file == 'pyproject.toml':
                    requires_python_pattern = re.compile(r'requires-python\s*=\s*[\'"]([^\'"]+)[\'"]')
                    match = requires_python_pattern.search(content)
                    if match:
                        python_version = match.group(1).strip()
                        return python_version

                # Try to find python_version in Pipfile
                if config_file == 'Pipfile':
                    python_version_pattern = re.compile(r'python_version\s*=\s*[\'"]([^\'"]+)[\'"]')
                    match = python_version_pattern.search(content)
                    if match:
                        python_version = match.group(1).strip()
                        return python_version

        return python_version
