"""
Protocol definitions for the Multi-Client Real-Time Communication System
"""
import struct

# ============================================================================
# TCP Control Channel Message Types
# ============================================================================

# Client -> Server
MSG_CREATE_MEETING = "CREATE_MEETING"
MSG_REQUEST_JOIN = "REQUEST_JOIN"
MSG_ALLOW_JOIN = "ALLOW_JOIN"
MSG_DENY_JOIN = "DENY_JOIN"
MSG_CHAT = "CHAT"
MSG_FILE_START = "FILE_START"
MSG_FILE_CHUNK = "FILE_CHUNK"
MSG_FILE_ACK = "FILE_ACK"
MSG_FILE_END = "FILE_END"
MSG_VIDEO_STATS = "VIDEO_STATS"
MSG_AUDIO_STATS = "AUDIO_STATS"
MSG_LEAVE = "LEAVE"
MSG_HEARTBEAT = "HEARTBEAT"
MSG_REGISTER_UDP = "REGISTER_UDP"
MSG_CAMERA_STATUS = "CAMERA_STATUS"  # Notify camera on/off

# Server -> Client
MSG_MEETING_CREATED = "MEETING_CREATED"
MSG_JOIN_PENDING = "JOIN_PENDING"
MSG_JOIN_ACCEPTED = "JOIN_ACCEPTED"
MSG_JOIN_REJECTED = "JOIN_REJECTED"
MSG_CHAT_BROADCAST = "CHAT_BROADCAST"
MSG_FILE_CHUNK_FORWARD = "FILE_CHUNK_FORWARD"
MSG_FILE_START_NOTIFY = "FILE_START_NOTIFY"
MSG_FILE_END_NOTIFY = "FILE_END_NOTIFY"
MSG_VIDEO_STATS_UPDATE = "VIDEO_STATS_UPDATE"
MSG_PARTICIPANT_JOINED = "PARTICIPANT_JOINED"
MSG_PARTICIPANT_LEFT = "PARTICIPANT_LEFT"
MSG_NEW_JOIN_REQUEST = "NEW_JOIN_REQUEST"
MSG_HEARTBEAT_ACK = "HEARTBEAT_ACK"
MSG_CAMERA_STATUS_BROADCAST = "CAMERA_STATUS_BROADCAST"  # Broadcast camera status to all

# ============================================================================
# Video Packet Format (UDP)
# ============================================================================
# Header: [frame_id (4 bytes)][timestamp (8 bytes)][sequence_num (4 bytes)]
#         [width (2 bytes)][height (2 bytes)][payload_size (4 bytes)][payload]

VIDEO_HEADER_SIZE = 24  # 4 + 8 + 4 + 2 + 2 + 4

def pack_video_header(frame_id, timestamp, sequence_num, width, height, payload_size):
    """Pack video header into bytes"""
    return struct.pack('!IQIHHi', frame_id, timestamp, sequence_num, width, height, payload_size)

def unpack_video_header(data):
    """Unpack video header from bytes"""
    if len(data) < VIDEO_HEADER_SIZE:
        raise ValueError(f"Invalid video header size: {len(data)}")
    frame_id, timestamp, sequence_num, width, height, payload_size = struct.unpack('!IQIHHi', data[:VIDEO_HEADER_SIZE])
    return {
        'frame_id': frame_id,
        'timestamp': timestamp,
        'sequence_num': sequence_num,
        'width': width,
        'height': height,
        'payload_size': payload_size
    }

# ============================================================================
# Audio Packet Format (UDP)
# ============================================================================
# Header: [audio_id (4 bytes)][timestamp (8 bytes)][sample_rate (2 bytes)]
#         [channels (1 byte)][payload_size (4 bytes)][payload]

AUDIO_HEADER_SIZE = 19  # 4 + 8 + 2 + 1 + 4

def pack_audio_header(audio_id, timestamp, sample_rate, channels, payload_size):
    """Pack audio header into bytes"""
    return struct.pack('!IQHBi', audio_id, timestamp, sample_rate, channels, payload_size)

