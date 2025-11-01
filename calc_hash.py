# In this file we calculate the SHA-1 info_hash of the 'info' dictionary in a .torrent file.
# This is just a practice file and does not get imported anywhere
from parser import bdecode, bencode
import hashlib
import pprint

def calculate_info_hash(torrent_file_path):
    """
    Calculate the SHA-1 info_hash of the 'info' dictionary in a .torrent file.
    
    Args:
        torrent_file_path (str): Path to the .torrent file.
        
    Returns:
        bytes: The 20-byte SHA-1 hash of the bencoded info dictionary.
        
    Raises:
        ValueError: If the file is invalid or missing the 'info' key.
        FileNotFoundError: If the torrent file does not exist.
    """
    with open(torrent_file_path, 'rb') as f:
        torrent_data = f.read()
    
    decoded = bdecode(torrent_data)
    
    # Extract the 'info' dictionary
    if b'info' not in decoded:
        raise ValueError("Torrent file does not contain 'info' dictionary")
    info_dict = decoded[b'info']
    
    # Re-encode the 'info' dictionary
    info_bencoded = bencode(info_dict)
    
    # Calculate SHA-1 hash
    info_hash = hashlib.sha1(info_bencoded).digest()
    
    return info_hash


try:
    torrent_file = 'test.torrent'
    
    with open(torrent_file, 'rb') as f:
        torrent_data = f.read()
    # decoded = bdecode(torrent_data)

    info_hash = calculate_info_hash(torrent_file)
    print("\nInfo Hash (hex):", info_hash.hex())
    print("Info Hash (raw bytes):", info_hash)
    
except FileNotFoundError:
    print(f"Error: The file '{torrent_file}' was not found.")
except ValueError as e:
    print(f"Error: {e}")