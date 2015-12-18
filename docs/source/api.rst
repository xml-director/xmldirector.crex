REST API documentation
======================

.. http:put:: /plone/xmldirector-create

   Create a new instance of XML Director ``Connector``

   **Example request**:

   .. sourcecode:: http

      PUT /xmldirector-create HTTP/1.1
      Host: example.com
      Accept: application/json
      Content-Type: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "id": "1f461181-b7cd-4708-8181-9787c9530ed2",
        "url": "http://example.com/plone/1f461181-b7cd-4708-8181-9787c9530ed2"
      }

   :reqheader Accept: must be ``application/json``
   :reqheader Content-Type: must be ``application/json``
   :reqheader Authorization: HTTP basic authentication
   :statuscode 201: content created
   :statuscode 403: unauthorized
   :statuscode 404: not found

.. http:get:: /xmldirector-search

   Search for connectors

   **Example request**:

   .. sourcecode:: http

      GET /plone/xmldirector-search HTTP/1.1
      Host: example.com
      Accept: application/json
      Content-Type: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {u'items': [{u'created': u'2015-12-18T13:16:28+01:00',
                   u'creator': u'admin',
                   u'id': u'148d5f0a-3be9-42b6-bc2e-b128df2dbc1b',
                   u'modified': u'2015-12-18T13:16:28+01:00',
                   u'path': u'/plone/148d5f0a-3be9-42b6-bc2e-b128df2dbc1b',
                   u'title': u'',
                   u'url': u'http://localhost:55001/plone/148d5f0a-3be9-42b6-bc2e-b128df2dbc1b'},
                  {u'created': u'2015-12-18T13:16:27+01:00',
                   u'creator': u'god',
                   u'id': u'connector',
                   u'modified': u'2015-12-18T13:16:27+01:00',
                   u'path': u'/plone/connector',
                   u'title': u'',
                   u'url': u'http://localhost:55001/plone/connector'}]}

   :reqheader Accept: must be ``application/json``
   :reqheader Content-Type: must be ``application/json``
   :reqheader Authorization: HTTP basic authentication
   :statuscode 200: Search successful
   :statuscode 403: unauthorized
   :statuscode 404: not found

.. http:delete:: /xmldirector-delete

   Removes a ``Connector`` given by its path/url

   **Example request**:

   .. sourcecode:: http

      DELETE /plone/1f461181-b7cd-4708-8181-9787c9530ed2/xmldirector-delete HTTP/1.1
      Host: example.com
      Accept: application/json
      Content-Type: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
      }

   :reqheader Accept: must be ``application/json``
   :reqheader Content-Type: must be ``application/json``
   :reqheader Authorization: HTTP basic authentication
   :statuscode 200: Connector deleted
   :statuscode 403: unauthorized
   :statuscode 404: not found
