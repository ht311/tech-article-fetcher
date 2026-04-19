"""Entry point for src module."""
import asyncio

from src.cli.main import main

if __name__ == "__main__":
    asyncio.run(main())

