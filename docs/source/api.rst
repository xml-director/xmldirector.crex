REST API documentation
======================

.. http:put:: /xmldirector-create

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
