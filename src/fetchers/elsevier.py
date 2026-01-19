import os
import re
import sys
import logging
from elsapy.elsclient import ElsClient
from elsapy.elsdoc import AbsDoc, FullDoc

# Configure logger
logger = logging.getLogger(__name__)

def fetch_elsevier_abstract(link):
    """
    Attempts to fetch the abstract from Elsevier API using PII extracted from the link.
    Requires 'ELSEVIER_API_KEY' environment variable.
    Returns: A tuple (abstract_string, full_json_data). Returns (None, None) if not found or error.
    """
    api_key = os.environ.get("ELSEVIER_API_KEY")
    if not api_key:
        logger.warning("ELSEVIER_API_KEY not set, skipping Elsevier fetch.")
        return (None, None)

    # Check if it's a ScienceDirect link
    if "sciencedirect.com" not in link:
        return (None, None)

    # Extract PII
    match = re.search(r'/pii/([A-Z0-9]+)', link)
    if not match:
        logger.warning(f"Could not extract PII from link: {link}")
        return (None, None)
    
    pii = match.group(1)
    client = ElsClient(api_key)
    
    # Strategy 1: Try Scopus Abstract API (AbsDoc) - usually has richer metadata
    try:
        # Manually construct URI for AbsDoc with PII
        target_uri = f"https://api.elsevier.com/content/abstract/pii/{pii}"
        doc = AbsDoc(uri=target_uri)
        if doc.read(client):
            abstract = _extract_abstract(doc.data)
            if abstract:
                return (abstract, doc.data)
    except Exception as e:
        logger.debug(f"Scopus API fetch failed for PII {pii}: {e}")

    # Strategy 2: Fallback to ScienceDirect API (FullDoc) - works for newer articles
    try:
        doc = FullDoc(sd_pii=pii)
        if doc.read(client):
            abstract = _extract_abstract(doc.data)
            if abstract:
                return (abstract, doc.data)
            # Even if abstract extraction fails, return data if available
            return (None, doc.data)
    except Exception as e:
        logger.error(f"ScienceDirect API fetch failed for PII {pii}: {e}")

    return (None, None)

def _extract_abstract(data):
    """Helper to extract abstract text from different Elsevier JSON structures."""
    try:
        coredata = data.get('coredata', {})
        abstract = None
        
        # 1. Try Scopus structure (item -> bibrecord -> head -> abstracts)
        if 'item' in data:
            abstract = data.get('item', {}).get('bibrecord', {}).get('head', {}).get('abstracts')
        
        # 2. Try Coredata description (Common in ScienceDirect and Scopus fallbacks)
        if not abstract:
            abstract = coredata.get('dc:description')
            
        # 3. Clean copyright info if present
        if abstract:
            copyright_info = coredata.get('publishercopyright')
            if copyright_info and abstract.startswith(copyright_info):
                abstract = abstract[len(copyright_info):].strip()
                
        return abstract
    except Exception:
        return None