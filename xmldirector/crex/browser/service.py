# -*- coding: utf-8 -*-

################################################################
# xmldirector.crex
# (C) 2015,  Andreas Jung, www.zopyx.com, Tuebingen, Germany
################################################################


import os
import json
import time
import furl
import uuid
import hashlib
import datetime
import tempfile
import requests
import fnmatch
import mimetypes
import fs.zipfs
from contextlib import contextmanager

import plone.api
import zExceptions
from plone.rest import Service
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.annotation.interfaces import IAnnotations
from zope.interface import implements
from AccessControl import Unauthorized
from AccessControl import getSecurityManager
from Products.CMFCore import permissions
from ZPublisher.Iterators import filestream_iterator
from ZPublisher.Iterators import IStreamIterator

from xmldirector.crex.logger import LOG
from xmldirector.crex.interfaces import ICRexSettings
from xmldirector.plonecore.interfaces import IWebdavHandle
from xmldirector.plonecore.connector import IConnector
from zopyx.plone.persistentlogger.logger import IPersistentLogger

from collective.taskqueue import taskqueue


ANNOTATION_KEY = 'xmldirector.plonecore.crex'
SRC_PREFIX = 'src'


class CRexConversionError(Exception):
    """ A generic C-Rex error """


def check_permission(permission, context):
    """ Check the given Zope permission against a context object """

    if not getSecurityManager().checkPermission(permission, context):
        raise Unauthorized(
            'You don\'t have the \'{}\' permission'.format(permission))


def decode_json_payload(request):
    """ Extract JSON data from the body of a Zope request """

    body = getattr(request, 'BODY', '') or '{}'

    try:
        return json.loads(body)
    except ValueError:
        raise ValueError(u'Request body could not be decoded as JSON')


def sha256_fp(fp, blocksize=2 ** 20):
    """ Calculate SHA256 hash for an open file(handle) """

    fp.seek(0)
    sha256 = hashlib.sha256()
    while True:
        data = fp.read(blocksize)
        if not data:
            break
        sha256.update(data)
    return sha256.hexdigest()


def store_zip(context, zip_filename, target_directory):
    """ Unzip a ZIP file within the given target directory """

    handle = context.webdav_handle()
    if handle.exists(target_directory):
        handle.removedir(target_directory, recursive=True, force=True)
    handle.makedir(target_directory)
    with fs.zipfs.ZipFS(zip_filename, 'r') as zip_in:
        for name in zip_in.walkfiles():
            target_path = '{}/{}'.format(target_directory,
                                         name.replace('/result/', ''))
            handle.ensuredir(target_path)
            with handle.open(target_path, 'wb') as fp_out:
                with zip_in.open(name, 'rb') as fp_in:
                    fp_out.write(fp_in.read())


@contextmanager
def delete_after(filename):
    """ Context manager for closing and deleting a temporary file after usage """

    yield None

    try:
        os.unlink(filename)
    except OSError:
        LOG.error('Unable to remove \'{}\''.format(filename))


def convert_crex(zip_path):
    """ Send ZIP archive with content to be converted to C-Rex.
        Returns name of ZIP file with converted resources.
    """

    ts = time.time()
    registry = getUtility(IRegistry)
    settings = registry.forInterface(ICRexSettings)

    # Fetch authentication token if necessary (older than one hour)
    crex_token = settings.crex_conversion_token
    crex_token_last_fetched = settings.crex_conversion_token_last_fetched or datetime.datetime(
        2000, 1, 1)
    diff = datetime.datetime.utcnow() - crex_token_last_fetched
    if not crex_token or diff.total_seconds() > 3600:
        f = furl.furl(settings.crex_conversion_url)
        token_url = '{}://{}/api/Token'.format(
            f.scheme, f.host, settings.crex_conversion_url)
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

    headers = {'authorization': 'Bearer {}'.format(crex_token)}

    with open(zip_path, 'rb') as fp:
        try:
            LOG.info(u'Starting C-Rex conversion of {}, size {} '.format(zip_path,
                                                                         os.path.getsize(zip_path)))
            result = requests.post(
                settings.crex_conversion_url, files=dict(source=fp), headers=headers)
        except requests.ConnectionError:
            msg = u'Connection to C-REX webservice failed'
            raise CRexConversionError(msg)

        if result.status_code == 200:
            msg = u'Conversion successful (HTTP code {}, duration: {:2.1f} seconds))'.format(
                result.status_code, time.time() - ts)
            LOG.info(msg)
            zip_out = temp_zip(suffix='.zip')
            with open(zip_out, 'wb') as fp:
                fp.write(result.content)
            return zip_out

        else:
            # Forbidden -> invalid token -> invalidate token stored in Plone
            if result.status_code == 401:
                settings.crex_conversion_token = u''
                settings.crex_conversion_token_last_fetched = datetime.datetime(
                    1999, 1, 1)
            msg = u'Conversion failed (HTTP code {}, message {})'.format(
                result.status_code, result.text)
            LOG.error(msg)
            raise CRexConversionError(msg)


