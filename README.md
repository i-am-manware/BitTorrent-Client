# BitTorrent-Client (Educational Implementation)
From my YouTube Guide of how to build a BitTorrent Client

A lightweight, educational BitTorrent client written in Python. This project demonstrates the core mechanics of the BitTorrent protocol, including:

- Parsing `.torrent` files using **bencoding**
- Computing the **info_hash**
- Communicating with **trackers** to get peer lists
- Performing **handshakes** with peers
- Downloading **pieces** via block requests
- **Synchronous** and **asynchronous** peer connection models

> **Note**: This is not a production-ready client. It is designed for learning and experimentation.

---

## Files Overview

| File | Purpose |
|------|---------|
| **`parser.py`** | Implements **bencode** decoding (`bdecode`) and encoding (`bencode`) functions to parse `.torrent` files. Includes helper parsers for integers, strings, lists, and dictionaries. |
| **`calc_hash.py`** | Standalone script to compute and print the **SHA-1 info_hash** of the `info` dictionary in a `.torrent` file. Useful for debugging and verification. |
| **`get_peers.py`** | Contacts the **tracker** using HTTP GET to retrieve a list of peers. Supports compact peer format. Generates a random `peer_id` and properly URL-encodes binary data like `info_hash`. |
| **`connect_to_peers.py`** | **Synchronous** implementation of peer connection. Performs handshake, sends `interested`, requests blocks, receives `piece` messages, verifies piece hashes, and assembles files. Includes a full single-threaded downloader. |
| **`connect_to_peer_async.py`** | **Asynchronous** version using `asyncio`. Supports concurrent connections to multiple peers, piece scheduling, bitfield tracking, and efficient block downloading. More scalable and realistic. |

---

## Prerequisites

- Python 3.6+
- Standard libraries only (`socket`, `struct`, `hashlib`, `urllib`, `asyncio`, etc.)

No external dependencies.

---

## Usage

1. Place a `.torrent` file (e.g., `test.torrent`) in the same directory.
2. Run any script:

```bash
# Calculate info hash
python calc_hash.py

# Get peers from tracker
python get_peers.py

# Download (sync version)
python connect_to_peers.py

# Download (async version - recommended)
python connect_to_peer_async.py
```

> Output file will be saved as `downloaded_file.bin` (or as specified).

---

## Learning Goals Achieved

- Understand bencoding format
- Parse real `.torrent` files
- Implement tracker HTTP protocol
- Master BitTorrent handshake & message format
- Handle piece verification with SHA-1
- Build both sync and async peer clients

---

**Happy torrenting (for science)!**
