import grequests
import requests
from collections import namedtuple

Block = namedtuple('Block', 'height time hash')

# Networking

def call_endpoint(url, headers = {'Accept': 'application/json'}):
        
    response = requests.get(url, headers=headers)
    return response

def call_endpoints(urls, headers = {'Accept': 'application/json'}):
    
    requests = (grequests.get(url, headers=headers) for url in urls)
    responses = grequests.map(requests)
    return responses

# Parsing

def parse_sync_info(response):

    catching_up = response["result"]["sync_info"]["catching_up"]
    height = response["result"]["sync_info"]["latest_block_height"]
    time = response["result"]["sync_info"]["latest_block_time"]
    hash = response["result"]["sync_info"]["latest_block_hash"]

    return catching_up, Block(int(height), time, hash)

def parse_node_info(response):

    moniker = response["result"]["node_info"]["moniker"]
    node_id = response["result"]["node_info"]["id"]
    network = response["result"]["node_info"]["network"]

    return moniker, node_id, network