def timed(method):
    """ A timing decorator """

    def timed(self):
        path = self.context.absolute_url(1)
        ts = time.time()
        result = method(self)
        te = time.time()
        s = u'{:>25}(\'{}\')'.format(self.__class__.__name__, path)
        s = s + u': {:2.6f} seconds'.format(te - ts)
        LOG.info(s)
        return result
    return timed


class fs_filestream_iterator(object):
    """ Iterator for 'fs' module filesystems """

    implements(IStreamIterator)

    def __init__(self, fs_handle, streamsize=1 << 16):
        self.streamsize = streamsize
        self.fs_handle = fs_handle

    def next(self):
        data = self.fs_handle.read(self.streamsize)
        if not data:
            raise StopIteration
        return data

    def __len__(self):
        cur_pos = self.fs_handle.tell()
        self.fs_handle.seek(0, 2)
        size = self.fs_handle.tell()
        self.fs_handle.seek(cur_pos, 0)
        return size


def temp_zip(suffix='.zip'):
    """ Temporary file for zip files """
    basedir = os.path.join(tempfile.gettempdir(), 'xmldirector-api')
    if not os.path.exists(basedir):
        os.mkdir(basedir)
    fn = tempfile.mkstemp(suffix=suffix, dir=basedir)
    return fn[1]


class BaseService(Service):
    """ Base class for REST services """

    @property
    def catalog(self):
        return plone.api.portal.get_tool('portal_catalog')

    @timed
    def render(self):

        if IConnector.providedBy(self.context) and not self.context.api_enabled:
            raise ValueError('API access disabled for {}'.format(
                self.context.absolute_url))

        try:
            return self._render()
        except Exception as e:
            LOG.error(self.request.text())
            LOG.error(e, exc_info=True)
            raise e


class api_create(BaseService):

    def _render(self):
        """ Create a new content object in Plone """

        check_permission(permissions.ModifyPortalContent, self.context)
        payload = decode_json_payload(self.request)

        id = str(uuid.uuid4())
        title = payload.get('title')
        description = payload.get('description')
        custom = payload.get('custom')

        connector = plone.api.content.create(
            type='xmldirector.plonecore.connector',
            container=self.context,
            id=id,
            title=title,
            description=description)

        connector.webdav_subpath = 'plone.api-{}/{}'.format(
            plone.api.portal.get().getId(), id)
        connector.api_enabled = True
        connector.webdav_handle(create_if_not_existing=True)
        connector.reindexObject()

        if custom:
            annotations = IAnnotations(connector)
            annotations[ANNOTATION_KEY] = custom

        IPersistentLogger(connector).log('created', details=payload)
        self.request.response.setStatus(201)
        return dict(
            id=id,
            url=connector.absolute_url(),
        )


class api_search(BaseService):

    def _render(self):

        check_permission(permissions.View, self.context)

        catalog = plone.api.portal.get_tool('portal_catalog')
        query = dict(
            portal_type='xmldirector.plonecore.connector',
            path='/'.join(self.context.getPhysicalPath()))
        brains = catalog(**query)
        items = list()
        for brain in brains:
            items.append(dict(
                id=brain.getId,
                path=brain.getPath(),
                url=brain.getURL(),
                title=brain.Title,
                creator=brain.Creator,
                created=brain.created.ISO8601(),
                modified=brain.modified.ISO8601()))
        return dict(items=items)


