from __future__ import unicode_literals

import collections
import logging

from mopidy import backend, models

from . import Extension, translator

logger = logging.getLogger(__name__)


class InternetArchiveLibraryProvider(backend.LibraryProvider):

    root_directory = models.Ref.directory(
        uri=translator.uri(''), name='Internet Archive'
    )

    def __init__(self, config, backend):
        super(InternetArchiveLibraryProvider, self).__init__(backend)
        self.__config = ext_config = config[Extension.ext_name]
        self.__browse_filter = '(mediatype:collection OR format:(%s))' % (
            ' OR '.join(map(translator.quote, ext_config['audio_formats']))
        )
        self.__search_filter = 'format:(%s)' % (
            ' OR '.join(map(translator.quote, ext_config['audio_formats']))
        )
        self.__lookup = {}  # track cache for faster lookup

    def browse(self, uri):
        identifier, filename, query = translator.parse_uri(uri)
        if filename:
            return []
        elif query:
            return self.__browse_collection(identifier, **query)
        elif identifier:
            return self.__browse_item(identifier)
        else:
            return self.__browse_root()

    def get_images(self, uris):
        client = self.backend.client
        urimap = collections.defaultdict(list)
        for uri in uris:
            identifier, _, _ = translator.parse_uri(uri)
            if identifier:
                urimap[identifier].append(uri)
            else:
                logger.warn('No images for %s', uri)
        results = {}
        formats = self.__config['image_formats']
        for identifier in urimap:
            item = client.getitem(identifier)
            images = translator.images(item, formats, client.geturl)
            results.update(dict.fromkeys(urimap[identifier], images))
        return results

    def lookup(self, uri):
        try:
            return [self.__lookup[uri]]
        except KeyError:
            logger.debug("Lookup cache miss for %r", uri)
        try:
            identifier, filename, _ = translator.parse_uri(uri)
            tracks = self.__tracks(self.backend.client.getitem(identifier))
            self.__lookup = trackmap = {t.uri: t for t in tracks}
            return [trackmap[uri]] if filename else tracks
        except Exception as e:
            logger.error('Lookup failed for %s: %s', uri, e)
            return []

    def refresh(self, uri=None):
        client = self.backend.client
        if client.cache:
            client.cache.clear()
        self.__lookup.clear()

    def search(self, query=None, uris=None, exact=False):
        # sanitize uris
        uris = set(uris or [self.root_directory.uri])
        if self.root_directory.uri in uris:
            # TODO: from cached root collections?
            uris.update(translator.uri(identifier)
                        for identifier in self.__config['collections'])
            uris.remove(self.root_directory.uri)
        try:
            qs = translator.query(query, uris, exact)
        except ValueError as e:
            logger.info('Not searching %s: %s', Extension.dist_name, e)
            return None
        else:
            logger.debug('Internet Archive query: %s' % qs)
        result = self.backend.client.search(
            '%s AND %s' % (qs, self.__search_filter),
            fields=['identifier', 'title', 'creator', 'date'],
            rows=self.__config['search_limit'],
            sort=self.__config['search_order']
        )
        return models.SearchResult(
            uri=translator.uri(q=result.query),
            albums=map(translator.album, result)
        )

    def __browse_collection(self, identifier, q=[], sort=['downloads desc']):
        if identifier:
            qs = 'collection:%s' % identifier
        else:
            qs = ' AND '.join(q)
        return list(map(translator.ref, self.backend.client.search(
            '%s AND %s' % (qs, self.__browse_filter),
            fields=['identifier', 'title', 'mediatype', 'creator'],
            rows=self.__config['browse_limit'],
            sort=sort
        )))

    def __browse_item(self, identifier):
        item = self.backend.client.getitem(identifier)
        if item['metadata']['mediatype'] != 'collection':
            tracks = self.__tracks(item)
            self.__lookup = {t.uri: t for t in tracks}  # cache tracks
            return [models.Ref.track(uri=t.uri, name=t.name) for t in tracks]
        elif 'members' in item:
            return list(map(translator.ref, item['members']))
        else:
            return self.__views(identifier)

    def __browse_root(self):
        # TODO: cache this
        result = self.backend.client.search(
            'mediatype:collection AND identifier:(%s)' % (
                ' OR '.join(self.__config['collections'])
            ),
            fields=['identifier', 'title', 'mediatype', 'creator']
        )
        refs = []
        objs = {obj['identifier']: obj for obj in result}
        for identifier in self.__config['collections']:
            try:
                obj = objs[identifier]
            except KeyError:
                logger.warn('Internet Archive collection "%s" not found',
                            identifier)
            else:
                refs.append(translator.ref(obj))
        return refs

    def __tracks(self, item, key=lambda t: (t.track_no or 0, t.uri)):
        tracks = translator.tracks(item, self.__config['audio_formats'])
        tracks.sort(key=key)
        return tracks

    def __views(self, identifier):
        refs = []
        for order, name in self.__config['browse_views'].items():
            uri = translator.uri(identifier, sort=order)
            refs.append(models.Ref.directory(name=name, uri=uri))
        return refs
