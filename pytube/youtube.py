#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
.. module:: pytube.youtube
   :platform: Unix
   :synopsis: Library for downloading YouTube videos

.. moduleauthor:: Nick Ficano <nficano@gmail.com>
"""

from mimetypes import guess_extension
from os.path import join
from urllib import urlencode
from urllib2 import urlopen
from urlparse import urlparse, parse_qs

import re

BASE_URL = 'http://www.youtube.com/get_video_info'

MIMETYPE_RE = re.compile('(video\/[A-Za-z0-9-_]*)')
CODECS_RE = re.compile('.*codecs\=\"(.*)\"')


class YouTube(object):
    """PyTube: Lightweight wrapper for downloading YouTube videos
    """

    def __init__(self, url):
        """
        Initialize class instance.

        :param url: web address to YouTube video
        :type url: str
        """
        self.url = url
        self.video_id = self.get_id_by_url(url)

    def get_id_by_url(self, url):
        """
        Extracts the video Id from a YouTube url.

        :param video_id: YouTube url
        :type video_id: str
        :returns: YouTube video Id
        :rtype: str
        """

        #TODO: raise exception for malformed url, no '?v=xxx' found in query
        #string. Also test on url-shortened youtu.be

        #Split URI into 'parts', check if query string contains node 'v' and
        #return accordingly.
        parts = urlparse(url)
        if hasattr(parts, 'query'):
            qs = self._parse_qs(parts.query)
            return qs.get('v')

    def mget_videos_by_id(self, video_id):
        """
        multi-get returns a list of object representation of YouTube videos for
        a given video Id.

        :param video_id: YouTube video Id
        :type video_id: str
        :returns: Video objects
        :rtype: list
        """
        videos = []
        metadata = self.get_metadata_by_id(video_id)['fmt_stream_map']
        for stream_map in metadata:
            vid = Video(stream_map)
            videos.append(vid)
        return videos

    def get_metadata_by_id(self, video_id):
        """
        Returns the YouTube meta data for a given Id.

        :param video_id: YouTube video Id
        :type video_id: str
        :returns: video meta data
        :rtype: dict
        """

        return self._request(video_id)

    def _url(self, url, *paths, **qs):
        """
        Lazily constructs a url given optional paths and query string as
        keyword args.

        :param url: The base URL (e.g.: http://example.com)
        :type url: str
        :param paths: (optional) Path(s) to append to url (e.g.: /path/to/file)
        :type paths: list
        :param qs: (optional) build query from keyword args (e.g.: ?foo=bar)
        :type qs: dict
        :returns: a formed url
        :rtype: str
        """

        #Store url as list for easier assembly.
        url_parts = [url]

        #TODO: Sanitize paths ensuring slashes are handled properly.
        if isinstance(paths, list):
            paths = join(*paths)
            url_parts.append(paths)

        #TODO: Sanitize query string ensuring no leading '?' or training '&'
        if isinstance(qs, dict):
            qs = '?' + urlencode(qs)
            url_parts.append(qs)

        return ''.join(url_parts)

    def _parse_qs(self, qs):
        """
        Parse a query given as a string argument. (Similar to parse_qs method
        found in urlparse module except this handles the flattening of
        unnecessary tuples.

        :param qs: uri query string
        :type qs: str
        :returns: a flattened dict representation of a query string
        :rtype: dict
        """

        d = dict()
        #loop through object key/value yielded from parse_qs iteritems, check
        #if the value contains one item (no child nodes), replace tuple with
        #strings accordingly.
        for key, val in parse_qs(qs).iteritems():
            d[key] = (val if len(val) > 1 else val[0])
        return d

    def _request(self, video_id):
        """
        Executes request to YouTube v3 service detailpage and handles the
        response, parsing out the meta data and decodes the format stream
        map.

        :param video_id: the YouTube video Id
        :type video_id: str
        :returns: a dict representation of the metadata
        :rtype: dict
        """

        #Assemble URL and execute http request.
        url = self._url(BASE_URL, asv=3, el='detailpage', hl='en_US',
                        video_id=video_id)
        response = urlopen(url)

        if response.getcode() != 200:
            #TODO: raise proper exception if status code is not 200.
            raise

        #Parse the meta data found in the response body using modified version
        #of parse_qs.
        metadata = self._parse_qs(response.read())

        stream_map = [self._parse_qs(fsm) for fsm in
                      metadata['url_encoded_fmt_stream_map'].split(',')]
        for fsm in stream_map:
            fsm.update({'url': '{url}&signature={sig}'.format(**fsm)})

        metadata['fmt_stream_map'] = stream_map
        return metadata


class Video(object):
    """YouTube video instances created by the YouTube factory class.
    """

    def __init__(self, stream_map):
        """Initialize instance of Video class

        :param stream_map: The url decoded fmt_stream_map.
        :type url: dict
        """

        self._raw_stream_map = stream_map
        self.itag = stream_map.get('itag')
        self.url = stream_map.get('url')
        self.quality = stream_map.get('quality')
        self.fallback_host = stream_map.get('fallback_host')

        self.content_type = stream_map.get('type')
        self.mimetype = self._get_mimetype(self.content_type)
        self.codecs = self._get_codecs(self.content_type)

    def _get_mimetype(self, content_type):
        mimetype = MIMETYPE_RE.match(content_type)
        if mimetype:
            return mimetype.group()

    def _get_codecs(self, content_type):
        codecs = CODECS_RE.match(content_type)
        if codecs:
            return codecs.group()

    def __repr__(self):
        return '<Video: "{mimetype}" quality: {quality}>'.format(
            mimetype=self.mimetype, quality=self.quality)


if __name__ == '__main__':
    from pprint import pprint
    yt = YouTube("http://www.youtube.com/watch?v=Ik-RsDGPI5Y")
    video_id = yt.video_id
    print yt.mget_videos_by_id(video_id)
