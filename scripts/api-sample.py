
import pprint
import json
import requests
from requests.auth import HTTPBasicAuth


def verify_result(result):
    data_json = result.json()
    if 'error' in data_json:
        print result.url
        print data_json['error']
        raise RuntimeError()

base_url = 'http://dev1.veit-schiele.de:12020/Plone'
user = 'admin'
password = 'admin'
all_headers = {'content-type': 'application/json', 'accept' : 'application/json'}

def send_request(method='GET', path='/@@API', data=None, files=None, headers={}, folder=None, url=None):

    f = getattr(requests, method.lower())
    api_url = url if url else base_url
    if folder:
        api_url += folder
    api_url += '/{}'.format(path)
    request_headers = all_headers.copy()
    request_headers.update(headers)
    print method, api_url
    if data:
        result = f(
            api_url, 
            auth=HTTPBasicAuth(user, password),
            headers=request_headers,
            data=data)
    elif files:
        result = f(
            api_url, 
            auth=HTTPBasicAuth(user, password),
            files=files)
    else:
        result = f(
            api_url, 
            auth=HTTPBasicAuth(user, password),
            headers=request_headers)
    print result
    return result


payload = dict(
    title=u'Hello world',
    description=u'This is the description',
    custom=dict(
        a=1,
        b=2,
        hello=u'world')
)

print '-'*80
print 'SEARCH'
result = send_request('GET', 'xmldirector-search')
verify_result(result)
data = result.json()
pprint.pprint(data)

print '-'*80
print 'CREATE'
result = send_request('PUT', 'xmldirector-create', folder='/folder', data=json.dumps(payload))
verify_result(result)
print result
data = result.json()
id = data['id']
url = data['url']
print(id)
print (url)


print '-'*80
print 'GET_METADATA'
result = send_request('GET', 'xmldirector-get-metadata', url=url)
verify_result(result)
data = result.json()
pprint.pprint(data)


print '-'*80
print 'SET_METADATA'
payload = dict(
    title=u'new title: hello world',
    description=u'New description'
)
result = send_request('POST', 'xmldirector-set-metadata', data=json.dumps(payload), url=url)
verify_result(result)
print result


print '-'*80
print 'DELETE'
result = send_request('DELETE', 'xmldirector-delete', url=url)
verify_result(result)
data = result.json()
pprint.pprint(data)

import sys
sys.exit(0)


for i in range(1,3):
    print '-'*80
    print 'UPLOAD DOCX'
    files = {'file': open('sample.docx', 'rb')}
    print url
    result = send_request('POST', '/@@API/xmldirector/store', files=files)
    verify_result(result)
    data = result.json()
    pprint.pprint(data)

print '-'*80
print 'UPLOAD GET'
payload = dict(
    files=['word/*']
)
result = send_request('POST', '/@@API/xmldirector/get', data=json.dumps(payload))
verify_result(result)
data = result.json()
pprint.pprint(data)

#print '-'*80
#print 'CONVERT2'
#result = send_request('GET','/@@API/xmldirector/convert2/')
#verify_result(result)
#data = result.json()
#pprint.pprint(data)

#print '-'*80
#print 'CONVERT'
#files = {'file': open('sample.zip', 'rb')}
#result = send_request('POST', '/@@API/xmldirector/convert/', files=files)
#verify_result(result)
#data = result.json()
#pprint.pprint(data)



