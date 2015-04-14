#!/bin/env python3.4

import os
import sys
import logging
from src.config import Config
from src.cli import CLI

__author__     = "Makoto Fujikawa"
__copyright__  = "Copyright 2015, Makoto Fujikawa"
__version__    = "0.1.0"
__maintainer__ = "Makoto Fujikawa"


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
        log.setLevel(logging.CRITICAL)

    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.DEBUG)
    console_logger.setFormatter(log_formatter)
    log.addHandler(console_logger)

    # If this is our first time running the application, run setup first
    try:
        if not config:
            cli.setup()

        cli.prompt()
        while True:
            print()
            cli.prompt(False)
    except KeyboardInterrupt:
        print('\nExiting\n')
        cli.exit()

if __name__ == '__main__':
    main()