# -*- coding: utf-8 -*-

################################################################
# xmldirector.crex
# (C) 2015,  Andreas Jung, www.zopyx.com, Tuebingen, Germany
################################################################

import os
import time
import datetime
import tempfile
import requests

import plone.api
from zope.component import getUtility
from zope.component import queryUtility
from plone.registry.interfaces import IRegistry

from xmldirector.crex.logger import LOG
from xmldirector.crex.interfaces import ICRexSettings


class CRexConversionError(Exception):
    pass


def convert_crex(zip_path):
    """ Send ZIP archive with content to be converted to C-Rex """

    registry = getUtility(IRegistry)
    settings = registry.forInterface(ICRexSettings)

    # Fetch authentication token if necessary (older than one hour)
    crex_token = settings.crex_conversion_token
    crex_token_last_fetched = settings.crex_conversion_token_last_fetched or datetime.datetime(
        2000, 1, 1)
    diff = datetime.datetime.utcnow() - crex_token_last_fetched
    if not crex_token or diff.total_seconds() > 3600:
        LOG.info('Fetching new DOCX authentication token')
        # get conversion token
        token_url = '{}/api/Token'.format(settings.crex_conversion_url)
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        params = dict(
            username=settings.crex_conversion_username,
            password=settings.crex_conversion_password,
            grant_type='password')
        result = requests.post(token_url, data=params, headers=headers)
        if result.status_code != 200:
            msg = u'Error retrieving DOCX conversion token from webservice (HTTP code {}, Message {})'.format(
                result.status_code, result.text)
            LOG.error(msg)
            raise CRexConversionError(msg)

        data = result.json()
        crex_token = data['access_token']

        settings.crex_conversion_token = crex_token
        settings.crex_conversion_token_last_fetched = datetime.datetime.utcnow()
        LOG.info('Fetching new DOCX authentication token - successful')
    else:
        LOG.info('Fetching DOCX authentication token from Plone cache')

    conversion_url = '{}/api/XBot/Convert/DGHO/docxMigration'.format(
        settings.crex_conversion_url)
    headers = {'authorization': 'Bearer {}'.format(crex_token)}

    with open(zip_path, 'rb') as fp:
        try:
            result = requests.post(
                conversion_url, files=dict(source=fp), headers=headers)
        except requests.ConnectionError:
            msg = u'Connection to C-REX webservice failed'
            raise CRexConversionError(msg)

        if result.status_code == 200:
            msg = u'Conversion successful (HTTP code {}))'.format(result.status_code)
            LOG.info(msg)
            zip_out = tempfile.mktemp(suffix='.zip')
            with open(zip_out, 'wb') as fp:
                fp.write(result.content)
            return zip_out

        else:
            # Forbidden -> invalid token -> invalidate token stored in
            # Plone
            if result.status_code == 401:
                settings.crex_conversion_token = u''
                settings.crex_conversion_token_last_fetched = datetime.datetime(
                    1999, 1, 1)

            msg = u'Conversion failed (HTTP code {}, message {})'.format(
                result.status_code, result.text)
            LOG.error(msg)
            raise CRexConversionError(msg)

