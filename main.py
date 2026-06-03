"""Convenience entrypoint for running the Bluebot AI desktop application."""

import sys

from src.app import main


if __name__ == "__main__":  # pragma: no cover - simple CLI entrypoint
    sys.exit(main())

