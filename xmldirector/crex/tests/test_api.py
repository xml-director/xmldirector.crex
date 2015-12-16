# -*- coding: utf-8 -*-

################################################################
# xmldirector.crex
# (C) 2015,  Andreas Jung, www.zopyx.com, Tuebingen, Germany
################################################################


import json
import requests

from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

from xmldirector.crex.tests.base import TestBase


class TestFilestreamIterator(TestBase):

    def test_create(self):
        response = requests.put(
            self.portal.absolute_url() + '/xmldirector-create',
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        payload = response.json()
        self.assertTrue(response.status_code == 201)
        self.assertTrue('id' in payload)
        id = payload['id']
        url = payload['url']

        response = requests.get(
            '{}/xmldirector-get-metadata?id={}'.format(url, id),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        self.assertTrue(response.status_code == 200)
        payload = response.json()
        self.assertEqual(payload['id'], id)


    def test_set_get_metadata(self):
        response = requests.put(
            self.portal.absolute_url() + '/xmldirector-create',
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        payload = response.json()
        url = payload['url']

        data = dict(
                title=u'hello world',
                description=u'my description',
                custom=dict(a=2, b=42))
        response = requests.post(
            '{}/xmldirector-set-metadata'.format(url),
            data=json.dumps(data),
            headers={'Accept': 'application/json', 'content-type': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        self.assertTrue(response.status_code == 200)

        response = requests.get(
            '{}/xmldirector-get-metadata'.format(url),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        self.assertTrue(response.status_code == 200)
        metadata = response.json()
        self.assertEqual(metadata['title'], data['title'])
        self.assertEqual(metadata['description'], data['description'])
        self.assertEqual(metadata['custom'], data['custom'])
