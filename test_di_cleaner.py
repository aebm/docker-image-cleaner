#!/usr/bin/env python

import unittest
import di_cleaner

class TestDockerImageCleanerMethods(unittest.TestCase):

    def test_split_by_none(self):
        image_none = {'dummy': False, u'RepoTags': u'<none>:<none>'}
        image_none_dummy = {'dummy': True, u'RepoTags': u'<none>:<none>'}
        image_non_none = {'dummy': False, u'RepoTags': u'a:b'}
        image_non_none_dummy = {'dummy': False, u'RepoTags': u'c:d'}
        none_images = [image_none_dummy]
        non_none_images = [image_non_none_dummy]
        non_none_images, none_images = di_cleaner.split_by_none(
            non_none_images,
            none_images,
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
            non_none_images,
            none_images,
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


if __name__ == '__main__':
    unittest.main()
