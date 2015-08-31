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
        grp_images = {u'a': [{u'Id': u'0', u'Tags': [u'0', u'1']}]}
        image_1 = {u'Id': u'1', u'RepoTags': [u'a:2', u'a:3']}
        image_2 = {u'Id': u'2', u'RepoTags': [u'b:0', u'b:1']}
        exp_a_images = [{u'Id': u'0', u'Tags': [u'0', u'1']},
                        {u'Id': u'1', u'Tags': [u'2', u'3']}]
        exp_b_images = [{u'Id': u'2', u'Tags': [u'0', u'1']}]
        grp_images = di_cleaner.add_image_to_grp_images(grp_images, image_1)
        self.assertIn(u'a', grp_images, msg='It should not remove repos')
        self.assertEqual(grp_images[u'a'], exp_a_images,
                         msg='This is not expected')
        grp_images = di_cleaner.add_image_to_grp_images(grp_images, image_2)
        self.assertIn(u'a', grp_images, msg='It should keep repo a')
        self.assertIn(u'b', grp_images, msg='It should have repo b')
        self.assertEqual(grp_images[u'b'], exp_b_images,
                         msg='This is not expected')


if __name__ == '__main__':
    unittest.main()
