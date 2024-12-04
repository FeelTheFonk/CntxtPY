# CntxtPY.py - Python codebase analyzer that generates comprehensive knowledge graphs optimized for LLM context windows

import os
import sys
import json
import networkx as nx
from networkx.readwrite import json_graph
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import logging
from datetime import datetime

# Import regex modules
try:
    from regex_components.ConfigFileParser import ConfigFileParser
    from regex_components.DependencyMapper import DependencyMapper
    from regex_components.CodeIdentifierExtractor import CodeIdentifierExtractor, FunctionInfo, Parameter
    from regex_components.CommentProcessor import CommentProcessor
    from regex_components.DocumentationAnalyzer import DocumentationAnalyzer
    from regex_components.BuildConfigExtractor import BuildConfigExtractor
    from regex_components.LoggingAnalyzer import LoggingAnalyzer
    from regex_components.VersionAnalyzer import VersionAnalyzer
    from regex_components.FileTypeProcessor import FileTypeProcessor
    from regex_components.IntegrationMapper import IntegrationMapper
    from regex_components.LocalizationProcessor import LocalizationProcessor
    from regex_components.CommentProcessor import CommentInfo, CommentType
except ImportError as e:
    print(f"Error importing regex components: {str(e)}")
    print("Make sure all component files are in the 'regex_components' directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class PythonCodeKnowledgeGraph:
    def __init__(self, directory: str):
        """Initialize the knowledge graph generator."""
        self.directory = directory
        self.graph = nx.DiGraph()
        self.files_processed = 0
        self.total_files = 0
        self.dirs_processed = 0
        self.analyzed_files = set()
        self.module_map = {}

        # Initialize statistics
        self.stats = {
            'total_classes': 0,
            'total_functions': 0,
            'total_modules': set(),
            'total_imports': 0,
            'total_dependencies': set(),
            'total_annotations': set(),
            'total_logging_statements': 0,
            'files_with_errors': 0,
            'total_comments': 0,
            'total_configs': 0,
            'total_integrations': 0,
            'total_localizations': 0,
            'total_build_scripts': 0,
            'total_version_constraints': 0,
            'total_variables': 0,
            'total_constants': 0
        }

        # Initialize processors and ignored paths
        self._init_processors()
        self._init_ignored_paths()

    def _init_processors(self):
        """Initialize all component processors."""
        try:
            # Pass the directory when initializing the VersionAnalyzer
            self.version_analyzer = VersionAnalyzer(directory=self.directory)
            self.config_parser = ConfigFileParser()
            self.dependency_mapper = DependencyMapper()
            self.code_extractor = CodeIdentifierExtractor()
            self.comment_processor = CommentProcessor()
            self.doc_analyzer = DocumentationAnalyzer()
            self.build_extractor = BuildConfigExtractor()
            self.log_analyzer = LoggingAnalyzer()
            self.file_processor = FileTypeProcessor()
            self.integration_mapper = IntegrationMapper()
            self.localization_processor = LocalizationProcessor()
        except Exception as e:
            logging.error(f"Error initializing processors: {str(e)}")
            raise

    def _init_ignored_paths(self):
        """Initialize sets of ignored directories and files."""
        self.ignored_directories = {
            '__pycache__', '.git', '.idea', '.vscode', '.venv', 'env', 'venv',
            '.mypy_cache', '.pytest_cache', '.eggs', 'build', 'dist', 'node_modules',
            '.tox', '.coverage', '.svn', '.hg'
        }

        self.ignored_files = {
            '.gitignore', '.DS_Store', 'Thumbs.db', '.env', '.env.example'
        }

    def _add_dependency_node(self, build_node: str, dep_info: Dict[str, str]):
        """Add a dependency node to the graph."""
        dep_id = f"{dep_info['name']}=={dep_info.get('version', '')}"
        dep_node = f"Dependency: {dep_id}"
        if not self.graph.has_node(dep_node):
            self.graph.add_node(
                dep_node,
                type="dependency",
                name=dep_info['name'],
                version=dep_info.get('version', ''),
                id=dep_node
            )
            self.stats['total_dependencies'].add(dep_id)
        self.graph.add_edge(build_node, dep_node, relation="DEPENDS_ON")

    def analyze_codebase(self):
        """Analyze the Python codebase and build the knowledge graph."""
        logging.info("Starting codebase analysis...")

        # Count files first
        self._count_files()

        # Process the codebase
        self._process_codebase()

        logging.info(f"Completed analysis of {self.files_processed} files")
        if self.stats['files_with_errors'] > 0:
            logging.warning(f"Encountered errors in {self.stats['files_with_errors']} files")

    def _count_files(self):
        """Count total files to be processed."""
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            if not any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                self.total_files += sum(
                    1 for f in files
                    if f.endswith(".py") and f not in self.ignored_files
                )
                # Include build files
                self.total_files += sum(
                    1 for f in files
                    if f in {"setup.py", "requirements.txt", "Pipfile", "pyproject.toml"} and f not in self.ignored_files
                )
                # Include config files
                self.total_files += sum(
                    1 for f in files
                    if f.endswith((".ini", ".env", ".cfg", ".yaml", ".yml", ".json")) and f not in self.ignored_files
                )
                # Include localization files
                self.total_files += sum(
                    1 for f in files
                    if f.endswith((".po", ".mo")) and f not in self.ignored_files
                )
                # Include README and documentation files
                self.total_files += sum(
                    1 for f in files
                    if f.lower() in {"readme.md", "readme.rst", "api.md", "docs.md"} and f not in self.ignored_files
                )

        logging.info(f"Found {self.total_files} files to process")

    def _process_codebase(self):
        """Process all files in the codebase."""
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            if any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                continue

            rel_path = os.path.relpath(root, self.directory)
            self.dirs_processed += 1
            logging.debug(f"Processing directory [{self.dirs_processed}]: {rel_path}")

            for file in files:
                if file in self.ignored_files:
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.directory)

                if file.endswith(".py"):
                    self._process_python_file(file_path)
                elif file in {"setup.py", "requirements.txt", "Pipfile", "pyproject.toml"}:
                    self._process_build_file(file_path)
                elif file.endswith((".ini", ".env", ".cfg", ".yaml", ".yml", ".json")):
                    self._process_config_file(file_path)
                elif file.endswith((".po", ".mo")):
                    self._process_localization_file(file_path)
                elif file.lower() in {"readme.md", "readme.rst", "api.md", "docs.md"}:
                    self._process_documentation_file(file_path)
                else:
                    self._process_generic_file(file_path)

    def _process_python_file(self, file_path: str):
        """Process a single Python file."""
        if file_path in self.analyzed_files:
            return

        try:
            self.files_processed += 1
            relative_path = os.path.relpath(file_path, self.directory)
            logging.debug(f"Processing file [{self.files_processed}/{self.total_files}]: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Add file node
            file_node = f"File: {relative_path}"
            self.analyzed_files.add(file_path)
            self.graph.add_node(file_node, type="file", path=relative_path, encoding="UTF-8", fileType="SOURCE_CODE")

            # Process file contents
            self._process_file_contents(file_node, content, file_path)

        except Exception as e:
            logging.error(f"Error processing {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_file_contents(self, file_node: str, content: str, file_path: str):
        """Process the contents of a Python file using all analyzers."""
        try:
            # Process imports
            imports = self.dependency_mapper.extract_imports(content)
            for import_name in imports:
                self._add_import_node(file_node, import_name)

            # Process classes
            classes = self.code_extractor.extract_classes(content)
            for class_info in classes:
                class_name = class_info.name
                self._add_class_node(file_node, class_name)

                # Add class annotations (decorators)
                for annotation in class_info.decorators:
                    self._add_annotation_node(file_node, annotation)

                # Process methods within the class
                for method in class_info.methods:
                    self._add_method_node(class_name, method)
                    # Add method annotations (decorators)
                    for annotation in method.decorators:
                        self._add_annotation_node(file_node, annotation)

            # Process functions
            functions = self.code_extractor.extract_functions(content)
            for function_info in functions:
                self._add_function_node(file_node, function_info)
                # Add function annotations (decorators)
                for annotation in function_info.decorators:
                    self._add_annotation_node(file_node, annotation)

            # Process variables and constants
            variables = self.code_extractor.extract_variables(content)
            for variable_info in variables:
                self._add_variable_node(file_node, variable_info)

            # Process comments and documentation
            comments = self.comment_processor.extract_comments(content)
            for comment in comments:
                self._add_comment_node(file_node, comment)

            # Process logging statements
            logging_statements = self.log_analyzer.extract_logs(content)
            for log in logging_statements:
                self._add_log_statement_node(file_node, log)

            # Process integrations
            integrations = self.integration_mapper.extract_integrations(content)
            for integration in integrations:
                self._add_integration_node(file_node, integration)

            # Process version constraints
            version_info = self.version_analyzer.extract_version_constraints(content)
            if version_info:
                self._add_version_info(file_node, version_info)

            # Process localization usage
            localizations = self.localization_processor.extract_localizations(content)
            for localization in localizations:
                self._add_localization_usage_node(file_node, localization)

        except Exception as e:
            logging.error(f"Error in _process_file_contents for {file_node}: {str(e)}")
            raise

    def _add_import_node(self, file_node: str, import_name: str):
        """Add an import node to the graph."""
        import_node = f"Import: {import_name}"
        if not self.graph.has_node(import_node):
            self.graph.add_node(import_node, type="import", name=import_name, id=import_node)
            self.stats['total_imports'] += 1
            logging.debug(f"Import added: {import_name}, Total imports: {self.stats['total_imports']}")
        self.graph.add_edge(file_node, import_node, relation="IMPORTS")
        logging.debug(f"Edge added: {file_node} -> {import_node} with relation IMPORTS")

    def _add_class_node(self, file_node: str, class_name: str):
        """Add a class node to the graph."""
        class_node = f"Class: {class_name}"
        if not self.graph.has_node(class_node):
            self.graph.add_node(class_node, type="class", name=class_name, id=class_node)
            self.stats['total_classes'] += 1
            logging.debug(f"Class node added: {class_node}, Total classes: {self.stats['total_classes']}")
        else:
            logging.debug(f"Class node already exists: {class_node}")

        self.graph.add_edge(file_node, class_node, relation="DEFINES")
        logging.debug(f"Edge added: {file_node} -> {class_node} with relation DEFINES")

    def _add_method_node(self, class_name: str, method_info: FunctionInfo):
        """Add a method node to the graph."""
        method_name = method_info.name
        method_node = f"Method: {method_name}"

        if not self.graph.has_node(method_node):
            # Convert parameters to a serializable format
            parameters = [
                {
                    'name': param.name,
                    'type': param.type_hint,
                    'default': param.default_value
                }
                for param in method_info.parameters
            ]

            self.graph.add_node(
                method_node,
                type="method",
                name=method_name,
                id=method_node,
                return_type=method_info.return_type,
                parameters=parameters,
                decorators=method_info.decorators
            )
            self.stats['total_functions'] += 1
            logging.debug(f"Method node added: {method_node}, Total functions: {self.stats['total_functions']}")
        else:
            logging.debug(f"Method node already exists: {method_node}")

        # Link method to its class
        class_node = f"Class: {class_name}"
        if self.graph.has_node(class_node):
            self.graph.add_edge(class_node, method_node, relation="HAS_METHOD")
            logging.debug(f"Edge added: {class_node} -> {method_node} with relation HAS_METHOD")
        else:
            logging.warning(f"Class node {class_node} does not exist; cannot add method {method_info.name}")

    def _add_function_node(self, file_node: str, function_info: FunctionInfo):
        """Add a function node to the graph."""
        function_name = function_info.name
        function_node = f"Function: {function_name}"

        if not self.graph.has_node(function_node):
            # Convert parameters to a serializable format
            parameters = [
                {
                    'name': param.name,
                    'type': param.type_hint,
                    'default': param.default_value
                }
                for param in function_info.parameters
            ]

            self.graph.add_node(
                function_node,
                type="function",
                name=function_name,
                id=function_node,
                return_type=function_info.return_type,
                parameters=parameters,
                decorators=function_info.decorators
            )
            self.stats['total_functions'] += 1
            logging.debug(f"Function node added: {function_node}, Total functions: {self.stats['total_functions']}")
        else:
            logging.debug(f"Function node already exists: {function_node}")

        # Link function to file
        self.graph.add_edge(file_node, function_node, relation="DEFINES")
        logging.debug(f"Edge added: {file_node} -> {function_node} with relation DEFINES")

    def _add_variable_node(self, file_node: str, variable_info: Dict[str, Any]):
        """Add a variable node to the graph."""
        variable_name = variable_info['name']
        variable_node = f"Variable: {variable_name}"

        if not self.graph.has_node(variable_node):
            self.graph.add_node(
                variable_node,
                type="variable",
                name=variable_name,
                id=variable_node,
                value=variable_info.get('value', None),
                type_hint=variable_info.get('type_hint', None)
            )
            self.stats['total_variables'] += 1
            logging.debug(f"Variable node added: {variable_node}, Total variables: {self.stats['total_variables']}")
        else:
            logging.debug(f"Variable node already exists: {variable_node}")

        # Link variable to file
        self.graph.add_edge(file_node, variable_node, relation="HAS_VARIABLE")
        logging.debug(f"Edge added: {file_node} -> {variable_node} with relation HAS_VARIABLE")

    def _add_annotation_node(self, file_node: str, annotation: str):
        """Add an annotation (decorator) node to the graph."""
        annotation_node = f"Decorator: {annotation}"

        if not self.graph.has_node(annotation_node):
            self.graph.add_node(annotation_node, type="decorator", name=annotation, id=annotation_node)
            if annotation not in self.stats['total_annotations']:
                self.stats['total_annotations'].add(annotation)
                logging.debug(f"Decorator node added: {annotation_node}, Total unique decorators: {len(self.stats['total_annotations'])}")
        else:
            logging.debug(f"Decorator node already exists: {annotation_node}")

        self.graph.add_edge(file_node, annotation_node, relation="DECORATED_WITH")
        logging.debug(f"Edge added: {file_node} -> {annotation_node} with relation DECORATED_WITH")

    def _add_comment_node(self, file_node: str, comment: CommentInfo):
        """Add a comment node to the graph."""
        comment_id = f"Comment: {comment.line_number}_{hash(comment.content)}"
        comment_node = comment_id
        if not self.graph.has_node(comment_node):
            self.graph.add_node(
                comment_node,
                type="comment",
                comment_type=comment.type.value,
                content=comment.content,
                line_number=comment.line_number,
                associated_element=comment.associated_element,
                tags=comment.tags or [],
                id=comment_node
            )
            self.stats['total_comments'] += 1
        self.graph.add_edge(file_node, comment_node, relation="HAS_COMMENT")

    def _add_log_statement_node(self, file_node: str, log_info: Dict[str, Any]):
        """Add a log statement node to the graph."""
        log_id = f"Log: {hash(log_info.get('message', ''))}"
        log_node = log_id
        if not self.graph.has_node(log_node):
            self.graph.add_node(
                log_node,
                type="log_statement",
                level=log_info.get('level', 'INFO'),
                message=log_info.get('message', ''),
                id=log_node
            )
            self.stats['total_logging_statements'] += 1
        self.graph.add_edge(file_node, log_node, relation="USES")

    def _add_integration_node(self, file_node: str, integration: Dict[str, Any]):
        """Add an integration node to the graph."""
        integration_name = integration.get('name', 'unnamed_integration')
        integration_node = f"Integration: {integration_name}"
        if not self.graph.has_node(integration_node):
            self.graph.add_node(
                integration_node,
                type="api_integration",
                name=integration_name,
                url=integration.get('url', ''),
                id=integration_node
            )
            self.stats['total_integrations'] += 1
        self.graph.add_edge(file_node, integration_node, relation="INTEGRATES_WITH")

    def _add_version_info(self, file_node: str, version_info: Dict[str, Any]):
        """Add version information to the graph."""
        for version_type, version_data in version_info.items():
            version_node = f"Version: {version_type}"
            if not self.graph.has_node(version_node):
                self.graph.add_node(
                    version_node,
                    type="version",
                    version_type=version_type,
                    constraints=version_data.get('constraints', ''),
                    id=version_node
                )
                self.stats['total_version_constraints'] += 1
            self.graph.add_edge(file_node, version_node, relation="HAS_VERSION")

    def _add_localization_usage_node(self, file_node: str, localization: Dict[str, Any]):
        """Add a localization usage node to the graph."""
        localization_path = localization.get('path', 'unknown_path')
        locale = localization.get('locale', 'unknown_locale')
        localization_node = f"i18n: {os.path.basename(localization_path)}"
        if not self.graph.has_node(localization_node):
            self.graph.add_node(
                localization_node,
                type="localization",
                path=localization_path,
                locale=locale,
                id=localization_node
            )
            self.stats['total_localizations'] += 1
        self.graph.add_edge(file_node, localization_node, relation="USES")

    def _process_build_file(self, file_path: str):
        """Process build configuration files."""
        try:
            build_type = None
            if file_path.endswith("setup.py") or file_path.endswith("setup.cfg"):
                build_type = "setuptools"
                dependencies = self.dependency_mapper.extract_setup_dependencies(file_path)
            elif file_path.endswith("requirements.txt"):
                build_type = "requirements"
                dependencies = self.dependency_mapper.extract_requirements(file_path)
            elif file_path.endswith("Pipfile"):
                build_type = "pipenv"
                dependencies = self.dependency_mapper.extract_pipfile_dependencies(file_path)
            elif file_path.endswith("pyproject.toml"):
                build_type = "poetry"
                dependencies = self.dependency_mapper.extract_pyproject_dependencies(file_path)
            else:
                dependencies = []

            # Add build script node
            build_node = f"Build: {os.path.relpath(file_path, self.directory)}"
            if not self.graph.has_node(build_node):
                self.graph.add_node(
                    build_node,
                    type="build_script",
                    path=os.path.relpath(file_path, self.directory),
                    build_tool=build_type,
                    id=build_node
                )
                self.stats['total_build_scripts'] += 1

            for dep in dependencies:
                dep_info = {
                    'name': dep.name,
                    'version': dep.version
                }
                self._add_dependency_node(build_node, dep_info)

        except Exception as e:
            logging.error(f"Error processing build file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_config_file(self, file_path: str):
        """Process configuration files."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            config_info = self.config_parser.parse_config_file(file_path)
            if config_info:
                config_node = f"Config: {relative_path}"
                if not self.graph.has_node(config_node):
                    self.graph.add_node(
                        config_node,
                        type="config",
                        path=relative_path,
                        config_type=config_info.config_type.value,
                        id=config_node
                    )
                    self.stats['total_configs'] += 1
                # Link config to file
                file_node = f"File: {relative_path}"
                self.graph.add_edge(file_node, config_node, relation="CONFIGURED_BY")
        except AttributeError as ae:
            logging.error(f"AttributeError processing config file {file_path}: {str(ae)}")
            self.stats['files_with_errors'] += 1
        except Exception as e:
            logging.error(f"Error processing config file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_localization_file(self, file_path: str):
        """Process localization files."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            locale = self.localization_processor.extract_locale(relative_path)
            localization_node = f"i18n: {os.path.basename(relative_path)}"
            if not self.graph.has_node(localization_node):
                self.graph.add_node(
                    localization_node,
                    type="localization",
                    path=relative_path,
                    locale=locale,
                    id=localization_node
                )
                self.stats['total_localizations'] += 1
            # Link localization to file
            file_node = f"File: {relative_path}"
            self.graph.add_edge(file_node, localization_node, relation="CONTAINS")

        except Exception as e:
            logging.error(f"Error processing localization file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_documentation_file(self, file_path: str):
        """Process documentation files like README.md and API docs."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            doc_info = self.doc_analyzer.analyze_documentation(file_path)
            if doc_info:
                doc_node = f"Documentation: {relative_path}"
                if not self.graph.has_node(doc_node):
                    self.graph.add_node(
                        doc_node,
                        type="documentation",
                        path=file_path,
                        sections=[section.title for section in doc_info.sections],
                        id=doc_node
                    )
                project_node = "Project: Main"
                if not self.graph.has_node(project_node):
                    self.graph.add_node(project_node, type="project", name="Main Project", id=project_node)
                self.graph.add_edge(project_node, doc_node, relation="HAS_DOCUMENTATION")

        except Exception as e:
            logging.error(f"Error processing documentation file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_generic_file(self, file_path: str):
        """Process generic files that don't fall into specific categories."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            file_info = self.file_processor.process_file(file_path)
            if file_info:
                file_node = f"File: {relative_path}"
                if not self.graph.has_node(file_node):
                    self.graph.add_node(
                        file_node,
                        type=file_info.type.value,
                        encoding=file_info.encoding or 'UTF-8',
                        fileType=file_info.extension,
                        purpose=file_info.purpose,
                        id=file_node
                    )
        except AttributeError as ae:
            logging.error(f"AttributeError processing generic file {file_path}: {str(ae)}")
            self.stats['files_with_errors'] += 1
        except Exception as e:
            logging.error(f"Error processing generic file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def save_graph(self, output_path: str):
        """Save the knowledge graph to a JSON file."""
        try:
            # Convert graph to JSON format with explicit edges keyword to suppress FutureWarning
            data = json_graph.node_link_data(self.graph, edges="links")

            # Prepare metadata
            metadata = {
                "stats": {
                    "total_files": self.total_files,
                    "files_processed": self.files_processed,
                    "files_with_errors": self.stats['files_with_errors'],
                    "total_classes": self.stats['total_classes'],
                    "total_functions": self.stats['total_functions'],
                    "total_variables": self.stats['total_variables'],
                    "total_modules": len(self.stats['total_modules']),
                    "total_imports": self.stats['total_imports'],
                    "total_dependencies": len(self.stats['total_dependencies']),
                    "total_annotations": len(self.stats['total_annotations']),
                    "total_logging_statements": self.stats['total_logging_statements'],
                    "total_comments": self.stats['total_comments'],
                    "total_configs": self.stats['total_configs'],
                    "total_integrations": self.stats['total_integrations'],
                    "total_localizations": self.stats['total_localizations'],
                    "total_build_scripts": self.stats['total_build_scripts'],
                    "total_version_constraints": self.stats['total_version_constraints']
                },
                "build_info": {
                    "python_version": self.version_analyzer.extract_python_version(),
                    "build_tool": self.build_extractor.get_build_tool(),
                    "main_module": self.code_extractor.get_main_module()
                },
                "documentation": {
                    "readme_path": "README.md",
                    "api_docs": "docs/api.md",
                    "coverage_threshold": self.doc_analyzer.get_coverage_threshold()
                },
                "analysis_timestamp": datetime.now().isoformat(),
                "analyzed_directory": self.directory,
                "modules": list(self.stats['total_modules']),
                "dependencies": list(self.stats['total_dependencies'])
            }

            # Combine data and metadata
            output_data = {
                "graph": {
                    "directed": data['directed'],
                    "multigraph": data['multigraph'],
                    "nodes": data['nodes'],
                    "links": data['links']
                },
                "metadata": metadata
            }

            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)

            # Log statistics
            logging.info(f"\nAnalysis Statistics:")
            for key, value in metadata['stats'].items():
                logging.info(f"{key}: {value}")

            logging.info(f"\nKnowledge graph saved to {output_path}")

        except AttributeError as ae:
            logging.error(f"AttributeError saving graph: {str(ae)}")
        except Exception as e:
            logging.error(f"Error saving graph: {str(e)}")

    def generate_example_output_structure(self):
        """Generate an example structure for reference."""
        example_output = {
            "graph": {
                "directed": True,
                "multigraph": False,
                "nodes": [
                    # Nodes will be populated here
                ],
                "links": [
                    # Links will be populated here
                ]
            },
            "metadata": {
                "stats": {
                    "total_files": 0,
                    "files_processed": 0,
                    "files_with_errors": 0,
                    "total_classes": 0,
                    "total_functions": 0,
                    "total_variables": 0,
                    "total_modules": 0,
                    "total_imports": 0,
                    "total_dependencies": 0,
                    "total_annotations": 0,
                    "total_logging_statements": 0,
                    "total_comments": 0,
                    "total_configs": 0,
                    "total_integrations": 0,
                    "total_localizations": 0,
                    "total_build_scripts": 0,
                    "total_version_constraints": 0
                },
                "build_info": {
                    "python_version": "",
                    "build_tool": "",
                    "main_module": ""
                },
                "documentation": {
                    "readme_path": "",
                    "api_docs": "",
                    "coverage_threshold": 0
                },
                "analysis_timestamp": "",
                "analyzed_directory": "",
                "modules": [],
                "dependencies": []
            }
        }
        return example_output

    def visualize_graph(self):
        """Visualize the knowledge graph."""
        try:
            import matplotlib.pyplot as plt

            # Create color map for different node types
            color_map = {
                "file": "#ADD8E6",           # Light blue
                "module": "#90EE90",         # Light green
                "class": "#FFE5B4",          # Peach
                "function": "#FFD700",       # Gold
                "variable": "#FFB6C1",       # Light pink
                "method": "#E6E6FA",         # Lavender
                "import": "#DDA0DD",         # Plum
                "dependency": "#8A2BE2",     # Blue Violet
                "decorator": "#FFA07A",      # Light Salmon
                "comment": "#C0C0C0",        # Silver
                "log_statement": "#808080",  # Gray
                "api_integration": "#FFDAB9",# Peach Puff
                "version": "#00CED1",        # Dark Turquoise
                "localization": "#40E0D0",   # Turquoise
                "build_script": "#B0E0E6",   # Powder Blue
                "documentation": "#F5DEB3",  # Wheat
                "project": "#98FB98",        # Pale Green
                "config": "#FFE4B5",         # Moccasin
            }

            # Set node colors
            node_colors = [
                color_map.get(self.graph.nodes[node].get("type", "file"), "lightgray")
                for node in self.graph.nodes()
            ]

            # Create figure and axis explicitly
            fig, ax = plt.subplots(figsize=(20, 15))

            # Calculate layout
            pos = nx.spring_layout(self.graph, k=1.5, iterations=50)

            # Draw the graph
            nx.draw(
                self.graph,
                pos,
                ax=ax,
                with_labels=True,
                node_color=node_colors,
                node_size=2000,
                font_size=8,
                font_weight="bold",
                arrows=True,
                edge_color="gray",
                arrowsize=20,
            )

            # Add legend
            legend_elements = [
                plt.Line2D(
                    [0], [0],
                    marker='o',
                    color='w',
                    markerfacecolor=color,
                    label=node_type.capitalize(),
                    markersize=10
                )
                for node_type, color in color_map.items()
            ]

            # Place legend outside the plot
            ax.legend(
                handles=legend_elements,
                loc='center left',
                bbox_to_anchor=(1.05, 0.5),
                title="Node Types"
            )

            # Set title
            ax.set_title("Python Code Knowledge Graph Visualization", pad=20)

            # Adjust layout to accommodate legend
            plt.subplots_adjust(right=0.85)

            # Show plot
            plt.show()

        except ImportError:
            print("Matplotlib is required for visualization. Install it using 'pip install matplotlib'.")

if __name__ == "__main__":
    try:
        print("Python Code Knowledge Graph Generator")
        print("------------------------------------")

        codebase_dir = input("Enter the path to the codebase directory: ").strip()
        if not os.path.exists(codebase_dir):
            raise ValueError(f"Directory does not exist: {codebase_dir}")

        output_file = "python_code_knowledge_graph.json"

        # Create and analyze the codebase
        graph_generator = PythonCodeKnowledgeGraph(directory=codebase_dir)
        graph_generator.analyze_codebase()

        # Save the graph
        graph_generator.save_graph(output_file)

        # Optional visualization
        while True:
            visualize = input("\nWould you like to visualize the graph? (yes/no): ").strip().lower()
            if visualize in ["yes", "no"]:
                break
            print("Invalid choice. Please enter yes or no.")

        if visualize == "yes":
            print("\nGenerating visualization...")
            graph_generator.visualize_graph()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
    finally:
        print("\nDone.")