def unpack_audio_header(data):
    """Unpack audio header from bytes"""
    if len(data) < AUDIO_HEADER_SIZE:
        raise ValueError(f"Invalid audio header size: {len(data)}")
    audio_id, timestamp, sample_rate, channels, payload_size = struct.unpack('!IQHBi', data[:AUDIO_HEADER_SIZE])
    return {
        'audio_id': audio_id,
        'timestamp': timestamp,
        'sample_rate': sample_rate,
        'channels': channels,
        'payload_size': payload_size
    }

# ============================================================================
# TCP Message Format
# ============================================================================
# All TCP messages are JSON encoded with a length prefix:
# [length (4 bytes)][json_payload]

def pack_tcp_message(msg_type, **kwargs):
    """
    Pack a TCP message with length prefix
    Returns: bytes
    """
    import json
    msg_dict = {'type': msg_type}
    msg_dict.update(kwargs)
    json_str = json.dumps(msg_dict)
    json_bytes = json_str.encode('utf-8')
    length = len(json_bytes)
    return struct.pack('!I', length) + json_bytes

def unpack_tcp_message(sock):
    """
    Unpack a TCP message from socket
    Returns: dict or None if connection closed
    """
    import json
    
    # Read length prefix
    length_data = recv_exact(sock, 4)
    if not length_data:
        return None
    
    length = struct.unpack('!I', length_data)[0]
    print(f"[Protocol] unpack_tcp_message: length={length}")
    
    # Read JSON payload
    json_data = recv_exact(sock, length)
    if not json_data:
        return None
    
    print(f"[Protocol] unpack_tcp_message: json_data={json_data[:100]}")
    result = json.loads(json_data.decode('utf-8'))
    print(f"[Protocol] unpack_tcp_message: msg_type={result.get('type')}")
    return result

def recv_exact(sock, n):
    """Receive exactly n bytes from socket"""
    data = b''
    while len(data) < n:
        try:
            chunk = sock.recv(n - len(data))
            if not chunk:
                # Connection closed
                return None
            data += chunk
        except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
            # Connection error
            print(f"[Protocol] recv_exact error: {e}")
            return None
    return data

# ============================================================================
# File Transfer Protocol
# ============================================================================
# FILE_START: {filename, filesize, chunk_size}
# FILE_CHUNK: {chunk_id, data (base64)}
# FILE_ACK: {chunk_id, cwnd}
# FILE_END: {checksum}

# ============================================================================
# Video Quality Levels
# ============================================================================
VIDEO_QUALITIES = {
    '144p': {'width': 256, 'height': 144, 'fps': 5, 'jpeg_quality': 40},
    '240p': {'width': 426, 'height': 240, 'fps': 10, 'jpeg_quality': 50},
    '360p': {'width': 640, 'height': 360, 'fps': 15, 'jpeg_quality': 60},
    '480p': {'width': 854, 'height': 480, 'fps': 20, 'jpeg_quality': 70},
}

# ============================================================================
# Audio Configuration
# ============================================================================
AUDIO_SAMPLE_RATE = 16000  # 16 kHz
AUDIO_CHANNELS = 1  # Mono
AUDIO_CHUNK_SIZE = 1024  # Samples per chunk
AUDIO_FORMAT = 'int16'  # 16-bit PCM

# ============================================================================
# Network Timeouts & Thresholds
# ============================================================================
TCP_SOCKET_TIMEOUT = 30  # seconds
UDP_PACKET_LOSS_THRESHOLD = 2  # seconds - assume packet lost after this
HEARTBEAT_INTERVAL = 5  # seconds
STATS_UPDATE_INTERVAL = 1  # seconds

# Adaptive streaming thresholds
PACKET_LOSS_HIGH_THRESHOLD = 10  # percent
PACKET_LOSS_LOW_THRESHOLD = 2  # percent
RTT_HIGH_THRESHOLD = 300  # milliseconds
RTT_LOW_THRESHOLD = 120  # milliseconds

# ============================================================================
# Congestion Control (TCP Reno for File Transfer)
# ============================================================================
INITIAL_CWND = 1
INITIAL_SSTHRESH = 8
BASE_CHUNK_SIZE = 8192  # 8 KB base chunk size
MAX_CWND = 64  # Maximum congestion window
