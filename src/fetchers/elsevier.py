import os
import re
import requests

def fetch_elsevier_abstract(link):
    """
    Attempts to fetch the abstract from Elsevier API using PII extracted from the link.
    Requires 'ELSEVIER_API_KEY' environment variable.
    Returns: Abstract string if found, None otherwise.
    """
    api_key = os.environ.get("ELSEVIER_API_KEY")
    if not api_key:
        return None

    # Check if it's a ScienceDirect link
    if "sciencedirect.com" not in link:
        return None

    # Extract PII
    match = re.search(r'/pii/([A-Z0-9]+)', link)
    if not match:
        return None
    
    pii = match.group(1)
    url = f"https://api.elsevier.com/content/abstract/pii/{pii}"
    headers = {
        "Accept": "application/json",
        "X-ELS-APIKey": api_key
    }
    params = {"view": "FULL"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            try:
                resp_root = data.get('abstracts-retrieval-response', {})
                abstract = resp_root.get('item', {}).get('bibrecord', {}).get('head', {}).get('abstracts')
                if not abstract:
                     abstract = resp_root.get('coredata', {}).get('dc:description')
                
                return abstract
            except:
                return None
        return None

    except Exception as e:
        print(f"Error fetching abstract for {pii}: {e}")
        return None