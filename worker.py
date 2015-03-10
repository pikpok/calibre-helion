from threading import Thread

from lxml.html import fromstring, tostring
import re, datetime

from calibre.ebooks.metadata.book.base import Metadata
from calibre.utils.cleantext import clean_ascii_chars
from calibre.ebooks.metadata import MetaInformation, check_isbn
from calibre.ebooks.metadata.sources.base import fixcase, fixauthors, cap_author_token

class Worker(Thread):

	def __init__(self, url, result_queue, browser, log, relevance, plugin, timeout=20):
		Thread.__init__(self)
		self.daemon = True
		self.url, self.result_queue = url[0], result_queue
		self.log, self.timeout = log, timeout
		self.relevance, self.plugin = relevance, plugin
		self.browser = browser.clone_browser()
		self.cover_url = self.helion_id = self.isbn = None

	def run(self):
		raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
		root = fromstring(clean_ascii_chars(raw))

		helion_id = re.search('ksiazki/(.*).htm', self.url).groups(0)[0]

		title = unicode(root.xpath('//div[@class="book_title"]/h1/span/text()')[0])

		author_node = root.xpath('///div[@class="book_title"]/p/descendant::text()')
		authors = []
		for i in range(1, len(author_node), 2):
			authors.append(unicode(author_node[i]))
		print(authors)

		mi = Metadata(title,authors)
		
		mi.set_identifier('helion', helion_id)
		self.helion_id = helion_id

		#TODO: parse series

		isbn = re.search(', (\d{13})$', root.xpath('//li[@itemprop="isbn"]/text()')[0])
		if not isbn:
			isbn = re.search(', (\d{10})$', root.xpath('//li[@itemprop="isbn"]/text()')[0])
		mi.isbn = self.isbn = isbn.groups(0)[0]

		mi.rating = 5*float(root.xpath('//span[@itemprop="ratingValue"]/text()')[0])/6

		#TODO: parse comments
		#TODO: parse tags
		
		self.cover_url = self.parse_cover(helion_id)
		mi.has_cover = bool(self.cover_url)

		mi.publisher = 'Helion'

		date = root.xpath('//div[@id="center-body-szczegoly"]/ul/li[contains(text(),"drukowanej")]/text()')[1]
		year = int(re.search(': (\d{4})-', date).groups(0)[0])
		month = int(re.search('-(\d{2})-', date).groups(0)[0])
		day = int(re.search('-(\d{2})$', date).groups(0)[0])
		mi.pubdate = datetime.datetime(year, month, day)

		mi.languages = ["pol"]

		self.plugin.cache_isbn_to_identifier(self.isbn, self.helion_id)
		self.plugin.cache_identifier_to_cover_url(self.helion_id, self.cover_url)

		mi.source_relevance = self.relevance
		self.clean_downloaded_metadata(mi)
		self.result_queue.put(mi)

	def parse_cover(self, helion_id):
		url = 'http://helion.pl/okladki/326x466/%s.jpg'%self.helion_id
		info = self.browser.open_novisit(url, timeout=self.timeout).info()
		if int(info.getheader('Content-Length')) > 1000:
			return url
		else:
			self.log.warning('Nie ma okladki: %s'%url)

	def clean_downloaded_metadata(self, mi):
		mi.authors = fixauthors(mi.authors)
		mi.tags = list(map(fixcase, mi.tags))
	 	mi.isbn = check_isbn(mi.isbn)