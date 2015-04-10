from os import path, makedirs, popen
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
        puts('Loading Manga chapter information')
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

        :return: mangopi metasite
        """
        self.log.info('Downloading chapter {num}: {title}'.format(num=chapter.chapter, title=chapter.title))
        puts('Loading Manga page information, this may take a while')
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
        series_path = path.join(manga_path, series_dir_template.format(series=chapter.series.name))
        self.log.debug('Series path set: {path}'.format(path=series_path))

        # Set up the volume directory
        self.log.debug('Formatting the volume directory path')
        volume_dir_template = self.config.get('Paths', 'volume_dir')
        volume = chapter.volume if hasattr(chapter, 'volume') else 0
        volume_path = path.join(series_path, volume_dir_template.format(volume=volume))
        self.log.debug('Volume path set: {path}'.format(path=volume_path))

        # Set up the Chapter directory
        self.log.debug('Formatting chapter directory path')
        chapter_dir_template = self.config.get('Paths', 'chapter_dir')
        chapter_path = path.join(volume_path, chapter_dir_template.format(num=chapter.chapter, title=chapter.title))
        self.log.debug('Chapter path set: {path}'.format(path=chapter_path))

        if not path.isdir(chapter_path):
            self.log.debug('Creating chapter directory')
            makedirs(chapter_path, 0o755)

        # Set up the series configuration
        config = ConfigParser()
        config.add_section('Paths')
        config.set('Paths', 'series_dir', series_dir_template.format(series=r'(?<series>\.+)'))
        config.set('Paths', 'volume_dir', volume_dir_template.format(volume=r'(?<volume>\d+(\.\d)?)'))
        config.set('Paths', 'chapter_dir', chapter_dir_template.format(num=r'(?<num>\d+(\.\d)?)',
                                                                       title=r'(?<title>.+)'))

        # Write to and close the configuration file
        cfg_path = path.join(series_path, '.' + Config().app_config_file)
        cfg_file = open(cfg_path, 'w')
        config.write(cfg_file)
        cfg_file.close()

        # If we're on Windows, make the configuration file hidden
        if platform.system() == 'Windows':
            p = popen('attrib +h ' + cfg_path)
            t = p.read()
            p.close()

        # Set up the progress bar
        progress_bar = ProgressBar(page_count, self.progress_widget)
        progress_bar.start()

        page_filename_template = self.config.get('Paths', 'page_filename')
        for page_no, page in enumerate(pages, 1):
            # Set the filename and path
            page_filename = page_filename_template.format(num=page_no, ext='jpg')
            self.log.debug('Page filename set: {filename}'.format(filename=page_filename))
            page_path = path.join(chapter_path, page_filename)

            # Download and save the page image
            image = page.image
            if not image:
                self.log.warn('Page found but it has no image resource available')
                raise ImageResourceUnavailableError

            request.urlretrieve(image.url, page_path)
            self.log.debug('Updating progress page number: {page_no}'.format(page_no=page_no))
            progress_bar.update(page_no)
            sleep(1)


class NoSearchResultsError(Exception):
    pass


class ImageResourceUnavailableError(Exception):
    pass