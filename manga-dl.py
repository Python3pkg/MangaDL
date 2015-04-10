#!/bin/env python3
import os
import sys
import logging
from src.config import Config
from src.cli import CLI


def main():
    config = Config().app_config() if Config().app_config_exists() else None
    cli = CLI()

    # Set up logging
    log = logging.getLogger('manga-dl')
    log_formatter = logging.Formatter("[%(asctime)s] %(levelname)s.%(name)s: %(message)s")

    # Set up our console logger
    if config and config.getboolean('Common', 'debug'):
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.NOTSET)

    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.DEBUG)
    console_logger.setFormatter(log_formatter)
    log.addHandler(console_logger)

    # If this is our first time running the application, run setup first
    if not config:
        cli.setup()
        os.execl(sys.executable, *([sys.executable] + sys.argv))

    cli.prompt()

if __name__ == '__main__':
    main()