import requests
from bs4 import BeautifulSoup
from scrapers import MangaScraper, SeriesMeta


class MangaHere(MangaScraper):
    def __init__(self):
        super().__init__('http://www.mangahere.co/search.php')

    @MangaScraper.series.setter
    def series(self, title):
        # Set up and execute the search request
        search_request = requests.get(self.search_url, params={'name': title})
        search_soup = BeautifulSoup(search_request.content)

        # Pull the first listed result
        results = search_soup.find('div', 'result_search')
        first_result = results.dl
        if not first_result.dt:
            raise self.NoSearchResultsFoundError

        # Search result list data
        name_one = first_result.dt.find('a', 'name_one')
        name_two = first_result.dt.find('a', 'name_two')

        # URL, Title, Chapter Count
        url = name_one['href']
        title = name_one.string
        chapter_count = name_two.string

        # Alt title parsing
        alt_titles = str(first_result.dd.string)
        if alt_titles.startswith('Alternative Name:'):
            alt_titles = alt_titles.replace('Alternative Name:', '')
            alt_titles = [title.strip() for title in alt_titles.split(';')]

        self._series = SeriesMeta(url, title, alt_titles, chapter_count)