class api_get_metadata(BaseService):

    def _render(self):

        check_permission(permissions.View, self.context)

        annotations = IAnnotations(self.context)
        custom = annotations.get(ANNOTATION_KEY)

        return dict(
            id=self.context.getId(),
            title=self.context.Title(),
            description=self.context.Description(),
            created=self.context.created().ISO8601(),
            modified=self.context.modified().ISO8601(),
            subject=self.context.Subject(),
            creator=self.context.Creator(),
            custom=custom)


class api_set_metadata(BaseService):

    def _render(self):

        check_permission(permissions.ModifyPortalContent, self.context)

        payload = decode_json_payload(self.request)
        IPersistentLogger(self.context).log('set_metadata', details=payload)

        title = payload.get('title')
        if title:
            self.context.setTitle(title)

        description = payload.get('description')
        if description:
            self.context.setDescription(description)

        subject = payload.get('subject')
        if subject:
            self.context.setSubject(subject)

        custom = payload.get('custom')
        if custom:
            annotations = IAnnotations(self.context)
            annotations[ANNOTATION_KEY] = custom

        return dict()


class api_delete(BaseService):

    def _render(self):

        check_permission(permissions.DeleteObjects, self.context)

        util = getUtility(IWebdavHandle)

        handle = util.webdav_handle()
        handle.removedir(self.context.webdav_subpath, True, True)

        parent = self.context.aq_parent
        parent.manage_delObjects(self.context.getId())
        return dict()


class api_store_zip(BaseService):

    def _render(self):

        check_permission(permissions.ModifyPortalContent, self.context)
        IPersistentLogger(self.context).log('store')

        if not 'zipfile' in self.request.form:
            raise ValueError('No parameter "zipfile" found')

        # cleanup source folder
        webdav_handle = self.context.webdav_handle(create_if_not_existing=True)
        target_dir = SRC_PREFIX
        if webdav_handle.exists(target_dir):
            webdav_handle.removedir(target_dir, force=True)
        webdav_handle.makedir(target_dir)

        # Write payload/data to ZIP file
        zip_out = temp_zip(suffix='.zip')
        with open(zip_out, 'wb') as fp:
            fp.write(self.request.form['zipfile'].read())

        # and unpack it
        with delete_after(zip_out):
            with fs.zipfs.ZipFS(zip_out, 'r') as zip_handle:
                for name in zip_handle.walkfiles():
                    dest_name = '{}/{}'.format(target_dir, name)
                    webdav_handle.ensuredir(dest_name)
                    data = zip_handle.open(name, 'rb').read()
                    with webdav_handle.open(dest_name, 'wb') as fp:
                        fp.write(data)
                    with webdav_handle.open(dest_name + '.sha256', 'wb') as fp:
                        fp.write(hashlib.sha256(data).hexdigest())

        return dict(msg=u'Saved')


class api_get_zip(BaseService):

    def _render(self):

        check_permission(permissions.ModifyPortalContent, self.context)

        handle = self.context.webdav_handle(create_if_not_existing=True)
        zip_out = temp_zip(suffix='.zip')
        with fs.zipfs.ZipFS(zip_out, 'w') as zip_handle:
            for name in handle.walkfiles():
                with handle.open(name, 'rb') as fp_in:
                    # zipfs seems to strip off the leading /
                    with zip_handle.open(name, 'wb') as fp_out:
                        fp_out.write(fp_in.read())

        with delete_after(zip_out):
            self.request.response.setHeader(
                'content-length', str(os.path.getsize(zip_out)))
            self.request.response.setHeader('content-type', 'application/zip')
            self.request.response.setHeader(
                'content-disposition', 'attachment; filename={}.zip'.format(self.context.getId()))
            return filestream_iterator(zip_out)


