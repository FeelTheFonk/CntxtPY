# LoggingAnalyzer.py
import re
from typing import List, Dict, Any
import ast
import logging

class LoggingAnalyzer:
    """
    Identifies logging statements in code, maps logging levels,
    and extracts log message patterns and formats.
    """

    def __init__(self):
        self.logging_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        logging.basicConfig(level=logging.INFO)

    def extract_logs(self, file_content: str) -> List[Dict[str, Any]]:
        """
        Extracts logging statements from the provided Python code.
        """
        logs = []
        try:
            tree = ast.parse(file_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Attribute):
                        if isinstance(func.value, ast.Name) and func.value.id == 'logging':
                            if func.attr.upper() in self.logging_levels:
                                log_entry = {
                                    'level': func.attr.upper(),
                                    'message': self._extract_message(node),
                                    'line_number': node.lineno,
                                    'module': self._get_module_name(node),
                                }
                                logs.append(log_entry)
        except Exception as e:
            logging.error(f"Error parsing code for logging statements: {e}")
        return logs

    def _extract_message(self, node: ast.Call) -> str:
        """
        Extracts the message from a logging call.
        """
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Str):
                return first_arg.s
            elif isinstance(first_arg, ast.Constant):  # For Python 3.8+
                return first_arg.value
            else:
                return ast.unparse(first_arg) if hasattr(ast, 'unparse') else '<complex expression>'
        return ''

    def _get_module_name(self, node: ast.AST) -> str:
        """
        Attempts to retrieve the module name where the logging call is made.
        """
        while node:
            if isinstance(node, ast.Module):
                return getattr(node, 'name', '<unknown>')
            node = getattr(node, 'parent', None)
        return '<unknown>'

    def analyze_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Analyzes a Python file for logging statements.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.extract_logs(content)
        except Exception as e:
            logging.error(f"Error analyzing file {file_path} for logs: {e}")
            return []

    def extract_logs_regex(self, file_content: str) -> List[Dict[str, Any]]:
        """
        Alternative method using regex to extract logging statements.
        """
        pattern = re.compile(r'logging\.(debug|info|warning|error|critical)\s*\(\s*(.*?)\s*\)', re.DOTALL)
        logs = []
        for match in pattern.finditer(file_content):
            level = match.group(1).upper()
            message = match.group(2)
            logs.append({
                'level': level,
                'message': message.strip('"\''),
                'line_number': self._get_line_number(file_content, match.start()),
                'module': '<unknown>',
            })
        return logs

    def _get_line_number(self, content: str, index: int) -> int:
        """
        Calculates the line number in the content string for a given index.
        """
        return content.count('\n', 0, index) + 1
