# -*- coding: utf-8 -*-

################################################################
# xmldirector.crex
# (C) 2015,  Andreas Jung, www.zopyx.com, Tuebingen, Germany
################################################################


import os
import json
import requests

from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

from xmldirector.crex.tests.base import TestBase


class TestFilestreamIterator(TestBase):

    def _make_one(self):
        response = requests.put(
            self.portal.absolute_url() + '/xmldirector-create',
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        self.portal._p_jar.sync()
        return response

    def test_create(self):
        response = self._make_one()
        self.assertTrue(response.status_code == 201)
        payload = response.json()
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
        response = self._make_one()
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

    
    def test_store_get(self):

        response = self._make_one()
        self.assertTrue(response.status_code == 201)
        url = response.json()['url']

        cwd = os.path.dirname(__file__)
        files = [('files', ('src/dummy/sample.docx', open(os.path.join(cwd, 'sample.docx'), 'rb'), 'application/zip')),
                 ('files', ('src/dummy/sample.txt', open(os.path.join(cwd, 'sample.txt'), 'rb'), 'text/plain'))]

        response = requests.post(
            '{}/xmldirector-store-single'.format(url),
            files=files,
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        self.assertTrue(response.status_code == 200)

        response = requests.get(
            '{}/xmldirector-get-single'.format(url),
            params=dict(name='DOES.NOT.EXIST'),
            headers={'Accept': 'application/json', 'content-type': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        self.assertTrue(response.status_code == 404)

        response = requests.get(
            '{}/xmldirector-get-single'.format(url),
            params=dict(name='src/dummy/sample.docx'),
            headers={'Accept': 'application/json', 'content-type': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        self.assertTrue(response.status_code == 200)

        data = response.content
        with open(os.path.join(cwd, 'sample.docx'), 'rb') as fp:
            docx_data = fp.read()
        self.assertTrue(data==docx_data)
