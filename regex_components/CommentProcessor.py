# regex_components/CommentProcessor.py

import re
from typing import List, Optional
from enum import Enum, auto


class CommentType(Enum):
    INLINE = auto()
    DOCSTRING = auto()
    TODO = auto()
    FIXME = auto()


class CommentInfo:
    def __init__(
        self,
        content: str,
        line_number: int,
        comment_type: CommentType,
        associated_element: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        self.content = content
        self.line_number = line_number
        self.type = comment_type
        self.associated_element = associated_element  # e.g., function or class name
        self.tags = tags or []


class CommentProcessor:
    def __init__(self):
        # Precompile regex patterns
        self.inline_comment_pattern = re.compile(r'#.*')
        self.todo_fixme_pattern = re.compile(r'#.*\b(TODO|FIXME)\b.*', re.IGNORECASE)
        self.docstring_pattern = re.compile(
            r'^[ \t]*("""|\'\'\')(?:.*?)(\1)', re.DOTALL | re.MULTILINE
        )
        self.def_class_pattern = re.compile(r'^[ \t]*(def|class)\s+(\w+)\s*[\(:]?')

    def extract_comments(self, content: str) -> List[CommentInfo]:
        comments = []
        lines = content.split('\n')
        in_docstring = False
        docstring_delimiter = ''
        docstring_start_line = 0
        docstring_content = ''
        associated_element = None

        for idx, line in enumerate(lines):
            line_number = idx + 1
            stripped_line = line.strip()

            # Check for docstring start
            if not in_docstring:
                docstring_match = re.match(
                    r'^[ \t]*("""|\'\'\')', line
                )
                if docstring_match:
                    in_docstring = True
                    docstring_delimiter = docstring_match.group(1)
                    docstring_start_line = line_number
                    docstring_content = line
                    # Check for associated element (function or class)
                    if idx > 0:
                        prev_line = lines[idx - 1]
                        element_match = self.def_class_pattern.match(prev_line)
                        if element_match:
                            associated_element = element_match.group(2)
                    continue
            else:
                docstring_content += '\n' + line
                if docstring_delimiter in stripped_line:
                    in_docstring = False
                    comment = CommentInfo(
                        content=docstring_content.strip(),
                        line_number=docstring_start_line,
                        comment_type=CommentType.DOCSTRING,
                        associated_element=associated_element,
                    )
                    comments.append(comment)
                    docstring_content = ''
                    docstring_delimiter = ''
                    associated_element = None
                continue

            # Check for inline comments
            comment_match = self.inline_comment_pattern.search(line)
            if comment_match:
                comment_text = comment_match.group().strip()
                tags = []
                comment_type = CommentType.INLINE

                if self.todo_fixme_pattern.search(line):
                    if 'TODO' in comment_text.upper():
                        comment_type = CommentType.TODO
                        tags.append('TODO')
                    elif 'FIXME' in comment_text.upper():
                        comment_type = CommentType.FIXME
                        tags.append('FIXME')

                comment = CommentInfo(
                    content=comment_text,
                    line_number=line_number,
                    comment_type=comment_type,
                    associated_element=None,
                    tags=tags,
                )
                comments.append(comment)

        return comments
