import sys
import logging
from os import path, makedirs, execl
from clint.textui import puts, prompt, colored
import img2pdf
from scrapers import ScraperManager
from src.config import Config
from src.manga import Manga, SeriesMeta, NoSearchResultsError, ImageResourceUnavailableError, MangaAlreadyExistsError


# noinspection PyUnboundLocalVariable,PyBroadException
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
        self.scraper_manager = ScraperManager()
        self.log = logging.getLogger('manga-dl.cli')
        if path.isfile(self.config.app_config_path):
            self.config = self.config.app_config()
            self.manga = Manga()

    def _manga_prompt(self, query='Which Manga title would you like to use?'):
        """
        Prompt the user to select a saved Manga entry
        :param query: The prompt query message
        :type  query: str

        :return: The metadata instance of the selected Manga
        :rtype : SeriesMeta

        :raises: NoMangaSavesError
        """
        manga_list = self.manga.all()
        if not manga_list:
            puts('No Manga titles have been downloaded yet, download something first!')
            raise NoMangaSavesError

        # Print our a list of available Manga saves
        puts()
        for key, manga in enumerate(manga_list, 1):
            puts('{key}. {title}'.format(key=key, title=manga.title))
        puts()

        # Prompt the user for the Manga title to update
        while True:
            try:
                update_key = int(prompt.query(query))
                local_manga = manga_list[update_key - 1]
            except (ValueError, IndexError):
                self.log.info('User provided invalid update input')
                puts('Invalid entry, please select a Manga entry from the above list')
                continue
            break
        return local_manga

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
        action = prompt.query('What would you like to do?').lower()
        if action not in self.PROMPT_ACTIONS:
            self.log.info('User provided an invalid action response')
            puts('Invalid selection, please chose from one of the options listed above')
            return self.prompt(False)

        action = self.PROMPT_ACTIONS[action]
        action_method = getattr(self, action)
        action_method()

    def download(self):
        """
        Download a new Manga title
        """
        title = prompt.query('What is the title of the Manga series?').strip()
        puts()

        # Fetch all available chapters
        try:
            series = self.manga.search(title)
        except NoSearchResultsError:
            puts('No search results returned for {query}'.format(query=colored.blue(title, bold=True)))
            if prompt.query('Exit?', 'Y').lower().strip() in self.YES_RESPONSES:
                self.exit()
            return

        # Create the series
        try:
            self.manga.create_series(series)
        except MangaAlreadyExistsError:
            # Series already exists, prompt the user for confirmation to continue
            puts('This Manga has already been downloaded')
            continue_prompt = prompt.query('Do you still wish to continue and overwrite the series?', 'N')
            if continue_prompt.lower().strip() not in self.YES_RESPONSES:
                self.exit()

        # Print out the number of chapters to be downloaded
        chapter_count = len(series.chapters)
        puts('{count} chapters added to queue'.format(count=chapter_count))

        # Loop through our chapters and download_chapter them
        for chapter_no, chapter in series.chapters.items():
            manga = SeriesMeta(series.title)
            try:
                self.manga.download_chapter(chapter, manga)
            except ImageResourceUnavailableError:
                puts('A match was found, but no image resources for the pages appear to be available')
                puts('This probably means the Manga was licensed and has been removed')
                if prompt.query('Exit?', 'Y').lower().strip() in self.YES_RESPONSES:
                    self.exit()
                return self.prompt()
            except AttributeError as e:
                self.log.warn('An exception was raised downloading this chapter', exc_info=e)
                puts('Chapter does not appear to have any readable pages, skipping')
                continue
            except Exception as e:
                self.log.error('Uncaught exception thrown', exc_info=e)
                response = prompt.query('An unknown error occurred trying to download this chapter. Continue?', 'Y')
                if response.lower().strip() in self.YES_RESPONSES:
                    continue
                puts('Exiting')
                break

    def update(self):
        """
        Update an existing Manga title
        """
        try:
            local_manga = self._manga_prompt('Which Manga title would you like to update?')
        except NoMangaSavesError:
            return

        # Run a search query on the selected title
        try:
            remote_series = self.manga.search(local_manga.title)
        except NoSearchResultsError:
            return puts('No search results returned for {query} (the title may have been licensed or otherwise removed)'
                        .format(query=colored.blue(local_manga.title, bold=True)))

        for remote_chapter in remote_series.chapters.values():
            try:
                self.manga.update(remote_chapter, local_manga)
            except ImageResourceUnavailableError:
                puts('A match was found, but no image resources for the pages appear to be available')
                puts('This probably means the Manga was licensed and has been removed')
                if prompt.query('Exit?', 'Y').lower().strip() in self.YES_RESPONSES:
                    self.exit()
                return self.prompt()
            except AttributeError as e:
                self.log.warn('An exception was raised downloading this chapter', exc_info=e)
                puts('Chapter does not appear to have any readable pages, skipping')
                continue
            except Exception as e:
                self.log.error('Uncaught exception thrown', exc_info=e)
                response = prompt.query('An unknown error occurred trying to download this chapter. Continue?', 'Y')
                if response.lower().strip() in self.YES_RESPONSES:
                    continue
                puts('Exiting')
                break

    def create_pdf(self):
        """
        Create PDFs for a Manga series
        """
        try:
            self.log.debug('Prompting the user for a Manga to create a PDF from')
            manga = self._manga_prompt()
        except NoMangaSavesError:
            self.log.info('No Manga\'s available to create PDFs from')
            return

        # Prompt for chapter / series PDF creation
        while True:
            self.log.debug('Prompting the user for Chapter or Series PDF creation')
            puts('\nWould you like to create individual PDF\'s for each chapter, or one for the entire series?')
            response = prompt.query('Chapter / Series?', 'CHAPTER').lower().strip()
            if response in ['c', 'chapter']:
                pdf_type = 'chapter'
            elif response in ['s', 'series']:
                pdf_type = 'series'
            else:
                puts('Invalid response, please enter in either "CHAPTER" or "SERIES"')
                continue
            break

        # Flip the order of the pages, so that the PDF can be read in reverse order
        reverse = prompt.query('\nWould you like to add the pages in reverse order? (Manga will be read backwards)',
                               'N')
        reverse = True if reverse.lower().strip() in self.YES_RESPONSES else False

        page_paths = []
        # If we're just creating one giant series PDF, do that now and return
        if pdf_type == 'series':
            self.log.info('Retrieving a list of paths to all pages in all chapters')
            for chapter in manga.chapters.values():
                page_paths += [page.path for page in chapter.pages.values()]
            if reverse:
                page_paths.reverse()
            page_count = len(page_paths)
            chapter_count = len(manga.chapters)
            self.log.info('{num} pages queued'.format(num=page_count))

            # Create the PDF and write it to a file
            pdf_header = '\nCreating a PDF for the entire {series} series, containing {chapter_count} chapters and ' \
                         '{page_count} pages'
            pdf_header = colored.yellow(pdf_header)
            puts(pdf_header.format(series=manga.title, chapter_count=chapter_count, page_count=page_count))

            pdf = img2pdf.convert(page_paths)
            pdf_path = path.join(manga.path, 'PDF', manga.title + '.pdf')
            pdf_file = open(pdf_path, 'wb')
            pdf_file.write(pdf)
            pdf_file.close()

            puts('PDF created and saved successfully to {path}'.format(path=pdf_path))
            return

        # Create individual PDFs for each chapter
        for chapter in manga.chapters.values():
            pdf_header = '\nCreating a PDF for Chapter {chapter}: {title}'
            pdf_header = colored.yellow(pdf_header)
            puts(pdf_header.format(chapter=chapter.chapter, title=chapter.title))

            page_paths = [page.path for page in chapter.pages.values()]
            if reverse:
                page_paths.reverse()
            pdf = img2pdf.convert(page_paths)
            pdf_filename = 'Chapter {chapter}: {title}'.format(chapter=chapter.chapter, title=chapter.title)
            pdf_path = path.join(manga.path, 'PDF', pdf_filename + '.pdf')
            makedirs(path.join(manga.path, 'PDF'), 0o755, True)
            pdf_file = open(pdf_path, 'wb')
            pdf_file.write(pdf)
            pdf_file.close()

            puts('PDF created and saved successfully to {path}'.format(path=pdf_path))

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
            puts('\nWhich Manga websites would you like to enable?')

            sites = self.scraper_manager.scrapers
            sites_map = {}
            for key, site in enumerate(sites, 1):
                sites_map[key] = site
                puts('{key}. {site}'.format(key=key, site=site))

            csv = ','.join(str(i) for i in range(1, len(sites) + 1))  # Generate a comma separated range list
            site_keys = prompt.query('Provide a comma separated list, highest priority first', csv)
            site_keys = site_keys.split(',')

            try:
                enabled_sites = []
                for site_key in site_keys:
                    site_key = int(site_key.strip())
                    self.log.info('Appending site: {site}'.format(site=sites_map[site_key]))
                    enabled_sites.append(sites_map[site_key])
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
        chapter_dir = '[Chapter {chapter}] - {title}'
        page_filename = 'page-{page}.{ext}'

        # Development mode
        debug_mode = prompt.query('\nWould you like to enable debug mode?', 'N')
        debug_mode = True if debug_mode.lower().strip() in self.YES_RESPONSES else False

        # Define the configuration values
        config = {'Paths': {'manga_dir': manga_dir, 'series_dir': series_dir, 'chapter_dir': chapter_dir,
                            'page_filename': page_filename},

                  'Common': {'sites': ','.join(enabled_sites), 'synonyms': str(synonyms_enabled), 'debug': debug_mode,
                             'throttle': 1}}

        Config().app_config_create(config)
        execl(sys.executable, *([sys.executable] + sys.argv))

    @staticmethod
    def exit():
        """
        Exit the application
        """
        sys.exit()


class NoMangaSavesError(Exception):
    pass