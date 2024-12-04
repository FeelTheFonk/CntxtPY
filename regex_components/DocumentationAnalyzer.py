# regex_components/DocumentationAnalyzer.py

import re
from typing import List, Optional


class Section:
    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content


class DocumentationInfo:
    def __init__(self, sections: List[Section]):
        self.sections = sections


class DocumentationAnalyzer:
    def __init__(self):
        # Regex patterns for Markdown and reStructuredText headings
        self.md_heading_pattern = re.compile(r'^(#{1,6})\s+(.*)')
        self.rst_heading_pattern = re.compile(
            r'^(.*)\n([=~\-`:\'^".#*]{2,})$', re.MULTILINE
        )
        # Initialize variables to store total lines and total sections
        self.total_lines = 0
        self.total_sections = 0

    def analyze_documentation(self, file_path: str) -> Optional[DocumentationInfo]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if file_path.endswith('.md'):
                sections = self._parse_markdown(content)
            elif file_path.endswith('.rst'):
                sections = self._parse_restructuredtext(content)
            else:
                # Unsupported file type
                return None

            # Update total lines and total sections
            self.total_lines += len(content.splitlines())
            self.total_sections += len(sections)

            return DocumentationInfo(sections=sections)

        except Exception as e:
            # Handle exception if needed
            return None

    def _parse_markdown(self, content: str) -> List[Section]:
        sections = []
        lines = content.split('\n')
        current_section_title = None
        current_section_content = []

        for line in lines:
            heading_match = self.md_heading_pattern.match(line)
            if heading_match:
                # Save the previous section
                if current_section_title is not None:
                    sections.append(
                        Section(
                            title=current_section_title,
                            content='\n'.join(current_section_content).strip(),
                        )
                    )
                    current_section_content = []

                current_section_title = heading_match.group(2).strip()
            else:
                if current_section_title:
                    current_section_content.append(line)

        # Save the last section
        if current_section_title:
            sections.append(
                Section(
                    title=current_section_title,
                    content='\n'.join(current_section_content).strip(),
                )
            )

        return sections

    def _parse_restructuredtext(self, content: str) -> List[Section]:
        sections = []
        lines = content.split('\n')
        idx = 0
        total_lines = len(lines)

        while idx < total_lines:
            line = lines[idx]
            if idx + 1 < total_lines:
                next_line = lines[idx + 1]
                heading_match = self.rst_heading_pattern.match(line + '\n' + next_line)
                if heading_match:
                    title = heading_match.group(1).strip()
                    underline = heading_match.group(2).strip()
                    idx += 2  # Skip the heading and underline
                    section_content = []

                    while idx < total_lines:
                        if idx + 1 < total_lines and self.rst_heading_pattern.match(
                            lines[idx] + '\n' + lines[idx + 1]
                        ):
                            break
                        section_content.append(lines[idx])
                        idx += 1

                    sections.append(
                        Section(
                            title=title, content='\n'.join(section_content).strip()
                        )
                    )
                else:
                    idx += 1
            else:
                idx += 1

        return sections

    def get_coverage_threshold(self) -> float:
        """
        Calculate the coverage threshold for the documentation based on the number of sections
        versus the total number of lines in the document.

        :return: A float value representing the percentage of documentation coverage.
        """
        # Return the coverage percentage (sections vs total lines)
        if self.total_lines == 0:
            return 0.0  # Avoid division by zero
        return (self.total_sections / self.total_lines) * 100
