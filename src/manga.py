import os
import platform
from time import sleep
import importlib
import logging
import re
from collections import OrderedDict
from urllib import request
from urllib.error import ContentTooShortError
from configparser import ConfigParser
from clint.textui import puts
from progressbar import ProgressBar, Percentage, Bar, SimpleProgress, AdaptiveETA
from src.config import Config


class Manga:
    """
    Manga downloading and updating services
    """
    def __init__(self):
        """
        Initialize a new Manga instance
        """
        self.config = Config().app_config()
        self.log = logging.getLogger('manga-dl.manga')
        self._site_modules = self._load_sites()
        self.throttle = self.config.getint('Common', 'throttle', fallback=1)
        self.progress_widget = [Percentage(), ' ', Bar(), ' Page: ', SimpleProgress(), ' ', AdaptiveETA()]

        # Define the directory / filename templates
        self.manga_dir_template = self.config.get('Paths', 'manga_dir')
        self.series_dir_template = self.config.get('Paths', 'series_dir')
        self.chapter_dir_template = self.config.get('Paths', 'chapter_dir')
        self.page_filename_template = self.config.get('Paths', 'page_filename')

    def _load_sites(self):
        """
        Load the configured sites
        :return: A list of mangopi site classes
        :rtype : list
        """
        sites = self.config.get('Common', 'sites')
        if not isinstance(sites, str):
            return
        sites = sites.split(',')

        # Import the site modules
        self.log.info('Loading site modules: {sites}'.format(sites=str(sites)))
        site_modules = []
        for site in sites:
            name = re.sub(r'\W+', '', site.lower())
            module = importlib.import_module('scrapers.sites.' + name)

            site_module = getattr(module, site)
            self.log.info('Appending module: {module}'.format(module=str(site_module)))
            site_modules.append(site_module)

        return site_modules

    def search(self, title):
        """
        Search for a given Manga title
        :param title: The name of the Manga series
        :type  title: str

        :return: Ordered dictionary of mangopi metasite chapter instances
        :rtype : MetaChapter
        """
        for module in self._site_modules:
            self.log.info('Assigning site: ' + str(module))
            self.log.info('Searching for series: {title}'.format(title=title))
            site = module()
            try:
                site.series = title
            except NoSearchResultsError:
                continue
            break
        else:
            raise NoSearchResultsError

        return site.series

    def create_series(self, series):
        """
        Create a new Manga series placeholder on the filesystem
        :param series: The meta instance of the Manga series
        :type  series: SeriesMeta
        """
        # Set up the manga directory
        self.log.debug('Formatting the manga directory path')
        manga_path = self.manga_dir_template
        self.log.debug('Manga path set: {path}'.format(path=manga_path))

        # Set up the series directory
        self.log.debug('Formatting the series directory path')
        series_path = os.path.join(manga_path, self.series_dir_template.format(series=series.title))
        self.log.debug('Series path set: {path}'.format(path=series_path))

        if not os.path.isdir(series_path):
            self.log.debug('Creating series directory')
            os.makedirs(series_path, 0o755)

        # Escape our dir templates for regex parsing
        series_re_template  = self.series_dir_template
        chapter_re_template = self.chapter_dir_template.replace('[', r'\[').replace(']', r'\]')
        page_re_template    = self.page_filename_template

        # Format the pattern templates
        series_pattern  = '^' + series_re_template.format(series=r'(?P<series>\.+)') + '$'
        chapter_pattern = '^' + chapter_re_template.format(chapter=r'(?P<chapter>\d+(\.\d)?)',
                                                           title=r'(?P<title>.+)') + '$'
        page_pattern    = '^' + page_re_template.format(page=r'(?P<page>\d+(\.\d)?)', ext=r'\w{3,4}') + '$'

        # Set up the series configuration
        config = ConfigParser()

        config.add_section('Patterns')
        config.set('Patterns', 'series_pattern', series_pattern)
        config.set('Patterns', 'chapter_pattern', chapter_pattern)
        config.set('Patterns', 'page_pattern', page_pattern)

        config.add_section('Common')
        config.set('Common', 'version', '0.1.0')

        # Write to and close the configuration file
        config_path = os.path.join(series_path, '.' + Config().app_config_file)

        # This series has already been created and configured
        if os.path.isfile(config_path):
            raise MangaAlreadyExistsError

        config_file = open(config_path, 'w')
        config.write(config_file)
        config_file.close()

        # If we're on Windows, make the configuration file hidden
        if platform.system() == 'Windows':
            p = os.popen('attrib +h ' + config_path)
            t = p.read()
            p.close()

    def download_chapter(self, chapter, manga, overwriting=True):
        """
        Download all pages in a chapter
        :param chapter: The chapter to download_chapter
        :type  chapter: MetaSite.MetaChapter

        :param manga: The local Manga series
        :type  manga: SeriesMeta

        :param overwriting: Overwrite existing pages
        :type  overwriting: bool
        """
        self.log.info('Downloading chapter {chapter}: {title}'.format(chapter=chapter.chapter, title=chapter.title))
        puts('\nChapter {chapter}: {title}'.format(chapter=chapter.chapter, title=chapter.title))
        pages = chapter.pages
        page_count = len(pages)
        self.log.info('{num} pages found'.format(num=page_count))

        # Set up the Chapter directory
        self.log.debug('Formatting chapter directory path')
        chapter_path = os.path.join(manga.path, self.chapter_dir_template.format(chapter=chapter.chapter,
                                                                                 title=chapter.title))
        self.log.debug('Chapter path set: {path}'.format(path=chapter_path))

        if not os.path.isdir(chapter_path):
            self.log.debug('Creating chapter directory')
            os.makedirs(chapter_path, 0o755)

        # Set up the progress bar
        progress_bar = ProgressBar(page_count, self.progress_widget)
        progress_bar.start()

        for index, page in enumerate(pages.values(), 1):
            # Set the filename and path
            page_filename = self.page_filename_template.format(page=page.page, ext='jpg')
            self.log.debug('Page filename set: {filename}'.format(filename=page_filename))
            page_path = os.path.join(chapter_path, page_filename)

            # If we're not overwriting and the file exists, skip it
            if not overwriting and os.path.exists(page_path):
                self.log.info('Skipping existing page ({page})'.format(page=page.page))
                progress_bar.update(index)
                continue

            # Download and save the page image
            image = page.image
            if not image:
                self.log.warn('Page found but it has no image resource available')
                raise ImageResourceUnavailableError

            failures = 0
            retry_throttle = 2
            while True:
                try:
                    request.urlretrieve(image.url, page_path)
                except ContentTooShortError:
                    # If we've already tried this download several times, give up
                    if failures >= 5:
                        self.log.error('Unable to download a page after several attempts were made, giving up')
                        raise

                    # Increase our failure count and throttle, then try again
                    failures += 1
                    sleep(retry_throttle)
                    retry_throttle *= 2
                    self.log.warn('Page download failed partway through, waiting a couple seconds then trying again')
                break

            self.log.debug('Updating progress page number: {page_no}'.format(page_no=page.page))
            progress_bar.update(index)
            sleep(self.throttle)
        puts()

    def update(self, chapter, manga, checking_pages=True):
        """
        Download a chapter only if it doesn't already exist, and replace any missing pages in existing chapters
        :param chapter: The chapter to update
        :type  chapter: MetaSite.MetaChapter

        :param manga: The local Manga series being updated
        :type  manga: SeriesMeta
        """
        # If we don't have this chapter yet, download_chapter it
        if chapter.chapter in manga.chapters and not checking_pages:
            self.log.info('Skipping existing chapter: ({no}) {title}'.format(no=chapter.chapter, title=chapter.title))
            return

        self.download_chapter(chapter, manga, overwriting=False)

    def get(self, chapter):
        """
        Retrieve local metadata on a given Manga chapter
        :param chapter: The chapter to retrieve
        :type  chapter: MetaSite.MetaChapter

        :return: MetaChapter instance if it exists, otherwise None
        :rtype : object or None
        """
        pass

    def all(self):
        """
        Return all locally available Manga saves

        :return: List of MangaMeta instances
        :rtype : list of SeriesMeta
        """
        manga_list = []
        for path_item in os.listdir(self.config.get('Paths', 'manga_dir')):
            try:
                manga_list.append(SeriesMeta(path_item))
            except MangaNotSavedError:
                continue
        return manga_list


