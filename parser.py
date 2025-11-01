# In this file we write helper functions to parse .torrent data
import pprint

def parse_int(data, i):
    assert data[i] == ord('i')
    i += 1
    j = data.index(b'e', i)
    val = int(data[i:j].decode())
    return val, j+1

def parse_str(data, i):
    j = data.index(b':', i)
    length = int(data[i:j])
    j += 1
    s = data[j:j+length]
    return s, j+length

def parse_list(data, i):
    assert data[i] == ord('l')
    i += 1
    arr = []
    while i<len(data) and data[i] != ord('e'):
        val, i = parse_any(data, i)
        arr.append(val)
    return arr, i+1

def parse_dict(data, i):
    assert data[i] == ord('d')
    i += 1
    d = {}
    while i<len(data) and data[i] != ord('e'):
        key, i = parse_str(data, i)
        val, i = parse_any(data, i)
        d[key] = val
    return d, i+1

def parse_any(data, i):
    if data[i] == ord('i'):
        return parse_int(data, i)
    elif data[i] == ord('l'):
        return parse_list(data, i)
    elif data[i] == ord('d'):
        return parse_dict(data, i)
    elif chr(data[i]).isdigit():
        return parse_str(data, i)
    else:
        raise ValueError(f"Invalid bencode type at index {i}: {chr(data[i])}")

def bdecode(data):
    if not isinstance(data, bytes):
        raise ValueError("Input must be a byte string")
    if not data:
        raise ValueError("Empty input")
    
    result, index = parse_any(data, 0)
    if index < len(data):
        raise ValueError(f"Extra data after parsing at index {index}")
    return result

def bencode(data):
    if isinstance(data, int):
        return b'i' + str(data).encode() + b'e'
    elif isinstance(data, bytes):
        return str(len(data)).encode() + b':' + data
    elif isinstance(data, str):
        # Convert string to bytes (assuming UTF-8)
        data = data.encode('utf-8')
        return str(len(data)).encode() + b':' + data
    elif isinstance(data, list):
        result = [b'l']
        for item in data:
            result.append(bencode(item))
        result.append(b'e')
        return b''.join(result)
    elif isinstance(data, dict):
        result = [b'd']
        # Sort keys to ensure consistent encoding (BitTorrent requires sorted keys)
        for key in sorted(data.keys()):
            if not isinstance(key, bytes):
                key = key.encode('utf-8')  # Convert string keys to bytes
            result.append(bencode(key))
            result.append(bencode(data[key]))
        result.append(b'e')
        return b''.join(result)
    else:
        raise ValueError(f"Unsupported type for bencoding: {type(data)}")
    
with open('test.torrent', 'rb') as f:
    torrent_data = f.read()

decoded = bdecode(torrent_data)
pprint.pprint(decoded[b'info'])