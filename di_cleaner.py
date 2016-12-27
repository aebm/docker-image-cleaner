#!/usr/bin/env python

import argparse
import atexit
import logging
import sys
from datetime import datetime
from functools import partial, reduce
from itertools import groupby
from pprint import pformat
from operator import itemgetter
from docker import DockerClient
from humanfriendly import format_size

DEFAULT_DOCKER_BASE_URL = 'unix://var/run/docker.sock'
HELP_DOCKER_BASE_URL = (
    'Refers to the protocol+hostname+port where the '
    'Docker server is hosted. Defaults to %s') % DEFAULT_DOCKER_BASE_URL
DEFAULT_DOCKER_API_VERSION = 'auto'
HELP_DOCKER_API_VERSION = (
    'The version of the API the client will use. '
    'Defaults to use the API version provided by the server')
DEFAULT_DOCKER_HTTP_TIMEOUT = 5
HELP_DOCKER_HTTP_TIMEOUT = (
    'The HTTP request timeout, in seconds. '
    'Defaults to %d secs') % DEFAULT_DOCKER_HTTP_TIMEOUT
DEFAULT_IMAGES_TO_KEEP = 2
HELP_IMAGES_TO_KEEP = (
    'How many docker images to keep. '
    'Defaults to %d images') % DEFAULT_IMAGES_TO_KEEP
HELP_KEEP_NONE_IMAGES = 'Keep <none> images'
HELP_NOOP = 'Do nothing'
HELP_VERBOSE = 'Print images to delete'


def _exit():
    logging.shutdown()


def is_debug_on():
    return logging.getLogger().getEffectiveLevel() == logging.DEBUG


def debug_var(debug, name, var):
    if debug:
        logging.debug('Var %s has: %s' % (name, pformat(var)))


def setup_parser(parser):
    parser.add_argument('--debug', help='debug mode', action='store_true')
    parser.add_argument(
        '--base-url',
        help=HELP_DOCKER_BASE_URL,
        default=DEFAULT_DOCKER_BASE_URL)
    parser.add_argument(
        '--api-version',
        help=HELP_DOCKER_API_VERSION,
        default=DEFAULT_DOCKER_API_VERSION)
    parser.add_argument(
        '--http-timeout',
        help=HELP_DOCKER_HTTP_TIMEOUT,
        default=DEFAULT_DOCKER_HTTP_TIMEOUT,
        type=int)
    parser.add_argument(
        '--images-to-keep',
        help=HELP_IMAGES_TO_KEEP,
        default=DEFAULT_IMAGES_TO_KEEP,
        type=int)
    parser.add_argument(
        '--keep-none-images',
        help=HELP_KEEP_NONE_IMAGES,
        action='store_true')
    parser.add_argument('--noop', help=HELP_NOOP, action='store_true')
    parser.add_argument('--verbose', help=HELP_VERBOSE, action='store_true')
    return parser


def validate_args(args):
    checks = [
        (lambda args: args.http_timeout < 0,
         'HTTP timeout should be 0 or bigger\n'),
        (lambda args: args.images_to_keep < 0,
         'Images to keep should be 0 or bigger\n')]
    if [sys.stderr.write(msg) for checker, msg in checks if checker(args)]:
        sys.exit(1)


def split_by_none(images_lists, image):
    if not isinstance(images_lists, tuple):
        raise TypeError('First argument should be a tuple')
    non_none_images, none_images = images_lists
    if image[u'RepoTags'] is None or u'<none>:<none>' in image[u'RepoTags']:
        none_images.append(image)
    else:
        non_none_images.append(image)
    return (non_none_images, none_images)


def split_images(images):
    return reduce(split_by_none, images, ([], []))


def remove_keys_from_dict(keys, dict_):
    return {k: v for k, v in dict_.items() if k not in keys}


def add_image_to_grp_images(grp_images, image):
    repos = sorted([e.split(':')[0] for e in image[u'RepoTags']])
    for repo, _ in groupby(repos):
        if repo in grp_images:
            grp_images[repo].append(image)
        else:
            grp_images[repo] = [image]
    return grp_images


def group_by_repo(images):
    return reduce(add_image_to_grp_images, images, {})


def reverse_sort_images_created(images):
    return sorted(images, key=itemgetter(u'Created'), reverse=True)


def sort_images_in_repos(repos):
    return {k: reverse_sort_images_created(v) for k, v in repos.items()}


def beautify_image(image):
    new_image = remove_keys_from_dict(
        [u'RepoDigests', u'ParentId', u'Labels'],
        image)
    new_image[u'Created'] = datetime.fromtimestamp(
        image[u'Created']).isoformat(' ')
    new_image[u'Size'] = format_size(image[u'Size'])
    new_image[u'VirtualSize'] = format_size(image[u'VirtualSize'])
    return new_image


def print_images_to_delete(images):
    print('Images to delete')
    print(pformat([beautify_image(image) for image in images]))


def remove_docker_image(client, image_id, verbose):
    try:
        if verbose:
            print("Removing {}".format(image_id))
        client.images.remove(image_id)
    except Exception as e:
        if verbose:
            print(e)


def delete_images(client, images, verbose):
    [remove_docker_image(client, image[u'Id'], verbose) for image in images]


def get_images_to_delete(none_images, repos, num_images_to_keep, keep_nones):
    images_to_delete = []
    if not keep_nones:
        images_to_delete.extend(none_images)
    [images_to_delete.extend(repo_images[num_images_to_keep:])
     for repo_images in repos.values()
     if len(repo_images) > num_images_to_keep]
    return images_to_delete


def _build_docker_client(args):
    if _is_osx_platform():
        return _macosx_docker_client(args)
    else:
        return _default_docker_client(args)


def _macosx_docker_client(args):
    from docker.utils import kwargs_from_env
    kwargs = kwargs_from_env()
    # Read http://docker-py.readthedocs.org/en/latest/boot2docker/
    kwargs['tls'].assert_hostname = False

    kwargs['version'] = args.api_version
    kwargs['timeout'] = args.http_timeout
    return Client(**kwargs)


def _default_docker_client(args):
    return DockerClient(base_url=args.base_url,
                  version=args.api_version,
                  timeout=args.http_timeout)


def _is_osx_platform():
    from sys import platform as _platform
    return "darwin" in _platform


def main():
    atexit.register(_exit)
    parser = setup_parser(argparse.ArgumentParser(
        description='Clean old docker images'))
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    debug = partial(debug_var, debug=is_debug_on())
    debug(name='args', var=args)
    validate_args(args)
    client = _build_docker_client(args)
    images = [i.attrs for i in client.images.list(all=True)]
    debug(name='images', var=images)
    non_none_images, none_images = split_images(images)
    debug(name='non_none_images', var=non_none_images)
    debug(name='none_images', var=none_images)
    repos = sort_images_in_repos(group_by_repo(non_none_images))
    debug(name='repos', var=repos)
    images_to_delete = get_images_to_delete(
        none_images, repos, args.images_to_keep, args.keep_none_images)
    debug(name='images_to_delete', var=images_to_delete)
    if args.verbose:
        print_images_to_delete(images_to_delete)
    if args.noop:
        sys.exit(0)
    delete_images(client, images_to_delete, args.verbose)

if __name__ == '__main__':
    main()