# noinspection PyTypeChecker
class SeriesMeta:
    """
    Manga Metadata
    """
    def __init__(self, title):
        """
        Initialize a new Manga Meta instance

        :param title: The title of the Manga series to load
        :type  title: str
        """
        self.log = logging.getLogger('manga-dl.manga-meta')
        self.title = title.strip()
        self.config = Config().app_config()
        self.manga_path = self.config.get('Paths', 'manga_dir')

        # Series configuration placeholders
        self._series_config  = None
        self.volume_pattern  = None
        self.chapter_pattern = None
        self.page_pattern    = None

        # Manga metadata placeholders
        self.path = None
        self.chapters = OrderedDict()

        self._load()

    def _load(self):
        """
        Attempt to load the requested Manga title
        """
        manga_paths = os.listdir(self.manga_path)

        # Loop through the manga directories and see if we can find a match
        for path_item in manga_paths:
            self.path = os.path.join(self.manga_path, path_item)
            if self.title.lower() == path_item.lower() and os.path.isdir(self.path):
                self.log.info('Match found: {dir}'.format(dir=path_item))
                # Series matched, define the path and begin loading
                self.path = os.path.join(self.manga_path, path_item)

                # Load the series configuration file
                series_config_path  = os.path.join(self.path, '.' + Config().app_config_file)
                if not os.path.isfile(series_config_path):
                    continue
                self._series_config = ConfigParser()
                self._series_config.read(series_config_path)

                # Compile the regex patterns
                self.series_pattern  = re.compile(self._series_config.get('Patterns', 'series_pattern', raw=True))
                self.chapter_pattern = re.compile(self._series_config.get('Patterns', 'chapter_pattern', raw=True))
                self.page_pattern    = re.compile(self._series_config.get('Patterns', 'page_pattern', raw=True))

                # Break on match
                break
        else:
            # Title was not found, abort loading
            raise MangaNotSavedError('Manga title "{manga}" could not be loaded from the filesystem'
                                     .format(manga=self.title))

        # Successful match if we're still here, load all available chapters
        self._load_chapters()

    def _load_chapters(self):
        """
        Load all available chapters for the volume
        """
        series_path = os.listdir(self.path)

        for path_item in series_path:
            match = self.chapter_pattern.match(path_item)
            if match:
                chapter_path = os.path.join(self.path, path_item)
                chapter = match.group('chapter')  # chapter number
                title = match.group('title')  # chapter title
                self.chapters[chapter] = ChapterMeta(chapter_path, chapter, title, self)


