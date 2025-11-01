# In this file we connect to a single peer, perform the BitTorrent handshake 
# and try to download all pieces from it.

import socket
import struct
import hashlib
import time
from parser import bdecode, bencode

class BitTorrentPeer:
    """Handles communication with a single BitTorrent peer."""
    
    def __init__(self, ip, port, info_hash, peer_id, timeout=5):
        self.ip = ip
        self.port = port
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.timeout = timeout
        self.socket = None
        self.choked = True
        self.interested = False
        self.peer_choking = True
        self.peer_interested = False
        self.bitfield = None
        
    def connect(self):
        """Establish TCP connection to peer."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.ip, self.port))
            return True
        except Exception as e:
            print(f"Failed to connect to {self.ip}:{self.port} - {e}")
            return False
    
    def handshake(self):
        """
        Perform BitTorrent handshake.
        Format: <pstrlen><pstr><reserved><info_hash><peer_id>
        - pstrlen: 1 byte (19)
        - pstr: 19 bytes ("BitTorrent protocol")
        - reserved: 8 bytes (all zeros)
        - info_hash: 20 bytes
        - peer_id: 20 bytes
        """
        pstr = b"BitTorrent protocol"
        pstrlen = len(pstr)
        reserved = b'\x00' * 8
        
        handshake_msg = struct.pack("B", pstrlen) + pstr + reserved + self.info_hash + self.peer_id
        
        try:
            self.socket.send(handshake_msg)
            
            # Receive handshake response (68 bytes total)
            response = self._recv_exact(68)
            
            # Parse response
            resp_pstrlen = response[0]
            resp_pstr = response[1:20]
            resp_reserved = response[20:28]
            resp_info_hash = response[28:48]
            resp_peer_id = response[48:68]
            
            # Verify the response
            if resp_pstrlen != 19 or resp_pstr != pstr:
                print(f"Invalid handshake from {self.ip}:{self.port}")
                return False
            
            if resp_info_hash != self.info_hash:
                print(f"Info hash mismatch from {self.ip}:{self.port}")
                return False
            
            print(f"Handshake successful with {self.ip}:{self.port}")
            return True
            
        except Exception as e:
            print(f"Handshake failed with {self.ip}:{self.port} - {e}")
            return False
    
    def _recv_exact(self, n):
        """Receive exactly n bytes from socket."""
        data = b''
        while len(data) < n:
            chunk = self.socket.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed by peer")
            data += chunk
        return data
    
    def send_interested(self):
        """Send 'interested' message to peer."""
        msg = struct.pack(">IB", 1, 2)  # length=1, id=2 (interested)
        self.socket.send(msg)
        self.interested = True
        print(f"Sent interested to {self.ip}:{self.port}")
    
    # def send_unchoke(self):
    #     """Send 'unchoke' message to peer."""
    #     msg = struct.pack(">IB", 1, 1) 
    #     self.socket.send(msg)
    #     self.choked = False
    
    def send_request(self, piece_index, begin, length):
        """
        Request a block from peer.
        Message: <len=0013><id=6><index><begin><length>
        """
        msg = struct.pack(">IBIII", 13, 6, piece_index, begin, length)
        self.socket.send(msg)
        print(f"Requested piece {piece_index}, offset {begin}, length {length}")
    
    def receive_message(self):
        """
        Receive and parse a message from peer.
        Returns: (message_id, payload) or (None, None) for keep-alive
        """
        try:
            # Read message length (4 bytes)
            length_data = self._recv_exact(4)
            length = struct.unpack(">I", length_data)[0]
            
            if length == 0:
                # Keep-alive message
                return None, None
            
            # Read message ID (1 byte)
            msg_id_data = self._recv_exact(1)
            msg_id = struct.unpack("B", msg_id_data)[0]
            
            # Read payload (length - 1 bytes)
            payload = b''
            if length > 1:
                payload = self._recv_exact(length - 1)
            
            return msg_id, payload
            
        except socket.timeout:
            return None, None
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None, None
    
    def handle_message(self, msg_id, payload):
        """Process received messages."""
        if msg_id is None:
            # Keep-alive
            return None
        
        # Message IDs
        # 0: choke, 1: unchoke, 2: interested, 3: not interested
        # 4: have, 5: bitfield, 6: request, 7: piece, 8: cancel
        
        if msg_id == 0:
            self.peer_choking = True
            print(f"Peer {self.ip}:{self.port} choked us")
        elif msg_id == 1:
            self.peer_choking = False
            print(f"Peer {self.ip}:{self.port} unchoked us")
        elif msg_id == 2:
            self.peer_interested = True
        elif msg_id == 3:
            self.peer_interested = False
        elif msg_id == 4:
            # Have message - peer has a piece
            piece_index = struct.unpack(">I", payload)[0]
            print(f"Peer has piece {piece_index}")
        elif msg_id == 5:
            # Bitfield - which pieces peer has
            self.bitfield = payload
            print(f"Received bitfield from {self.ip}:{self.port} ({len(payload)} bytes)")
        elif msg_id == 7:
            # Piece message - actual data
            index = struct.unpack(">I", payload[0:4])[0]
            begin = struct.unpack(">I", payload[4:8])[0]
            block = payload[8:]
            print(f"Received piece {index}, offset {begin}, {len(block)} bytes")
            return ('piece', index, begin, block)
        
        return None
    
    def has_piece(self, piece_index):
        """Check if peer has a specific piece."""
        if self.bitfield is None:
            return False
        byte_index = piece_index // 8
        bit_index = 7 - (piece_index % 8)
        if byte_index >= len(self.bitfield):
            return False
        return bool((self.bitfield[byte_index] >> bit_index) & 1)
    
    def close(self):
        """Close connection to peer."""
        if self.socket:
            self.socket.close()


def download_piece(peer, piece_index, piece_length, piece_hash, block_size=16384):
    """
    Download a complete piece from a peer.
    
    Args:
        peer: BitTorrentPeer object (already connected and handshaked)
        piece_index: Index of the piece to download
        piece_length: Length of the piece in bytes
        piece_hash: SHA1 hash of the piece for verification
        block_size: Size of each block request (default 16KB)
    
    Returns:
        bytes: The complete piece data, or None if failed
    """
    # Wait for bitfield and unchoke
    piece_data = {}
    max_attempts = 50
    
    for _ in range(max_attempts):
        msg_id, payload = peer.receive_message()
        if msg_id is not None:
            result = peer.handle_message(msg_id, payload)
            if result and result[0] == 'piece':
                _, idx, begin, block = result
                if idx == piece_index:
                    piece_data[begin] = block
    
    # Check if peer has this piece
    if not peer.has_piece(piece_index):
        print(f"Peer doesn't have piece {piece_index}")
        return None
    
    # Send interested if not already
    if not peer.interested:
        peer.send_interested()
    
    # Wait for unchoke
    while peer.peer_choking:
        msg_id, payload = peer.receive_message()
        if msg_id is not None:
            peer.handle_message(msg_id, payload)
        time.sleep(0.1)
    
    print(f"Downloading piece {piece_index} ({piece_length} bytes)")
    
    # Request blocks
    for begin in range(0, piece_length, block_size):
        length = min(block_size, piece_length - begin)
        peer.send_request(piece_index, begin, length)
    
    # Collect blocks
    piece_data = {}
    timeout_counter = 0
    max_timeout = 100
    
    while len(piece_data) * block_size < piece_length and timeout_counter < max_timeout:
        msg_id, payload = peer.receive_message()
        
        if msg_id is None:
            timeout_counter += 1
            time.sleep(0.1)
            continue
        
        result = peer.handle_message(msg_id, payload)
        if result and result[0] == 'piece':
            _, idx, begin, block = result
            if idx == piece_index:
                piece_data[begin] = block
                timeout_counter = 0
    
    # Assemble piece from blocks
    if sum(len(block) for block in piece_data.values()) < piece_length:
        print(f"Failed to download complete piece {piece_index}")
        return None
    
    # Sort by offset and concatenate
    complete_piece = b''.join(piece_data[offset] for offset in sorted(piece_data.keys()))
    
    # Verify hash
    calculated_hash = hashlib.sha1(complete_piece).digest()
    if calculated_hash != piece_hash:
        print(f"Piece {piece_index} hash verification failed!")
        return None
    
    print(f"Piece {piece_index} downloaded and verified successfully!")
    return complete_piece


def download_from_peers(torrent_file_path, peers, output_file):
    """
    Download a torrent file from peers.
    
    Args:
        torrent_file_path: Path to .torrent file
        peers: List of (ip, port) tuples
        output_file: Path to save downloaded file
    """
    # Read torrent metadata
    with open(torrent_file_path, 'rb') as f:
        torrent_data = bdecode(f.read())
    
    info = torrent_data[b'info']
    info_hash = hashlib.sha1(bencode(info)).digest()
    piece_length = info[b'piece length']
    pieces_hash = info[b'pieces']
    
    # Calculate number of pieces
    num_pieces = len(pieces_hash) // 20
    
    # Get total length
    if b'length' in info:
        total_length = info[b'length']
    else:
        total_length = sum(f[b'length'] for f in info[b'files'])
    
    print(f"Torrent info: {num_pieces} pieces, {total_length} bytes total")
    
    # Generate peer_id
    peer_id = b'-PY0001-' + b'0' * 12
    
    # Storage for downloaded pieces
    downloaded_pieces = [None] * num_pieces
    
    # Try to download from each peer
    for ip, port in peers:
        print(f"\nTrying peer {ip}:{port}")
        
        peer = BitTorrentPeer(ip, port, info_hash, peer_id)
        
        if not peer.connect():
            continue
        
        if not peer.handshake():
            peer.close()
            continue
        
        # Try to download missing pieces
        for piece_idx in range(num_pieces):
            if downloaded_pieces[piece_idx] is not None:
                continue
            
            # Calculate piece length (last piece may be smaller)
            if piece_idx == num_pieces - 1:
                current_piece_length = total_length - (piece_idx * piece_length)
            else:
                current_piece_length = piece_length
            
            # Get piece hash
            piece_hash = pieces_hash[piece_idx * 20:(piece_idx + 1) * 20]
            
            # Download piece
            piece_data = download_piece(peer, piece_idx, current_piece_length, piece_hash)
            
            if piece_data:
                downloaded_pieces[piece_idx] = piece_data
                print(f"Progress: {sum(1 for p in downloaded_pieces if p is not None)}/{num_pieces} pieces")
        
        peer.close()
        
        # Check if complete
        if all(p is not None for p in downloaded_pieces):
            print("\nDownload complete!")
            break
    
    # Write to file
    if all(p is not None for p in downloaded_pieces):
        with open(output_file, 'wb') as f:
            for piece in downloaded_pieces:
                f.write(piece)
        print(f"File saved to {output_file}")
    else:
        print(f"Download incomplete: {sum(1 for p in downloaded_pieces if p is not None)}/{num_pieces} pieces")

from get_peers import get_peers_from_tracker

# Example usage
if __name__ == "__main__":
    peers = get_peers_from_tracker('one-piece.torrent')
    print(peers[:10])
    
    try:
        download_from_peers('one-piece.torrent', peers, 'downloaded_file.bin')
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()