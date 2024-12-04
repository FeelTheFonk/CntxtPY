import os
import re
import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import toml
import json

@dataclass
class Dependency:
    name: str
    version: Optional[str] = None
    extras: List[str] = None
    
    def __post_init__(self):
        if self.extras is None:
            self.extras = []

class DependencyMapper:
    def __init__(self):
        self.version_pattern = re.compile(r'^([^=<>!~]+)(?:[=<>!~]=?|@)(.+)$')
        self.import_pattern = re.compile(r'^(?:from\s+(\S+)\s+)?import\s+(.+)$')
        self.extras_pattern = re.compile(r'\[(.*?)\]')
        
    def extract_requirements(self, file_path: str) -> List[Dependency]:
        """Extract dependencies from requirements.txt."""
        dependencies = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-r'):
                        # Handle extras
                        extras_match = self.extras_pattern.search(line)
                        extras = []
                        if extras_match:
                            extras = [e.strip() for e in extras_match.group(1).split(',')]
                            line = line[:extras_match.start()].strip()
                            
                        # Handle version constraints
                        match = self.version_pattern.match(line)
                        if match:
                            name, version = match.groups()
                            dependencies.append(Dependency(name.strip(), version.strip(), extras))
                        else:
                            dependencies.append(Dependency(line, extras=extras))
                            
        except Exception as e:
            logging.error(f"Error parsing requirements.txt: {str(e)}")
            
        return dependencies
        
    def extract_pipfile_dependencies(self, file_path: str) -> List[Dependency]:
        """Extract dependencies from Pipfile."""
        dependencies = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = toml.load(f)
                
            for section in ['packages', 'dev-packages']:
                if section in content:
                    for name, constraint in content[section].items():
                        if isinstance(constraint, str):
                            dependencies.append(Dependency(name, constraint))
                        elif isinstance(constraint, dict):
                            version = constraint.get('version', '')
                            extras = constraint.get('extras', [])
                            dependencies.append(Dependency(name, version, extras))
                            
        except Exception as e:
            logging.error(f"Error parsing Pipfile: {str(e)}")
            
        return dependencies
        
    def extract_setup_dependencies(self, file_path: str) -> List[Dependency]:
        """Extract dependencies from setup.py."""
        dependencies = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for install_requires list
            install_requires = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if install_requires:
                deps = install_requires.group(1).split(',')
                for dep in deps:
                    dep = dep.strip().strip("'").strip('"')
                    if dep:
                        match = self.version_pattern.match(dep)
                        if match:
                            name, version = match.groups()
                            dependencies.append(Dependency(name.strip(), version.strip()))
                        else:
                            dependencies.append(Dependency(dep))
                            
            # Look for extras_require dict
            extras_require = re.search(r'extras_require\s*=\s*{(.*?)}', content, re.DOTALL)
            if extras_require:
                extras_content = extras_require.group(1)
                extras_matches = re.finditer(r"'([^']+)'\s*:\s*\[(.*?)\]", extras_content, re.DOTALL)
                for match in extras_matches:
                    extra_name = match.group(1)
                    extra_deps = match.group(2).split(',')
                    for dep in extra_deps:
                        dep = dep.strip().strip("'").strip('"')
                        if dep:
                            match = self.version_pattern.match(dep)
                            if match:
                                name, version = match.groups()
                                dependencies.append(Dependency(name.strip(), version.strip(), [extra_name]))
                            else:
                                dependencies.append(Dependency(dep, extras=[extra_name]))
                                
        except Exception as e:
            logging.error(f"Error parsing setup.py: {str(e)}")
            
        return dependencies
        
    def extract_pyproject_dependencies(self, file_path: str) -> List[Dependency]:
        """Extract dependencies from pyproject.toml."""
        dependencies = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = toml.load(f)
                
            # Handle poetry dependencies
            if 'tool' in content and 'poetry' in content['tool']:
                poetry = content['tool']['poetry']
                
                # Main dependencies
                if 'dependencies' in poetry:
                    for name, constraint in poetry['dependencies'].items():
                        if isinstance(constraint, str):
                            dependencies.append(Dependency(name, constraint))
                        elif isinstance(constraint, dict):
                            version = constraint.get('version', '')
                            extras = constraint.get('extras', [])
                            dependencies.append(Dependency(name, version, extras))
                            
                # Dev dependencies
                if 'dev-dependencies' in poetry:
                    for name, constraint in poetry['dev-dependencies'].items():
                        if isinstance(constraint, str):
                            dependencies.append(Dependency(name, constraint, ['dev']))
                        elif isinstance(constraint, dict):
                            version = constraint.get('version', '')
                            extras = constraint.get('extras', []) + ['dev']
                            dependencies.append(Dependency(name, version, extras))
                            
        except Exception as e:
            logging.error(f"Error parsing pyproject.toml: {str(e)}")
            
        return dependencies
        
    def extract_imports(self, content: str) -> Set[str]:
        """Extract import statements from Python code."""
        imports = set()
        for line in content.splitlines():
            line = line.strip()
            match = self.import_pattern.match(line)
            if match:
                module_from, imported = match.groups()
                if module_from:
                    imports.add(module_from)
                imports.update(imp.strip() for imp in imported.split(','))
        return imports
        
    def map_import_hierarchy(self, directory: str) -> Dict:
        """Map import hierarchy within a codebase."""
        hierarchy = {}
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, directory)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        imports = self.extract_imports(content)
                        hierarchy[rel_path] = list(imports)
                    except Exception as e:
                        logging.error(f"Error processing {file_path}: {str(e)}")
                        
        return hierarchy
