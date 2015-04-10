import sys
import logging
from os import path, makedirs
from clint.textui import puts, prompt, colored
from src.config import Config
from src.manga import Manga, NoSearchResultsError, ImageResourceUnavailableError


class CLI:
    # Boolean responses
    YES_RESPONSES = ['y', 'yes', 'true']
    NO_RESPONSES = ['n', 'no', 'false']

    PROMPT_ACTIONS = {'1': 'download', '2': 'update', '3': 'create_pdf', '4': 'delete', 's': 'setup', 'e': 'exit'}

    def __init__(self):
        """
        Initialize a new CLI instance
        """
        self.config = Config()
        self.log = logging.getLogger('manga-dl.cli')

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

    def prompt(self, header=True):
        """
        Prompt for an action
        :param header: Display the application header before the options
        :type  header: bool

        :return : An action to perform
        :rtype : str
        """
        if header:
            self.print_header()
        puts('1. Download new series')
        puts('2. Update existing series')
        puts('3. Create PDF\'s from existing series')
        puts('4. Delete existing series')
        puts('--------------------------------')
        puts('s. Re-run setup')
        puts('e. Exit\n')

        self.log.info('Prompting user for an action')
        action = prompt.query('What would you like to do?')
        if action not in self.PROMPT_ACTIONS:
            self.log.info('User provided an invalid action response')
            puts('Invalid selection, please chose from one of the options listed above')
            return self.prompt(False)

        self.download()

    def download(self):
        title = prompt.query('What is the title of the Manga series?').strip()
        manga = Manga()

        # Fetch all available chapters
        try:
            chapters = manga.search(title)
        except NoSearchResultsError:
            puts('No search results returned for {query}'.format(query=colored.blue(title, bold=True)))
            if prompt.query('Exit?', 'Y').lower().strip() in self.YES_RESPONSES:
                self.exit()
            return self.prompt()

        # Since our dictionary may include "half"/bonus chapters, len() may not produce a viable metric here
        chapter_count = len(chapters)  # A bit hacky, gets the last item of an ordered dictionary
        puts('Downloading {num} chapters'.format(num=chapter_count))

        # Loop through our chapters and download them
        for no, chapter in chapters.items():
            try:
                print(chapter.first_available_choice)
                manga.download(chapter)
            except ImageResourceUnavailableError:
                puts('A match was found, but no image resources for the pages appear to be available')
                puts('This probably means the Manga was licensed and has been removed')
                if prompt.query('Exit?', 'Y').lower().strip() in self.YES_RESPONSES:
                    self.exit()
                return self.prompt()
            except AttributeError as e:
                self.log.error('An exception was raised downloading this chapter', exc_info=e)
                response = prompt.query('An error occured trying to download this chapter. Continue?', 'Y')
                if response.lower().strip() in self.YES_RESPONSES:
                    continue
                puts('Exiting')
                break

    # noinspection PyUnboundLocalVariable
    def setup(self, header=True):
        """
        Run setup tasks for MangaDL
        :param header: Display the setup header prior to user prompts
        :type  header: bool
        """
        self.log.info('Running setup tasks')
        if header:
            puts('MangaDL appears to be running for the first time, initializing setup')

        # Manga directory
        manga_dir_default = path.join(path.expanduser('~'), 'Manga')
        manga_dir = prompt.query('\nWhere would you like your Manga collection to be saved?', manga_dir_default)
        manga_dir = manga_dir.strip().rstrip('/')

        # Create the Manga directory if it doesn't exist
        if not path.exists(manga_dir):
            create_manga_dir = prompt.query('Directory does not exist, would you like to create it now?', 'Y')
            if create_manga_dir.lower().strip() in self.YES_RESPONSES:
                self.log.info('Setting up Manga directory')
                makedirs(manga_dir)
                puts('Manga directory created successfully')
            else:
                self.log.info('User refused to create manga directory, aborting setup')
                puts('Not creating Manga directory, setup aborted')

        # Sites
        while True:
            self.log.info('Prompting for Manga sites to enable')
            sites = []
            puts('\nWhich Manga websites would you like to enable?')

            sites_dictionary = ['MangaHere', 'MangaFox', 'MangaPanda', 'MangaReader']
            for key, site in enumerate(sites_dictionary, 1):
                puts('{key}. {site}'.format(key=key, site=site))

            site_keys = prompt.query('Provide a comma separated list, highest priority first', '1,2,3,4')
            site_keys = site_keys.split(',')

            try:
                for site_key in site_keys:
                    site_key = int(site_key) - 1
                    self.log.info('Appending site: {site}'.format(site=sites_dictionary[site_key]))
                    sites.append(sites_dictionary[site_key])
            except (ValueError, IndexError):
                self.log.info('User provided invalid sites input')
                puts('Please provide a comma separated list of ID\'s from the above list')
                continue

            break

        # Synonyms
        puts('\nMangaDL can attempt to search for known alternative names to Manga titles when no results are found')
        synonyms_enabled = prompt.query('Would you like to enable this functionality?', 'Y')
        synonyms_enabled = True if synonyms_enabled.lower().strip() in self.YES_RESPONSES else False

        # Paths
        series_dir = '{series}'
        volume_dir = 'Volume {volume}'
        chapter_dir = '[Chapter {num}] - {title}'

        # Development mode
        debug_mode = prompt.query('\nWould you like to enable debug mode?', 'N')
        debug_mode = True if debug_mode.lower().strip() in self.YES_RESPONSES else False

        # Define the configuration values
        config = {'Paths': {'manga_dir': manga_dir, 'series_dir': series_dir, 'volume_dir': volume_dir,
                            'chapter_dir': chapter_dir, 'page_filename': 'page-{num}.{ext}'},

                  'Common': {'sites': ','.join(sites), 'synonyms': str(synonyms_enabled), 'debug': debug_mode}}

        self.config.app_config_create(config)

    @staticmethod
    def exit():
        """
        Exit the application
        """
        sys.exit()