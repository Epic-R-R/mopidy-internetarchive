from __future__ import unicode_literals

import datetime
import logging
import re

__all__ = (
    'parse_bitrate',
    'parse_date',
    'parse_length',
    'parse_mtime',
    'parse_track_no'
)

_DURATION_RE = re.compile(r"""
(?:
    (?:(?P<hours>\d+):)?
    (?P<minutes>\d+):
)?
(?P<seconds>\d+)
""", flags=re.VERBOSE)

_ISODATE_RE = re.compile(r"""
(\d{4})
(?:\-(\d{2}))?
(?:\-(\d{2}))?
""", flags=re.VERBOSE)

logger = logging.getLogger(__name__)


def parse_bitrate(string, default=None):
    if string:
        try:
            return int(float(string))
        except:
            logger.warn('Invalid Internet Archive bitrate: %r', string)
    return default


def parse_date(string, default=None):
    if string:
        try:
            return '-'.join(_ISODATE_RE.match(string).groups('01'))
        except:
            logger.warn('Invalid Internet Archive date: %r', string)
    return default


def parse_length(string, default=None):
    if string:
        try:
            groups = _DURATION_RE.match(string).groupdict('0')
            d = datetime.timedelta(**{k: int(v) for k, v in groups.items()})
            return int(d.total_seconds() * 1000)
        except:
            logger.warn('Invalid Internet Archive length: %r', string)
    return default


def parse_mtime(string, default=None):
    if string:
        try:
            return int(string)
        except:
            logger.warn('Invalid Internet Archive mtime: %r', string)
    return default


def parse_track_no(string, default=None):
    if string:
        try:
            return int(string.partition('/')[0])
        except:
            logger.warn('Invalid Internet Archive track no.: %r', string)
    return default
