# -*- coding: utf-8 -*-
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD

from xmldirector.crex.tests.base import TestBase

import unittest
import requests
import transaction


class TestFilestreamIterator(TestBase):

    def test_create(self):
        response = requests.put(
            self.portal.absolute_url() + '/xmldirector-create',
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD))
        print response
        self.assertTrue(response.status_code == 201)
