#!/usr/bin/env python

import argparse
import atexit
import logging

DEFAULT_DOCKER_BASE_URL = 'unix://var/run/docker.sock'
HELP_DOCKER_BASE_URL =  ('Refers to the protocol+hostname+port where the '
    'Docker server is hosted. Defaults to %s') % DEFAULT_DOCKER_BASE_URL
DEFAULT_DOCKER_API_VERSION = 'auto'
HELP_DOCKER_API_VERSION =  ('The version of the API the client will use. '
    'Defaults to use the API version provided by the server')
DEFAULT_DOCKER_HTTP_TIMEOUT = 5
HELP_DOCKER_HTTP_TIMEOUT =  ('The HTTP request timeout, in seconds. '
    'Defaults to %d secs') % DEFAULT_DOCKER_HTTP_TIMEOUT
DEFAULT_IMAGES_TO_KEEP = 2
HELP_IMAGES_TO_KEEP =  ('How many docker images to keep. '
    'Defaults to %d images') % DEFAULT_IMAGES_TO_KEEP

def _exit():
    logging.shutdown()

def _debug_dict(name, data):
    [logging.debug('Dict %s has: %s=%s' % (name, k, v)) for k, v in data.iteritems()]

def _setup_parser(parser):
    parser.add_argument('--debug', help='debug mode', action='store_true')
    parser.add_argument('--base-url', help=HELP_DOCKER_BASE_URL, default=DEFAULT_DOCKER_BASE_URL)
    parser.add_argument('--api-version', help=HELP_DOCKER_API_VERSION, default=DEFAULT_DOCKER_API_VERSION)
    parser.add_argument('--http-timeout', help=HELP_DOCKER_HTTP_TIMEOUT, default=DEFAULT_DOCKER_HTTP_TIMEOUT, type=int)
    parser.add_argument('--images-to-keep', help=HELP_IMAGES_TO_KEEP, default=DEFAULT_IMAGES_TO_KEEP, type=int)
    return parser

def _validate_args(args):
    if args.http_timeout < 0:
        raise ValueError('HTTP timeout should be 0 or bigger')
    if args.images_to_keep < 0:
        raise ValueError('Images to keep should be 0 or bigger')

def main():
    atexit.register(func=_exit)
    parser = _setup_parser(argparse.ArgumentParser(description='Clean old docker images'))
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    _debug_dict(name='args', data=vars(args))
    _validate_args(args)

if __name__ == '__main__':
    main()
