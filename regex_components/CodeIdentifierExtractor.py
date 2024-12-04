import re
import ast
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass
import logging

@dataclass
class Parameter:
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None

@dataclass
class FunctionInfo:
    name: str
    parameters: List[Parameter]
    return_type: Optional[str]
    decorators: List[str]
    is_async: bool = False
    is_generator: bool = False
    docstring: Optional[str] = None

@dataclass
class ClassInfo:
    name: str
    bases: List[str]
    decorators: List[str]
    methods: List[FunctionInfo]
    docstring: Optional[str] = None

class CodeIdentifierExtractor:
    def __init__(self):
        self.class_pattern = re.compile(r'class\s+(\w+)\s*(?:\((.*?)\))?:')
        self.function_pattern = re.compile(r'(?:async\s+)?def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*([^:]+))?:')
        self.decorator_pattern = re.compile(r'@(\w+(?:\.\w+)*(?:\(.*?\))?)')
        self.variable_pattern = re.compile(r'(\w+)\s*(?::\s*([^=]+))?\s*=\s*([^#\n]+)')
        self.constant_pattern = re.compile(r'([A-Z_][A-Z0-9_]*)\s*=\s*([^#\n]+)')
        
    def extract_classes(self, content: str) -> List[ClassInfo]:
        """Extract class definitions and their methods."""
        classes = []
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Collect decorators
            decorators = []
            while line.startswith('@'):
                decorator_match = self.decorator_pattern.match(line)
                if decorator_match:
                    decorators.append(decorator_match.group(1))
                i += 1
                if i >= len(lines):
                    break
                line = lines[i].strip()
            
            # Match class definition
            class_match = self.class_pattern.match(line)
            if class_match:
                class_name = class_match.group(1)
                bases = []
                if class_match.group(2):
                    bases = [b.strip() for b in class_match.group(2).split(',')]
                
                # Extract class methods
                methods = []
                i += 1
                while i < len(lines) and (not lines[i].strip() or lines[i].startswith(' ') or lines[i].startswith('\t')):
                    method_lines = []
                    while i < len(lines) and (not lines[i].strip() or lines[i].startswith(' ') or lines[i].startswith('\t')):
                        method_lines.append(lines[i])
                        i += 1
                    if method_lines:
                        method_content = '\n'.join(method_lines)
                        methods.extend(self._extract_methods(method_content))
                
                classes.append(ClassInfo(
                    name=class_name,
                    bases=bases,
                    decorators=decorators,
                    methods=methods
                ))
            i += 1
        return classes

    def _extract_methods(self, content: str) -> List[FunctionInfo]:
        """Extract method definitions from class content."""
        methods = []
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Collect decorators
            decorators = []
            while line.startswith('@'):
                decorator_match = self.decorator_pattern.match(line)
                if decorator_match:
                    decorators.append(decorator_match.group(1))
                i += 1
                if i >= len(lines):
                    break
                line = lines[i].strip()
            
            # Match function definition
            func_match = self.function_pattern.match(line)
            if func_match:
                is_async = line.startswith('async')
                name = func_match.group(1)
                params_str = func_match.group(2)
                return_type = func_match.group(3)
                
                # Parse parameters
                parameters = self._parse_parameters(params_str)
                
                methods.append(FunctionInfo(
                    name=name,
                    parameters=parameters,
                    return_type=return_type.strip() if return_type else None,
                    decorators=decorators,
                    is_async=is_async
                ))
            i += 1
        return methods

    def extract_functions(self, content: str) -> List[FunctionInfo]:
        """Extract function definitions."""
        functions = []
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Collect decorators
            decorators = []
            while line.startswith('@'):
                decorator_match = self.decorator_pattern.match(line)
                if decorator_match:
                    decorators.append(decorator_match.group(1))
                i += 1
                if i >= len(lines):
                    break
                line = lines[i].strip()
            
            # Match function definition
            func_match = self.function_pattern.match(line)
            if func_match and not line.startswith(' ') and not line.startswith('\t'):
                is_async = line.startswith('async')
                name = func_match.group(1)
                params_str = func_match.group(2)
                return_type = func_match.group(3)
                
                # Parse parameters
                parameters = self._parse_parameters(params_str)
                
                functions.append(FunctionInfo(
                    name=name,
                    parameters=parameters,
                    return_type=return_type.strip() if return_type else None,
                    decorators=decorators,
                    is_async=is_async
                ))
            i += 1
        return functions

    def _parse_parameters(self, params_str: str) -> List[Parameter]:
        """Parse function parameters with their type hints and default values."""
        parameters = []
        if not params_str.strip():
            return parameters
            
        # Handle nested parentheses in default values
        depth = 0
        current = []
        params = []
        
        for char in params_str:
            if char == '(' or char == '[' or char == '{':
                depth += 1
            elif char == ')' or char == ']' or char == '}':
                depth -= 1
            elif char == ',' and depth == 0:
                params.append(''.join(current).strip())
                current = []
                continue
            current.append(char)
        
        if current:
            params.append(''.join(current).strip())
        
        for param in params:
            param = param.strip()
            if not param:
                continue
                
            # Handle type hints and default values
            parts = param.split(':')
            name = parts[0].strip()
            type_hint = None
            default_value = None
            
            if len(parts) > 1:
                # Handle default values in type-hinted parameters
                type_parts = parts[1].split('=')
                type_hint = type_parts[0].strip()
                if len(type_parts) > 1:
                    default_value = type_parts[1].strip()
            else:
                # Handle default values in non-type-hinted parameters
                if '=' in name:
                    name, default_value = map(str.strip, name.split('=', 1))
            
            parameters.append(Parameter(
                name=name,
                type_hint=type_hint,
                default_value=default_value
            ))
            
        return parameters

    def extract_variables(self, content: str) -> List[Dict[str, Any]]:
        """Extract variable definitions with their type hints and values."""
        variables = []
        
        # First pass: collect all variable assignments
        matches = list(self.variable_pattern.finditer(content))
        matches.extend(self.constant_pattern.finditer(content))
        
        for match in matches:
            if match.re == self.variable_pattern:
                name, type_hint, value = match.groups()
                is_constant = name.isupper()
            else:  # constant pattern
                name, value = match.groups()
                type_hint = None
                is_constant = True
            
            # Skip if it's inside a function/class definition
            line_start = content.rfind('\n', 0, match.start()) + 1
            line = content[line_start:match.start()].strip()
            if line and (line.startswith('def ') or line.startswith('class ')):
                continue
            
            variables.append({
                'name': name,
                'type_hint': type_hint.strip() if type_hint else None,
                'value': value.strip(),
                'is_constant': is_constant
            })
            
        return variables

    def get_main_module(self) -> Optional[str]:
        """Identify the main module name in the codebase."""
        # This is a placeholder - in a real implementation, you would
        # look for patterns like if __name__ == '__main__' or
        # identify the entry point from setup.py/pyproject.toml
        return None
