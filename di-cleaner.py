#!/usr/bin/env python

import argparse
import atexit
import logging
import sys
from datetime import datetime
from pprint import pformat
from operator import itemgetter
from docker import Client

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
HELP_KEEP_NONE_IMAGES =  'Keep <none> images'
HELP_NOOP =  'Do nothing'
HELP_VERBOSE =  'Print images to delete'

def _exit():
    logging.shutdown()

def debug_var(name, var):
    logging.debug('Var %s has: %s' % (name, pformat(var)))

def setup_parser(parser):
    parser.add_argument('--debug', help='debug mode', action='store_true')
    parser.add_argument('--base-url', help=HELP_DOCKER_BASE_URL, default=DEFAULT_DOCKER_BASE_URL)
    parser.add_argument('--api-version', help=HELP_DOCKER_API_VERSION, default=DEFAULT_DOCKER_API_VERSION)
    parser.add_argument('--http-timeout', help=HELP_DOCKER_HTTP_TIMEOUT, default=DEFAULT_DOCKER_HTTP_TIMEOUT, type=int)
    parser.add_argument('--images-to-keep', help=HELP_IMAGES_TO_KEEP, default=DEFAULT_IMAGES_TO_KEEP, type=int)
    parser.add_argument('--keep-none-images', help=HELP_KEEP_NONE_IMAGES, action='store_true')
    parser.add_argument('--noop', help=HELP_NOOP, action='store_true')
    parser.add_argument('--verbose', help=HELP_VERBOSE, action='store_true')
    return parser

def validate_args(args):
    if args.http_timeout < 0:
        sys.stderr.write('HTTP timeout should be 0 or bigger\n')
        sys.exit(1)
    if args.images_to_keep < 0:
        sys.stderr.write('Images to keep should be 0 or bigger\n')
        sys.exit(1)

def split_by_none((non_none, none), dict_):
    if u'<none>:<none>' in dict_[u'RepoTags']:
        none.append(dict_)
    else:
        non_none.append(dict_)
    return (non_none, none)

def split_images(images):
    return reduce(split_by_none, images, ([], []))

def remove_keys_from_dict(keys, dict_):
    return { k: v for k, v in dict_.iteritems() if k not in keys }

def add_image_to_grp_images(grp_images, image):
    repo, _ = image[u'RepoTags'][0].split(':')
    new_image = remove_keys_from_dict([u'RepoTags'], image)
    new_image[u'Tags'] = [e.split(':')[-1] for e in image[u'RepoTags']]
    if repo in grp_images:
        grp_images[repo].append(new_image)
    else:
        grp_images[repo] = [new_image]
    return grp_images

def group_by_repo(images):
    return reduce(add_image_to_grp_images, images, {})

def reverse_sort_images_created(images):
    return sorted(images, key=itemgetter(u'Created'), reverse=True)

def sort_images_in_repos(repos):
    return { k: reverse_sort_images_created(v) for k, v in repos.iteritems() }

def fix_none_image(image):
    new_image = remove_keys_from_dict([u'RepoTags'], image)
    new_image[u'Tags'] = image[u'RepoTags']
    return new_image

def beautify_image(image):
    new_image = remove_keys_from_dict([u'RepoDigests', u'ParentId', u'Labels'], image)
    new_image[u'Created'] = datetime.fromtimestamp(image[u'Created']).isoformat(' ')
    return new_image

def print_images_to_delete(repos):
    print('Images to delete')
    print(pformat({k: [beautify_image(e) for e in v] for k, v in repos.iteritems()}))

def main():
    atexit.register(func=_exit)
    parser = setup_parser(argparse.ArgumentParser(description='Clean old docker images'))
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    if args.debug:
        debug_var(name='args', var=args)
    validate_args(args)
    client = Client(base_url=args.base_url, version=args.api_version, timeout=args.http_timeout)
    images = client.images()
    if args.debug:
        debug_var(name='images', var=images)
    non_none_images, none_images = split_images(images)
    if args.debug:
        debug_var(name='non_none_images', var=non_none_images)
        debug_var(name='none_images', var=none_images)
    repos = sort_images_in_repos(group_by_repo(non_none_images))
    if args.debug:
        debug_var(name='repos', var=repos)
    to_delete = {}
    if not args.keep_none_images:
        to_delete[u'<none>'] = [fix_none_image(e) for e in none_images]
    if args.debug:
        debug_var(name='to_delete', var=to_delete)
    repos_w_images = {k: v for k, v in repos.iteritems() if len(v) > args.images_to_keep}
    if args.debug:
        debug_var(name='repos_w_images', var=repos_w_images)
    to_delete.update({k: v[args.images_to_keep:] for k, v in repos_w_images.iteritems()})
    if args.debug:
        debug_var(name='to_delete', var=to_delete)
    if args.verbose:
        print_images_to_delete(to_delete)
    if args.noop:
        sys.exit(0)

if __name__ == '__main__':
    main()
