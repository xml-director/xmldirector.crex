# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting
from plone.testing import z2
from Products.Five.browser import BrowserView

from zope.configuration import xmlconfig


class CRexLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import xmldirector.crex
        xmlconfig.file(
            'configure.zcml',
            xmldirector.crex,
            context=configurationContext
        )


CREX_FIXTURE = CRexLayer()
CREX_INTEGRATION_TESTING = IntegrationTesting(
    bases=(CREX_FIXTURE,),
    name="CRexLayer:Integration"
)
CREX_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(CREX_FIXTURE, z2.ZSERVER_FIXTURE),
    name="CRexLayer:Functional"
)
