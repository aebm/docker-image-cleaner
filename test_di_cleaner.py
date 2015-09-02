#!/usr/bin/env python

import unittest
import di_cleaner
from datetime import datetime
from humanfriendly import format_size


class TestDockerImageCleanerMethods(unittest.TestCase):

    def test_split_by_none(self):
        image_none = {'dummy': False, u'RepoTags': u'<none>:<none>'}
        image_none_dummy = {'dummy': True, u'RepoTags': u'<none>:<none>'}
        image_non_none = {'dummy': False, u'RepoTags': u'a:b'}
        image_non_none_dummy = {'dummy': False, u'RepoTags': u'c:d'}
        none_images = [image_none_dummy]
        non_none_images = [image_non_none_dummy]
        non_none_images, none_images = di_cleaner.split_by_none(
            (non_none_images, none_images),
            image_none)
        self.assertIn(
            image_none,
            none_images,
            msg='None image should be in none_images list')
        self.assertIn(
            image_none_dummy,
            none_images,
            msg='It is not preserving the none_images passed')
        self.assertNotIn(
            image_none,
            non_none_images,
            msg='None image should not be in non_none_images list')
        non_none_images, none_images = di_cleaner.split_by_none(
            (non_none_images, none_images),
            image_non_none)
        self.assertIn(
            image_non_none,
            non_none_images,
            msg='Non one image should be in non_none_images list')
        self.assertIn(
            image_non_none_dummy,
            non_none_images,
            msg='It is not preserving the non_none_images passed')
        self.assertNotIn(
            image_non_none,
            none_images,
            msg='Non None image should not be in none_images list')
        with self.assertRaises(TypeError):
            di_cleaner.split_by_none(non_none_images, image_non_none)
        with self.assertRaises(ValueError):
            di_cleaner.split_by_none((non_none_images,), image_non_none)
            di_cleaner.split_by_none((non_none_images, none_images,
                                      none_images), image_non_none)

    def test_split_images(self):
        images = [{'id': id_, u'RepoTags': u'<none>:<none>'}
                  for id_ in range(2)]
        images.append({'id': 2, u'RepoTags': u'<alfa>:<omega>'})
        non_none_images, none_images = di_cleaner.split_images(images)
        self.assertEqual(len(non_none_images), 1,
                         msg='non_none_images should have one element')
        self.assertEqual(len(none_images), 2,
                         msg='none_images should have two elements')

    def test_remove_keys_from_dict(self):
        dict_ = {i: i for i in range(5)}
        target_dict = {i: i for i in range(5) if i in [1, 3]}
        new_dict = di_cleaner.remove_keys_from_dict([0, 2, 4], dict_)
        self.assertEqual(new_dict, target_dict,
                         msg='Did not get expected dict')

    def test_add_image_to_grp_images(self):
        grp_images = {u'a': [{u'Id': u'0', u'RepoTags': [u'a:0', u'a:1']}]}
        image_1 = {u'Id': u'1', u'RepoTags': [u'a:2', u'a:3']}
        image_2 = {u'Id': u'2', u'RepoTags': [u'b:0', u'b:1']}
        exp_a_images = [{u'Id': u'0', u'RepoTags': [u'a:0', u'a:1']},
                        image_1]
        exp_b_images = [image_2]
        grp_images = di_cleaner.add_image_to_grp_images(grp_images, image_1)
        self.assertIn(u'a', grp_images, msg='It should not remove repos')
        self.assertEqual(grp_images[u'a'], exp_a_images,
                         msg='This is not expected')
        grp_images = di_cleaner.add_image_to_grp_images(grp_images, image_2)
        self.assertIn(u'a', grp_images, msg='It should keep repo a')
        self.assertIn(u'b', grp_images, msg='It should have repo b')
        self.assertEqual(grp_images[u'b'], exp_b_images,
                         msg='This was not expected')

    def test_group_by_repo(self):
        images = [
            {u'Id': u'0', u'RepoTags': [u'a:0', u'a:1']},
            {u'Id': u'2', u'RepoTags': [u'b:0', u'b:1']},
            {u'Id': u'1', u'RepoTags': [u'a:2', u'a:3']}
        ]
        exp_grouped = {u'a': [
                {u'Id': u'0', u'RepoTags': [u'a:0', u'a:1']},
                {u'Id': u'1', u'RepoTags': [u'a:2', u'a:3']}],
            u'b': [
                {u'Id': u'2', u'RepoTags': [u'b:0', u'b:1']}]}
        grouped = di_cleaner.group_by_repo(images)
        self.assertEqual(grouped, exp_grouped, msg='This was not expected')

    def test_reverse_sort_images_created(self):
        images = [
            {u'Id': '2', u'Created': 2},
            {u'Id': '1', u'Created': 1},
            {u'Id': '3', u'Created': 3}
        ]
        exp_images = [
            {u'Id': '3', u'Created': 3},
            {u'Id': '2', u'Created': 2},
            {u'Id': '1', u'Created': 1}
        ]
        self.assertEqual(di_cleaner.reverse_sort_images_created(images),
                         exp_images, msg='The images are in the wrong order')

    def test_sort_images_in_repos(self):
        repos = {
            u'a': [
                {u'Id': '2', u'Created': 2},
                {u'Id': '1', u'Created': 1},
                {u'Id': '3', u'Created': 3}
            ],
            u'b': [
                {u'Id': '4', u'Created': 4},
                {u'Id': '5', u'Created': 5}
            ]
        }
        exp_repos = {
            u'a': [
                {u'Id': '3', u'Created': 3},
                {u'Id': '2', u'Created': 2},
                {u'Id': '1', u'Created': 1}
            ],
            u'b': [
                {u'Id': '5', u'Created': 5},
                {u'Id': '4', u'Created': 4}
            ]
        }
        self.assertEqual(di_cleaner.sort_images_in_repos(repos), exp_repos,
                         msg='The images are in the wrong order')

    def test_beautify_image(self):
        image = {
            u'Id': u'1',
            u'RepoDigests': 'digest',
            u'ParentId': u'0',
            u'Labels': 'labels',
            u'Created': 1441050417,
            u'Size': 1048576,
            u'VirtualSize': 1024
        }
        exp_image = {
            u'Id': u'1',
            u'Created': datetime.fromtimestamp(
                image[u'Created']).isoformat(' '),
            u'Size': format_size(image[u'Size']),
            u'VirtualSize': format_size(image[u'VirtualSize'])
        }
        self.assertEqual(di_cleaner.beautify_image(image), exp_image,
                         msg='Unexpected result')

    def test_get_images_to_delete(self):
        none_images = [{u'Id': u'0', u'RepoTags': [u'<none>:<none>']},
                       {u'Id': u'1', u'RepoTags': [u'<none>:<none>']}]
        repos = {
            u'a': [
                {u'Id': '4', u'Created': 4, u'RepoTags': [u'a:4']},
                {u'Id': '3', u'Created': 3, u'RepoTags': [u'a:3']},
                {u'Id': '2', u'Created': 2, u'RepoTags': [u'a:2']}
            ],
            u'b': [
                {u'Id': '6', u'Created': 6, u'RepoTags': [u'b:6']},
                {u'Id': '5', u'Created': 5, u'RepoTags': [u'b:5']}
            ]
        }
        exp_1 = [{u'Id': '2', u'Created': 2, u'RepoTags': [u'a:2']}]
        self.assertEqual(
            di_cleaner.get_images_to_delete(none_images, repos, 2, True),
            exp_1, msg='Unexpected result')
        exp_2 = [image for image in none_images]
        exp_2.extend(exp_1)
        self.assertEqual(
            di_cleaner.get_images_to_delete(none_images, repos, 2, False),
            exp_2, msg='Unexpected result')


if __name__ == '__main__':
    unittest.main()
