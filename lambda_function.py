import os
import requests
from collections import defaultdict

req = {
    'POST': requests.post,
    'GET': requests.get,
    'OPTIONS': requests.options,
    'PUT': requests.put,
    'HEAD': requests.head
}

# any exceptions where the target is http need to be noted.
target_protocol = defaultdict(lambda: 'https')
if 'http_targets' in os.environ:
    for http_target in os.environ['http_targets'].split(','):
        target_protocol[http_target.lower()] = 'http'

# create (lookup & rev lookup) dict for hosts found in url_map env var
swap_host = dict()
for pair in [tuple(urls.split(':')) for urls in os.environ['url_map'].split(',')]:
    swap_host[pair[0].lower()] = pair[1].lower()
    swap_host[pair[1].lower()] = pair[0].lower()
print(swap_host)


def lambda_handler(event, context):
    headers = {
        k: event['multiValueHeaders'][k][0]
        for k in event['multiValueHeaders']
    }
    try:
        host = swap_host[headers['host'].lower()]
    except KeyError:
        return {
            "statusCode": 403,
            "multiValueHeaders": event['multiValueHeaders'],
            "body": "Improper use"
        }

    http_method = event['httpMethod']
    path = event['path']
    print(event, f"{target_protocol[host]}://{host}{path}")
    response = req[http_method](
        f"{target_protocol[host]}://{host}{path}",
        headers=headers,
        params=event['multiValueQueryStringParameters'],
        data=event['body']
    )
    domain_swapped_list = list()
    for h in response.raw.headers.getlist('Set-Cookie'):
        domain_swapped_list.append(swap_host[h], 'Domain=.')
    header_multi = {h: [response.headers[h], ] for h in response.headers}
    header_multi["Set-Cookie"] = domain_swapped_list
    if 'Access-Control-Allow-Origin' in header_multi:
        header_multi['Access-Control-Allow-Origin'][0] = (
            swap_host[header_multi['Access-Control-Allow-Origin'][0]]
        )
    return {
        "statusCode": response.status_code,
        "multiValueHeaders": header_multi,
        "body": response.text
    }
