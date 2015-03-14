#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

import time

from urllib import quote
from lxml.html import fromstring, tostring

from calibre.ebooks.metadata.sources.base import Source
from calibre import browser, url_slash_cleaner
from calibre.utils.cleantext import clean_ascii_chars

class Helion(Source):

    name = 'Helion'
    description = _('Pobiera metadane z helion.pl')
    author = 'pikpok'
    supported_platforms = ['windows', 'osx', 'linux']
    version = (0, 0, 4)
    minimum_calibre_version = (0, 8, 0)

    capabilities = frozenset(['identify', 'cover'])
    touched_fields = frozenset(['title', 'authors', 'identifier:helion',
        'identifier:isbn', 'rating', 'publisher', 'pubdate', 'languages'])
    supports_gzip_transfer_encoding = True

    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30):
        matches = []
        br = self.browser
        q = ''

        title_tokens = list(self.get_title_tokens(title, strip_joiners=False, strip_subtitle=True))
        if title_tokens:
            tokens = [quote(t.encode('iso-8859-2')) for t in title_tokens]
            q += '+'.join(tokens)

        if authors:
            authors_tokens = self.get_author_tokens(authors, only_first_author=True)
            if authors_tokens:
                q += '+'
                tokens = [quote(t.encode('iso-8859-2')) for t in authors_tokens]
            q += '+'.join(tokens)

        query = 'http://helion.pl/search?qa=&szukaj=%s&sortby=wd&wsprzed=1&wprzyg=1&wyczerp=1&sent=1'%(q)

        response = br.open_novisit(query, timeout=timeout)
        raw = response.read().strip()

        root = fromstring(clean_ascii_chars(raw))
        results = root.xpath('*//div[contains(@class,"search-helion")]')

        for result in results:
            book_url = result.xpath('./a[contains(@href,"ksiazki")]/@href')
            matches.append(book_url)

        from calibre_plugins.helion.worker import Worker
        workers = [Worker(url, result_queue, br, log, i, self) for i, url in enumerate(matches) if url]
        for w in workers:
            w.start()
            time.sleep(0.1)
        while not abort.is_set():
            a_worker_is_alive = False
            for w in workers:
                w.join(0.2)
                if abort.is_set():
                    break
                if w.is_alive():
                    a_worker_is_alive = True
            if not a_worker_is_alive:
                break
        return None

    def download_cover(self, log, result_queue, abort, title = None, authors = None, identifiers = {}, timeout = 30, get_best_cover = False):
        url = self.get_cached_cover_url(identifiers = identifiers)
        br = self.browser
        try:
            cdata = br.open_novisit(url, timeout=timeout).read()
            result_queue.put((self, cdata))
        except:
            log.exception('Failed to download cover from:', url)

    def get_cached_cover_url(self, identifiers):
        url = None
        helion_id = identifiers.get('helion')
        if helion_id is not None:
            url = 'http://helion.pl/okladki/326x466/%s.jpg'%(helion_id)
        return url

if __name__ == '__main__':
    '''
    Tests
    '''
    from calibre.ebooks.metadata.sources.test import (test_identify_plugin, title_test, authors_test)
    test_identify_plugin(Helion.name,
        [
        (
            {
            'title':'Ruby on Rails. Wprowadzenie',
            'authors':['Bruce A. Tate & Curt Hibbs']
            },
            [
            title_test('Ruby on Rails. Wprowadzenie'),
            authors_test(['Bruce A. Tate', 'Curt Hibbs'])
            ]
        )
        ]
    )
    test_identify_plugin(Helion.name,
        [
        (
            {
            'title':u'Jak pozostać anonimowym w sieci',
            'authors':[u'Radosław Sokół']
            },
            [
            title_test(u'Jak pozostać anonimowym w sieci'),
            authors_test([u'Radosław Sokół'])
            ]
        )
        ]
    )
