from __future__ import unicode_literals

import collections
import requests
import uritools

BASE_URL = 'http://archive.org/'


class InternetArchiveClient(object):

    pykka_traversable = True

    def __init__(self, base_url=BASE_URL, timeout=None):
        self.search_url = uritools.urijoin(base_url, '/advancedsearch.php')
        self.metadata_url = uritools.urijoin(base_url, '/metadata/')
        self.download_url = uritools.urijoin(base_url, '/download/')
        self.bookmarks_url = uritools.urijoin(base_url, '/bookmarks/')
        self.session = requests.Session()
        self.timeout = timeout

    def search(self, query, fields=None, sort=None, rows=None, start=None):
        response = self.session.get(self.search_url, params={
            'q': query,
            'fl[]': fields,
            'sort[]': sort,
            'rows': rows,
            'start': start,
            'output': 'json'
        }, timeout=self.timeout)
        if not response.content:
            raise self.SearchError(response.url)
        return self.SearchResult(response.json())

    def metadata(self, path):
        url = uritools.urijoin(self.metadata_url, path.lstrip('/'))
        response = self.session.get(url, timeout=self.timeout)
        data = response.json()

        if not data:
            raise LookupError('Internet Archive item %s not found' % path)
        elif 'error' in data:
            raise LookupError(data['error'])
        elif 'result' in data:
            return data['result']
        else:
            return data

    def bookmarks(self, username):
        url = uritools.urijoin(self.bookmarks_url, username + '?output=json')
        response = self.session.get(url, timeout=self.timeout)
        # requests for non-existant users yield text/xml response
        if response.headers['Content-Type'] != 'application/json':
            raise LookupError('Internet Archive user %s not found' % username)
        return response.json()

    def geturl(self, identifier, filename=None):
        if filename:
            ref = identifier + '/' + uritools.uriencode(filename)
        else:
            ref = identifier + '/'
        return uritools.urijoin(self.download_url, ref)

    class SearchResult(collections.Sequence):

        def __init__(self, result):
            self.query = result['responseHeader']['params']['q']
            self.rowcount = result['response']['numFound']
            self.docs = result['response']['docs']

        def __getitem__(self, key):
            return self.docs[key]

        def __len__(self):
            return len(self.docs)

        def __iter__(self):
            return iter(self.docs)

    class SearchError(Exception):
        pass
