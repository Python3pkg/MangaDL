from os import path, makedirs
from src.config import Config
from clint.textui import puts, prompt


class CLI:
    # Boolean responses
    YES_RESPONSES = ['y', 'yes', 'true']
    NO_RESPONSES = ['n', 'no', 'false']

    def __init__(self):
        """
        Initialize a new CLI instance
        """
        self.config = Config()

    @staticmethod
    def print_header():
        """
        Prints the CLI header
        """
        puts("""
                                   ___  __
  /\/\   __ _ _ __   __ _  __ _   /   \/ /
 /    \ / _` | '_ \ / _` |/ _` | / /\ / /
/ /\/\ \ (_| | | | | (_| | (_| |/ /_// /___
\/    \/\__,_|_| |_|\__, |\__,_/___,'\____/
                    |___/
        """)

    def prompt(self):
        """
        Prompt for an action

        :return : An action to perform
        :rtype : str
        """
        self.print_header()
        puts('1. Download new series')
        puts('2. Update existing series')
        puts('3. Create PDF\'s from existing series')
        puts('4. Delete existing series')
        puts('--------------------------------')
        puts('e. Exit\n')

        return prompt.query('What would you like to do?')

    # noinspection PyUnboundLocalVariable
    def setup(self):
        """
        Run setup tasks for MangaDL
        """
        puts('MangaDL appears to be running for the first time, initializing setup')

        # Manga directory
        manga_dir_default = path.join(path.expanduser('~'), 'Manga')
        manga_dir = prompt.query('\nWhere would you like your Manga collection to be saved?', manga_dir_default)
        manga_dir = manga_dir.strip().rstrip('/')

        # Create the Manga directory if it doesn't exist
        if not path.exists(manga_dir):
            create_manga_dir = prompt.query('Directory does not exist, would you like to create it now?', 'Y')
            if create_manga_dir.lower() in self.YES_RESPONSES:
                makedirs(manga_dir)
                puts('Manga directory created successfully')
            else:
                puts('Not creating Manga directory, setup aborted')

        # Sites
        while True:
            sites = []
            puts('\nWhich Manga websites would you like to enable?')

            sites_dictionary = ['MangeHere', 'MangaFox', 'MangaPanda', 'MangaReader']
            for key, site in enumerate(sites_dictionary, 1):
                puts('{key}. {site}'.format(key=key, site=site))

            site_keys = prompt.query('Provide a comma separated list, highest priority first', '1,2,3,4')
            site_keys = site_keys.split(',')

            try:
                for site_key in site_keys:
                    site_key = int(site_key) - 1
                    sites.append(sites_dictionary[site_key])
            except (ValueError, IndexError):
                puts('Please provide a comma separated list of ID\'s from the above list')
                continue

            break

        # Define the configuration values
        config = {'Paths': {'manga_dir': manga_dir, 'chapter_dir': '${manga_dir}/{series}/Chapter {num}',
                            'page_filename': 'page-{num}.{ext}'},

                  'Common': {'sites': ','.join(sites)}}

        self.config.app_config_create(config)