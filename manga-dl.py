#!/bin/env python3
import logging
from src.config import Config
from src.cli import CLI


def main():
    config = Config()
    cli = CLI()

    # Set up logging
    log = logging.getLogger('manga-dl')
    log_formatter = logging.Formatter("[%(asctime)s] %(levelname)s.%(name)s: %(message)s")

    # Set up our console logger
    log.setLevel(logging.DEBUG)
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.DEBUG)
    console_logger.setFormatter(log_formatter)
    log.addHandler(console_logger)

    # If this is our first time running the application, run setup first
    if not config.app_config_exists():
        cli.setup()

    cli.prompt()

if __name__ == '__main__':
    main()