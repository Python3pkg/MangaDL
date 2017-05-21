import os
from importlib import import_module
from collections import OrderedDict
from abc import ABCMeta, abstractmethod


class ScraperManager:
    """
    Loads and contains all available site scraper classes
    """
    def __init__(self):
        """
        Initialize a new Scraper Manager instance
        """
        self.scrapers = {}
        self._load_all()

    def _load_all(self):
        """
        Load all available scraper sites
        """
        base_dir = os.path.dirname(os.path.realpath(__file__))
        sites_path = os.path.join(base_dir, 'sites')
        contents = os.listdir(sites_path)
        imps = [p.rstrip('.py') for p in contents if not p.startswith('_') and p.endswith('.py')]

        for imp in imps:
            try:
                module = import_module('mangadl.scrapers.sites.{name}'.format(name=imp))
                name, scraper_class = module.Scraper
                self.scrapers[name] = scraper_class
            except ImportError:
                continue


class MangaScraper(metaclass=ABCMeta):
    """
    Manga scraper
    """

    def __init__(self, search_url):
        """
        Initialize a new Manga Scraper instance
        :param search_url: The URL used to submit search queries to
        :type  search_url: str
        """
        self.search_url = search_url
        self._series = NotImplemented

    @property
    def series(self):
        return self._series

    @series.setter
    @abstractmethod
    def series(self, title):
        pass

    # Metadata base classes
    class SeriesMeta(metaclass=ABCMeta):
        """
        Series metadata base class
        """

        def __init__(self, url, title, alt_titles=NotImplemented, chapter_count=NotImplemented):
            """
            Initialize a new Series Meta instance
            :param url: Link to the Manga series
            :type  url: str

            :param title: Title of the Manga series
            :type  title: str

            :param alt_titles: Any alternate titles for the series
            :type  alt_titles: list of str

            :param chapter_count: The total number of chapters in the series
            :type  chapter_count: str
            """
            # Assign the metadata attributes
            self.url = url
            self.title = title
            self.alt_titles = alt_titles
            self.chapter_count = chapter_count
            self._chapters = OrderedDict()

        @abstractmethod
        def _load_chapters(self):
            """
            Load and parse all available chapters for the series
            """
            pass

        @property
        def chapters(self):
            """
            Chapters property
            """
            if self._chapters:
                return self._chapters

            self._load_chapters()
            # Chapters are inserted in backwards order, so we need to reverse the dictionary
            self._chapters = OrderedDict(reversed(list(self._chapters.items())))
            return self._chapters

    class ChapterMeta(metaclass=ABCMeta):
        """
        Chapter metadata base class
        """

        def __init__(self, url, title, chapter, series):
            """
            Initialize a new Chapter Meta instance
            :param url: Link to the chapter
            :type  url: str

            :param title: Title of the chapter
            :type  title: str

            :param chapter: The chapter number
            :type  chapter: str

            :param series: The instantiating SeriesMeta instance
            :type  series: SeriesMeta
            """
            self.url = url
            self.title = title
            self.chapter = chapter
            self.series = series
            self._pages = OrderedDict()

        @abstractmethod
        def _load_pages(self):
            pass

        @property
        def pages(self):
            """
            Chapters property
            """
            if self._pages:
                return self._pages

            self._load_pages()
            return self._pages

    class PageMeta(metaclass=ABCMeta):
        """
        Page metadata base class
        """

        def __init__(self, url, page_no, chapter):
            """
            Initialize a new Page Meta instance
            :param url: Link to the page
            :type  url: str

            :param page_no: The page number
            :type  page_no: str

            :param chapter: The instantiating ChapterMeta instance
            :type  chapter: SeriesMeta
            """
            self.url = url
            self.page = page_no
            self.chapter = chapter
            self._image = None

        @abstractmethod
        def _load_image(self):
            pass

        @property
        def image(self):
            """
            Image property
            """
            if self._image:
                return self._image

            self._load_image()
            return self._image

    class ImageMeta:
        """
        Image metadata base class
        """
        def __init__(self, url, page):
            """
            Initialize a new Image Meta instance
            :param url: Link to the image
            :type  url: str

            :param page: The instantiating PageMeta instance
            :type  page: PageMeta
            """
            self.url = url
            self.page = page