class api_get(BaseService):

    def _render(self):

        check_permission(permissions.View, self.context)
        name = self.request.form.get('name')
        if not name:
            raise ValueError('Parameter "name" is missing')

        mt, encoding = mimetypes.guess_type(os.path.basename(name))
        handle = self.context.webdav_handle(create_if_not_existing=True)
        if handle.exists(name):
            fp = handle.open(name, 'rb')
            size = handle.getsize(name)
            self.request.response.setHeader(
                'content-length', str(size))
            self.request.response.setHeader('content-type', mt)
            self.request.response.setHeader(
                'content-disposition', 'attachment; filename={}'.format(os.path.basename(name)))
            return fs_filestream_iterator(fp)
        else:
            self.request.response.setStatus(403)
            raise zExceptions.NotFound(u'Not found: {}'.format(name))


class api_convert(BaseService):

    def _render(self):

        check_permission(permissions.ModifyPortalContent, self.context)
        IPersistentLogger(self.context).log('convert')

        handle = self.context.webdav_handle()
        zip_tmp = temp_zip(suffix='.zip')
        with fs.zipfs.ZipFS(zip_tmp, 'w') as zip_fp:
            with zip_fp.open('word/index.docx', 'wb') as fp:
                with handle.open('src/word/index.docx', 'rb') as fp_in:
                    fp.write(fp_in.read())

        with delete_after(zip_tmp):
            zip_out = convert_crex(zip_tmp)
        store_zip(self.context, zip_out, 'current')

        with delete_after(zip_out):
            self.request.response.setHeader(
                'content-length', str(os.path.getsize(zip_out)))
            self.request.response.setHeader('content-type', 'application/zip')
            self.request.response.setHeader(
                'content-disposition', 'attachment; filename={}.zip'.format(self.context.getId()))
            return filestream_iterator(zip_out)


class api_list(BaseService):

    def _render(self):

        check_permission(permissions.View, self.context)

        handle = self.context.webdav_handle(create_if_not_existing=True)
        files = list(handle.walkfiles())
        files = [fn.lstrip('/') for fn in files]
        return dict(files=files)


class api_list_full(BaseService):

    def _render(self):

        check_permission(permissions.View, self.context)

        handle = self.context.webdav_handle(create_if_not_existing=True)
        result = dict()
        for dirname in handle.walkdirs():
            for name, data in handle.ilistdirinfo(dirname, full=True):
                # datetime not JSONifyable
                data['modified_time'] = data['modified_time'].isoformat()
                if handle.isfile(name):
                    with handle.open(name, 'rb') as fp:
                        data['sha256'] = sha256_fp(fp)
                result[name] = data
        return result


class api_hashes(BaseService):

    def _render(self):

        check_permission(permissions.View, self.context)
        handle = self.context.webdav_handle(create_if_not_existing=True)
        result = dict()
        for name in handle.walkfiles():
            if name.endswith('.sha256'):
                continue
            result[name.lstrip('/')] = dict()
            try:
                with handle.open(name + '.sha256', 'rb') as fp:
                    result[name.lstrip('/')]['sha256'] = fp.read()
            except fs.errors.ResourceError:
                try:
                    with handle.open(name, 'rb') as fp:
                        result[name.lstrip('/')]['sha256'] = sha256_fp(fp)
                except fs.errors.ResourceError:
                    pass
        return result


class api_store(BaseService):

    def _render(self):

        handle = self.context.webdav_handle(create_if_not_existing=True)
        for file_item in self.request.form.get('files', ()):
            filename = file_item.filename
            handle.ensuredir(filename)
            with handle.open(filename, 'wb') as fp_out:
                fp_out.write(file_item.read())
            with handle.open(filename + '.sha256', 'wb') as fp_out:
                fp_out.write(sha256_fp(file_item))
        return {}


class api_delete_content(BaseService):

    def _render(self):

        check_permission(permissions.ModifyPortalContent, self.context)
        handle = self.context.webdav_handle(create_if_not_existing=True)
        payload = decode_json_payload(self.request)

        if 'files' not in payload:
            raise ValueError('No data for "files" found in JSON data')

        files = payload['files']
        result = dict()
        for name in files:
            if handle.exists(name):
                if handle.isfile(name):
                    handle.remove(name)
                elif handle.isdir(name):
                    handle.removedir(name, force=True)
                result[name] = u'removed'
            else:
                result[name] = u'not found'
        return result
