#!/usr/bin/env python

import argparse
import atexit
import logging

DEFAULT_DOCKER_BASE_URL = 'unix://var/run/docker.sock'
DOCKER_BASE_URL_HELP =  ('Refers to the protocol+hostname+port where the '
    'Docker server is hosted. Defaults to %s') % DEFAULT_DOCKER_BASE_URL
DEFAULT_DOCKER_API_VERSION = 'auto'
DOCKER_API_VERSION_HELP =  ('The version of the API the client will use. '
    'Defaults to use the API version provided by the server')
DEFAULT_DOCKER_HTTP_TIMEOUT = 5
DOCKER_HTTP_TIMEOUT_HELP =  ('The HTTP request timeout, in seconds. '
    'Defaults to %d secs') % DEFAULT_DOCKER_HTTP_TIMEOUT

def _exit():
    logging.shutdown()

def main():
    atexit.register(func=_exit)
    parser = argparse.ArgumentParser(description='Clean old docker images')
    parser.add_argument('--debug', help='debug mode', action='store_true')
    parser.add_argument('--base-url', help=DOCKER_BASE_URL_HELP, default=DEFAULT_DOCKER_BASE_URL)
    parser.add_argument('--api-version', help=DOCKER_API_VERSION_HELP, default=DEFAULT_DOCKER_API_VERSION)
    parser.add_argument('--http-timeout', help=DOCKER_HTTP_TIMEOUT_HELP, default=DEFAULT_DOCKER_HTTP_TIMEOUT, type=int)
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    main()
