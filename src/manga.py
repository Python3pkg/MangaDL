import os
import platform
from time import sleep
import importlib
import logging
import re
from urllib import request
from configparser import ConfigParser
from clint.textui import puts
from progressbar import ProgressBar, Percentage, Bar, SimpleProgress, AdaptiveETA
from mangopi.metasite import MetaSite
from src.config import Config


class Manga:
    def __init__(self):
        """
        Initialize a new Manga instance
        """
        self.config = Config().app_config()
        self.log = logging.getLogger('manga-dl.manga')
        self._site_modules = self._load_sites()
        self.meta_search = MetaSite(self._site_modules)
        self.throttle = self.config.getint('Common', 'throttle', fallback=1)
        self.progress_widget = [Percentage(), ' ', Bar(), ' Pages: ', SimpleProgress(), ' ', AdaptiveETA()]

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
            module = importlib.import_module('mangopi.site.' + name)

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
        :rtype : collections.OrderedDict of (str, MetaSite.MetaChapter)
        """
        self.log.info('Searching for series: {title}'.format(title=title))
        series = self.meta_search.series(title)
        puts('Loading Manga chapter data, this may take a few moments')
        chapters = series.chapters

        # If we have no chapters, we didn't get any matching search results
        self.log.info('{num} chapters found'.format(num=len(chapters)))
        if not len(chapters):
            raise NoSearchResultsError

        return chapters

    def download(self, chapter):
        """
        Download all pages in a chapter
        :param chapter: The chapter to download
        :type  chapter: MetaSite.MetaChapter
        """
        self.log.info('Downloading chapter {num}: {title}'.format(num=chapter.chapter, title=chapter.title))
        puts('Loading Manga page data, this may take a while')
        pages = chapter.pages
        page_count = len(pages)
        self.log.info('{num} pages found'.format(num=page_count))

        # Set up the manga directory
        self.log.debug('Formatting the manga directory path')
        manga_dir_template = self.config.get('Paths', 'manga_dir')
        manga_path = manga_dir_template
        self.log.debug('Manga path set: {path}'.format(path=manga_path))

        # Set up the series directory
        self.log.debug('Formatting the series directory path')
        series_dir_template = self.config.get('Paths', 'series_dir')
        series_path = os.path.join(manga_path, series_dir_template.format(series=chapter.series.name))
        self.log.debug('Series path set: {path}'.format(path=series_path))

        # Set up the volume directory
        self.log.debug('Formatting the volume directory path')
        volume_dir_template = self.config.get('Paths', 'volume_dir')
        volume = chapter.volume if hasattr(chapter, 'volume') else 0
        volume_path = os.path.join(series_path, volume_dir_template.format(volume=volume))
        self.log.debug('Volume path set: {path}'.format(path=volume_path))

        # Set up the Chapter directory
        self.log.debug('Formatting chapter directory path')
        chapter_dir_template = self.config.get('Paths', 'chapter_dir')
        chapter_path = os.path.join(volume_path, chapter_dir_template.format(chapter=chapter.chapter,
                                                                             title=chapter.title))
        self.log.debug('Chapter path set: {path}'.format(path=chapter_path))

        if not os.path.isdir(chapter_path):
            self.log.debug('Creating chapter directory')
            os.makedirs(chapter_path, 0o755)

        # Escape our dir templates for regex parsing
        page_filename_template = self.config.get('Paths', 'page_filename')
        series_re_template  = series_dir_template
        volume_re_template  = volume_dir_template
        chapter_re_template = chapter_dir_template.replace('[', r'\[').replace(']', r'\]')
        page_re_template    = page_filename_template

        # Format the pattern templates
        series_pattern  = '^' + series_re_template.format(series=r'(?P<series>\.+)') + '$'
        volume_pattern  = '^' + volume_re_template.format(volume=r'(?P<volume>\d+(\.\d)?)') + '$'
        chapter_pattern = '^' + chapter_re_template.format(chapter=r'(?P<chapter>\d+(\.\d)?)',
                                                            title=r'(?P<title>.+)') + '$'
        page_pattern    = '^' + page_re_template.format(page=r'(?P<page>\d+(\.\d)?)', ext=r'\w{3,4}') + '$'

        # Set up the series configuration
        config = ConfigParser()

        config.add_section('Patterns')
        config.set('Patterns', 'series_pattern', series_pattern)
        config.set('Patterns', 'volume_pattern', volume_pattern)
        config.set('Patterns', 'chapter_pattern', chapter_pattern)
        config.set('Patterns', 'page_pattern', page_pattern)

        config.add_section('Common')
        config.set('Common', 'version', '0.1.0')

        # Write to and close the configuration file
        config_path = os.path.join(series_path, '.' + Config().app_config_file)
        config_file = open(config_path, 'w')
        config.write(config_file)
        config_file.close()

        # If we're on Windows, make the configuration file hidden
        if platform.system() == 'Windows':
            p = os.popen('attrib +h ' + config_path)
            t = p.read()
            p.close()

        # Set up the progress bar
        progress_bar = ProgressBar(page_count, self.progress_widget)
        progress_bar.start()

        for page_no, page in enumerate(pages, 1):
            # Set the filename and path
            page_filename = page_filename_template.format(page=page_no, ext='jpg')
            self.log.debug('Page filename set: {filename}'.format(filename=page_filename))
            page_path = os.path.join(chapter_path, page_filename)

            # Download and save the page image
            image = page.image
            if not image:
                self.log.warn('Page found but it has no image resource available')
                raise ImageResourceUnavailableError

            request.urlretrieve(image.url, page_path)
            self.log.debug('Updating progress page number: {page_no}'.format(page_no=page_no))
            progress_bar.update(page_no)
            sleep(self.throttle)

    def update(self, chapter):
        """
        Download a chapter only if it doesn't already exist, and replace any missing pages in existing chapters
        :param chapter: The chapter to update
        :type  chapter: MetaSite.MetaChapter
        """
        pass

    def get(self, chapter):
        """
        Retrieve local metadata on a given Manga chapter
        :param chapter: The chapter to retrieve
        :type  chapter: MetaSite.MetaChapter

        :return: MetaChapter instance if it exists, otherwise None
        :rtype : object or None
        """

    def all(self):
        """
        Return all locally available Manga saves

        :return: List of MangaMeta instances
        :rtype : list of MangaMeta
        """
        manga_list = []
        for path_item in os.listdir(self.config.get('Paths', 'manga_dir')):
            try:
                manga_list.append(MangaMeta(path_item))
            except MangaNotSavedError:
                continue
        return manga_list


# noinspection PyTypeChecker
class MangaMeta:
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
        self.volumes = {}

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
                self.volume_pattern  = re.compile(self._series_config.get('Patterns', 'volume_pattern', raw=True))
                self.chapter_pattern = re.compile(self._series_config.get('Patterns', 'chapter_pattern', raw=True))
                self.page_pattern    = re.compile(self._series_config.get('Patterns', 'page_pattern', raw=True))

                # Break on match
                break
        else:
            # Title was not found, abort loading
            raise MangaNotSavedError('Manga title "{manga}" could not be loaded from the filesystem'
                                     .format(manga=self.title))

        # Successful match if we're still here, load all available volumes
        self._load_volumes()

    def _load_volumes(self):
        """
        Load all available volumes for the Manga series
        """
        for path_item in os.listdir(self.path):
            match = self.volume_pattern.match(path_item)
            if match:
                volume_path = os.path.join(self.path, path_item)
                volume = match.group('volume')  # volume number
                self.volumes[volume] = VolumeMeta(volume_path, volume, self)


# noinspection PyTypeChecker
class VolumeMeta:
    """
    Manga Volume Metadata
    """
    def __init__(self, path, volume, manga):
        """
        Initialize a new Volume Meta instance
        :param path: Filesystem path to the volume
        :type  path: str

        :param volume: The volume number
        :type  volume: str

        :param manga: The MangaMeta instance for this volume
        :type  manga: MangaMeta
        """
        self.log = logging.getLogger('manga-dl.volume-meta')

        # Volume metadata
        self.volume   = volume
        self.path     = path
        self.manga    = manga
        self.chapters = {}

        self._load_chapters()

    def _load_chapters(self):
        """
        Load all available chapters for the volume
        """
        volume_paths = os.listdir(self.path)

        for path_item in volume_paths:
            match = self.manga.chapter_pattern.match(path_item)
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
        self.pages   = {}

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


class MangaNotSavedError(Exception):
    pass