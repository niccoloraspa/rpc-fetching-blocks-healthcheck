import grequests
import requests

# Networking

def call_endpoint(url, headers = {'Accept': 'application/json'}):
        
    response = requests.get(url, headers=headers)
    return response

def call_endpoints(urls, headers = {'Accept': 'application/json'}):
    
    requests = (grequests.get(url, headers=headers) for url in urls)
    responses = grequests.map(requests)
    return responses
