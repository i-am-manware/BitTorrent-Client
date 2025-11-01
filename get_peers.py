# In this file we fetch the IP list of peers from tracker

import urllib.parse
import urllib.request
import hashlib
import os
import random
from parser import bdecode, bencode

def get_peers_from_tracker(torrent_file_path, port=6881, numwant=50):
    """
    Communicate with the tracker to fetch a list of peers for the torrent.
    
    Args:
        torrent_file_path (str): Path to the .torrent file.
        port (int): The port your client is listening on (default: 6881).
        numwant (int): Number of peers to request (default: 50).
        
    Returns:
        list: List of tuples (ip_str, port_int) for peers.
        
    Raises:
        ValueError: If required keys are missing or request fails.
        urllib.error.URLError: If network issues occur.
    """
    # Read and decode the torrent file
    with open(torrent_file_path, 'rb') as f:
        torrent_data = f.read()
    decoded = bdecode(torrent_data)
    
    if b'announce' not in decoded:
        raise ValueError("Torrent file missing 'announce' key")
    announce_url = decoded[b'announce'].decode('utf-8')
    
    info = decoded[b'info']
    # Re-encode info to compute info_hash
    info_bencoded = bencode(info)
    info_hash = hashlib.sha1(info_bencoded).digest()
    
    # Calculate total bytes left (for single or multi-file torrents)
    if b'length' in info:
        left = info[b'length']
    elif b'files' in info:
        left = sum(f[b'length'] for f in info[b'files'])
    else:
        raise ValueError("Invalid info dictionary: missing 'length' or 'files'")
    
    # Generate a peer_id (20 bytes, e.g., '-PY0001-' + random)
    peer_id_prefix = b'-PY0001-'
    peer_id = peer_id_prefix + os.urandom(20 - len(peer_id_prefix))
    
    # Prepare parameters for the announce request
    params = {
        'info_hash': info_hash,
        'peer_id': peer_id,
        'port': port,
        'uploaded': 0,
        'downloaded': 0,
        'left': left,
        'compact': 1,
        'event': 'started',
        'numwant': numwant,
    }
    
    # URL-encode binary values properly
    query_parts = []
    for key, val in params.items():
        if isinstance(val, bytes):
            # Properly encode binary data
            encoded_val = urllib.parse.quote(val, safe='')
            query_parts.append(f"{key}={encoded_val}")
        else:
            # Regular URL encoding for non-binary values
            query_parts.append(f"{key}={urllib.parse.quote(str(val), safe='')}")
    
    query_string = '&'.join(query_parts)
    
    # Build the full announce URL
    if '?' in announce_url:
        full_url = announce_url + '&' + query_string
    else:
        full_url = announce_url + '?' + query_string
    
    print(f"Announce URL: {announce_url}")
    print(f"Full announce URL: {full_url}")
    # print(f"Requesting: {announce_url}")
    
    # Send HTTP GET request
    req = urllib.request.Request(full_url)
    req.add_header('User-Agent', 'Python-BitTorrent-Client/1.0')
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            tracker_data = response.read()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        raise ValueError(f"Tracker returned error: {e.code} - {error_body}")
    
    print(f"Received tracker response: {tracker_data}")
    # Decode the tracker response (bencoded)
    tracker_decoded = bdecode(tracker_data)
    
    # Check for failure reason
    if b'failure reason' in tracker_decoded:
        failure = tracker_decoded[b'failure reason'].decode('utf-8')
        raise ValueError(f"Tracker failure: {failure}")
    
    if b'peers' not in tracker_decoded:
        raise ValueError("Tracker response missing 'peers' key")
    
    peers_data = tracker_decoded[b'peers']
    # print(f"Received peers from tracker: ", peers_data)
    
    # Handle both compact and non-compact peer formats
    peers = []
    if isinstance(peers_data, bytes):
        # Compact format: 4 bytes IP + 2 bytes port per peer
        if len(peers_data) % 6 != 0:
            raise ValueError("Invalid compact peers format")
        
        for i in range(0, len(peers_data), 6):
            ip_bytes = peers_data[i:i+4]
            port_bytes = peers_data[i+4:i+6]
            ip = '.'.join(map(str, ip_bytes))
            port = int.from_bytes(port_bytes, 'big')
            peers.append((ip, port))
    elif isinstance(peers_data, list):
        # Non-compact format: sometimes the tracker might send a list of dictionaries
        for peer_dict in peers_data:
            ip = peer_dict[b'ip'].decode('utf-8')
            port = peer_dict[b'port']
            peers.append((ip, port))
    else:
        raise ValueError("Unknown peers format")
    
    return peers

# Example usage
if __name__ == "__main__":
    try:
        peers = get_peers_from_tracker('one-piece.torrent')
        print(f"\nFound {len(peers)} peers from tracker:")
        for ip, port in peers[:10]:
            print(f"  {ip}:{port}")
        if len(peers) > 10:
            print(f"  ... and {len(peers) - 10} more")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()