class ChapterMeta:
    """
    Volume Chapter Metadata
    """
    def __init__(self, path, chapter, title, volume):
        """
        Initialize a new Chapter Meta instance
        :param path: Filesystem path to the chapter
        :type  path: str

        :param chapter: The chapter number
        :type  chapter: str

        :param title: The chapter title
        :type  title: str

        :param volume: The VolumeMeta instance for this chapter
        :type  volume: VolumeMeta
        """
        self.log = logging.getLogger('manga-dl.chapter-meta')

        # Chapter metadata
        self.chapter = chapter
        self.title   = title
        self.path    = path
        self.manga   = volume.manga
        self.pages   = OrderedDict()

        self._load_pages()

    def _load_pages(self):
        """
        Load all available pages for the chapter
        """
        chapter_paths = os.listdir(self.path)

        for path_item in chapter_paths:
            match = self.manga.page_pattern.match(path_item)
            if match:
                page_path = os.path.join(self.path, path_item)
                page = match.group('page')  # page number
                self.pages[page] = PageMeta(page_path, page, self)


class PageMeta:
    """
    Chapter Page Metadata
    """
    def __init__(self, path, page, chapter):
        """
        Initialize a new Page Meta instance
        :param path: Filesystem path to the page
        :type  path: str

        :param page: The page number
        :type  page: str

        :param chapter: The ChapterMeta instance for this page
        :type  chapter: ChapterMeta
        """
        self.log = logging.getLogger('manga-dl.page-meta')
        self.page = page
        self.chapter = chapter
        self.path = path


class NoSearchResultsError(Exception):
    pass


class ImageResourceUnavailableError(Exception):
    pass


class MangaAlreadyExistsError(Exception):
    pass


class MangaNotSavedError(Exception):
    pass