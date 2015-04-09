#!/bin/env python3
from src.config import Config
from src.cli import CLI


def main():
    config = Config()
    cli = CLI()

    # If this is our first time running the application, run setup first
    if not config.app_config_exists():
        cli.setup()

    cli.prompt()

if __name__ == '__main__':
    main()