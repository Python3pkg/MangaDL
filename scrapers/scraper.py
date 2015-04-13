from abc import ABCMeta, abstractmethod


class MangaScraper:
    """
    Manga scraper
    """
    __metaclass__ = ABCMeta

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

    # Exceptions
    class NoSearchResultsFoundError(Exception):
        pass


class SeriesMeta:
    """
    Series metadata
    """
    def __init__(self, url, title, alt_titles=NotImplemented, chapter_count=NotImplemented):
        """
        Initialize a new Series Meta instance
        :param url: Link to the Manga series
        :type  url: str

        :param title: The title of the Manga series
        :type  title: str

        :param alt_titles: Any alternate titles for the series
        :type  alt_titles: list of str

        :param chapter_count: The total number of chapters in the series
        :type  chapter_count: int or float
        """
        # Assign the metadata attributes
        self.url = url
        self.title = title
        self.alt_titles = alt_titles
        self.chapter_count = chapter_count