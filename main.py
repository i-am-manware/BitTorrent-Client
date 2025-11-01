# Navigate files in this order:
# parser.py -> calc_hash.py -> get_peers.py -> connect_to_peer.py -> connect_to_peer_async.py

import asyncio
from get_peers import get_peers_from_tracker
from connect_to_peer_async import download_from_peers_async

async def main():    
    #  Get peers
    peers = get_peers_from_tracker('one-piece.torrent')
    if len(peers) == 0:
        print("No peers found in tracker. Exiting...")
        return
    
    # Connect with peers and start downloading
    success = await download_from_peers_async(
        'one-piece.torrent',
        peers,
        'downloaded_file.mkv',
        max_peers=50
    )
    
    if success:
        print("Download successful!")
    else:
        print("Download failed or incomplete")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nDownload interrupted by user")