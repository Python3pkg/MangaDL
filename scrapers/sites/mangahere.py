import requests
from bs4 import BeautifulSoup
from scrapers import MangaScraper


class MangaHere(MangaScraper):
    def __init__(self):
        """
        Initialize a new MangaHere scraper instance
        """
        super().__init__('http://www.mangahere.co/search.php')

    @MangaScraper.series.setter
    def series(self, title):
        """
        Set up and execute the search request
        :param title: Title of the manga series
        :type  title: str
        """
        search_request = requests.get(self.search_url, params={'name': title})
        search_soup = BeautifulSoup(search_request.content)

        # Pull the first listed result
        try:
            results = search_soup.find('div', 'result_search')
            first_result = results.dl
        except AttributeError:
            raise self.NoSearchResultsFoundError

        # Search result list data
        name_one = first_result.dt.find('a', 'name_one')
        name_two = first_result.dt.find('a', 'name_two')

        # URL, Title, Chapter Count
        url = name_one['href']
        title = name_one.string
        chapter_count = name_two.string.lstrip('Ch.')

        # Alt title parsing
        alt_titles = str(first_result.dd.string)
        if alt_titles.startswith('Alternative Name:'):
            alt_titles = alt_titles.replace('Alternative Name:', '')
            alt_titles = [title.strip() for title in alt_titles.split(';')]

        self._series = MangaHere.SeriesMeta(url, title, alt_titles, chapter_count)

    class SeriesMeta(MangaScraper.SeriesMeta):
        """
        Series metadata
        """
        def _load_chapters(self):
            """
            Load and parse all available chapters for the series
            """
            # Set up and execute the Table of Contents request
            toc_request = requests.get(self.url)
            toc_soup = BeautifulSoup(toc_request.content)

            # Get a list of chapters
            detail_list = toc_soup.find('div', 'detail_list').ul
            if not detail_list:
                return
            detail_list = detail_list.find_all('li')

            for detail in detail_list:
                # Parse and set the title
                try:
                    title = detail.find('span', 'mr6').nextSibling.strip()
                except AttributeError:
                    title = 'Untitled'

                # URL and Chapter
                link = detail.find('span', 'left').a
                url = link['href']
                chapter = link.string.strip().split(' ')[-1]

                self._chapters[chapter] = MangaHere.ChapterMeta(url, title, chapter)

    class ChapterMeta(MangaScraper.ChapterMeta):
        """
        Chapter metadata
        """
        def _load_pages(self):
            """
            Load and parse all available pages for the series
            """
            # Set up and execute the pages request for the chapter
            pages_request = requests.get(self.url)
            pages_soup = BeautifulSoup(pages_request.content)

            # Get a list of pages
            go_header = pages_soup.find('div', 'go_page')
            page_list = go_header.find('span', 'right').find('select').find_all('option')

            # Iterate, parse and add the pages
            for page in page_list:
                url = page['value']
                page_no = page.string
                self._pages[page_no] = MangaHere.PageMeta(url, page_no)

    class PageMeta(MangaScraper.PageMeta):
        """
        Page metadata
        """
        def _load_image(self):
            """
            Load and parse a pages image
            """
            # Set up and execute the page request for the chapter
            page_request = requests.get(self.url)
            page_soup = BeautifulSoup(page_request.content)

            # Get the page image link
            image = page_soup.find('section', 'read_img').find('img', id='image')
            self._image = MangaScraper.ImageMeta(image['src'])