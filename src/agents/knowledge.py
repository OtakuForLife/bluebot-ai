"""Knowledge base system for loading and managing markdown documentation.

This module provides functionality for agents to load and access markdown
documentation files (like Godot documentation) to inform their decision-making
and code generation.
"""

import logging
from pathlib import Path
from typing import Optional


class KnowledgeBase:

    KNOWLEGDE_PATH = Path(__file__).parent.parent.parent / "knowledge"

    def __init__(self, name: str, pattern: str = "**/*.md") -> None:
        """Initialize a new knowledge base.

        Args:
            name: Name of this knowledge base. Same as the directory name.
            pattern: pattern to load only specific files
        """
        self.name = name
        self.directory = self.KNOWLEGDE_PATH / name
        self.logger = logging.getLogger(f"knowledge_base.{name}")
        self._documents: dict[str, str] = {}

        if not self.directory.exists():
            raise ValueError(f"Directory does not exist: {self.directory}")

        if not self.directory.is_dir():
            raise ValueError(f"Path is not a directory: {self.directory}")

        self.logger.info(f"Loading markdown files from {self.directory} with pattern {pattern}")

        count = 0
        for md_file in self.directory.glob(pattern):
            if md_file.is_file():
                try:
                    content = md_file.read_text(encoding="utf-8")
                    # Store relative path as key
                    relative_path = str(md_file.relative_to(self.directory))
                    self._documents[relative_path] = content
                    count += 1
                    self.logger.debug(f"Loaded: {relative_path}")
                except Exception as e:
                    self.logger.error(f"Failed to load {md_file}: {e}")

        self.logger.info(f"Loaded {count} markdown documents")


    def get_document(self, key: str) -> Optional[str]:
        """Retrieve a document by its key.

        Args:
            key: The document key.

        Returns:
            The document content, or None if not found.
        """
        return self._documents.get(key)

    def search(self, query: str, case_sensitive: bool = False) -> list[tuple[str, str]]:
        """Simple search for documents containing a query string.

        Args:
            query: The search query.
            case_sensitive: Whether to perform case-sensitive search.

        Returns:
            List of tuples (key, content) for matching documents.
        """
        results = []
        search_query = query if case_sensitive else query.lower()

        for key, content in self._documents.items():
            search_content = content if case_sensitive else content.lower()
            if search_query in search_content:
                results.append((key, content))

        self.logger.debug(f"Search for '{query}' found {len(results)} results")
        return results

    def get_all_keys(self) -> list[str]:
        """Get all document keys in the knowledge base.

        Returns:
            List of all document keys.
        """
        return list(self._documents.keys())


