"""Knowledge base system for loading and managing markdown documentation.

This module provides functionality for agents to load and access markdown
documentation files (like Godot documentation) to inform their decision-making
and code generation.
"""

import logging
from pathlib import Path
from typing import Optional


class KnowledgeBase:
    """A knowledge base that loads and manages markdown documentation.

    The knowledge base can load markdown files from a directory and provide
    search and retrieval capabilities for agents to access relevant information.

    Attributes:
        name: Name of this knowledge base.
        base_path: Root directory containing the markdown files.
        _documents: Dictionary mapping file paths to their content.
    """

    def __init__(self, name: str, base_path: Optional[Path] = None) -> None:
        """Initialize a new knowledge base.

        Args:
            name: Name of this knowledge base.
            base_path: Optional root directory for markdown files.
        """
        self.name = name
        self.base_path = base_path
        self.logger = logging.getLogger(f"knowledge_base.{name}")
        self._documents: dict[str, str] = {}
        self._loaded = False

    def load_from_directory(self, directory: Path, pattern: str = "**/*.md") -> int:
        """Load all markdown files from a directory.

        Args:
            directory: Directory to load markdown files from.
            pattern: Glob pattern for matching files (default: **/*.md).

        Returns:
            Number of documents loaded.

        Raises:
            ValueError: If directory doesn't exist.
        """
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        self.logger.info(f"Loading markdown files from {directory} with pattern {pattern}")

        count = 0
        for md_file in directory.glob(pattern):
            if md_file.is_file():
                try:
                    content = md_file.read_text(encoding="utf-8")
                    # Store relative path as key
                    relative_path = str(md_file.relative_to(directory))
                    self._documents[relative_path] = content
                    count += 1
                    self.logger.debug(f"Loaded: {relative_path}")
                except Exception as e:
                    self.logger.error(f"Failed to load {md_file}: {e}")

        self._loaded = True
        self.logger.info(f"Loaded {count} markdown documents")
        return count

    def load_from_file(self, file_path: Path, key: Optional[str] = None) -> None:
        """Load a single markdown file.

        Args:
            file_path: Path to the markdown file.
            key: Optional key to store the document under. If None, uses filename.

        Raises:
            ValueError: If file doesn't exist.
        """
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")
            doc_key = key or file_path.name
            self._documents[doc_key] = content
            self._loaded = True
            self.logger.info(f"Loaded document: {doc_key}")
        except Exception as e:
            self.logger.error(f"Failed to load {file_path}: {e}")
            raise

    def load_from_string(self, content: str, key: str) -> None:
        """Load markdown content from a string.

        Args:
            content: The markdown content.
            key: Key to store the document under.
        """
        self._documents[key] = content
        self._loaded = True
        self.logger.debug(f"Loaded document from string: {key}")

    def get_document(self, key: str) -> Optional[str]:
        """Retrieve a document by its key.

        Args:
            key: The document key.

        Returns:
            The document content, or None if not found.
        """
        return self._documents.get(key)

    def search(self, query: str, case_sensitive: bool = False) -> list[tuple[str, str]]:
        """Search for documents containing a query string.

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

    def get_document_count(self) -> int:
        """Get the number of documents in the knowledge base.

        Returns:
            Number of documents.
        """
        return len(self._documents)

    def clear(self) -> None:
        """Clear all documents from the knowledge base."""
        self._documents.clear()
        self._loaded = False
        self.logger.info("Knowledge base cleared")

    def is_loaded(self) -> bool:
        """Check if the knowledge base has been loaded.

        Returns:
            True if documents have been loaded, False otherwise.
        """
        return self._loaded

    def get_summary(self) -> dict[str, any]: # type: ignore
        """Get a summary of the knowledge base.

        Returns:
            Dictionary containing knowledge base statistics.
        """
        return {
            "name": self.name,
            "document_count": self.get_document_count(),
            "loaded": self.is_loaded(),
            "base_path": str(self.base_path) if self.base_path else None,
        }