✅ FULL PROJECT INSTRUCTION / AGENT PROMPT (COPY–PASTE READY)
Project Name: Multi-Client Real-Time Communication System (Desktop GUI)
BUILD THIS ENTIRE PROJECT EXACTLY AS SPECIFIED BELOW
1. Overview

Build a complete desktop-based real-time communication system supporting:

Multi-client meeting rooms

Meeting code based joining

Host approval workflow

Text messaging via TCP

File transfer via TCP with custom congestion control (Reno-like)

Video/audio streaming via UDP

Adaptive video quality (FPS + resolution + compression)

Real-time network stats (RTT, packet loss, jitter, bitrate, cwnd)

PyQt GUI similar to Google Meet layout

Pure Python: NO WebRTC, NO database, NO external signaling servers

Everything must be implemented manually using Python sockets + threading/async.

2. Tech Stack

Client:

Python 3.x

PyQt5 or PySide6

OpenCV (camera → JPEG compression → frame packets)

PyAudio (audio capture → raw PCM, no compression)

Matplotlib (real-time stats window)

sockets (TCP/UDP)

Server:

Python 3.x

sockets (TCP + UDP)

threading/async

In-memory session data (Python dictionaries only)

3. Server Requirements
3.1 Server Responsibilities

The server must manage:

Meeting creation

Join requests (host approval workflow)

Text messaging broadcasting

File transfer routing

Video/audio UDP stream relaying

Control channel for stats

Congestion control for file transfers

Participant lists

3.2 Global Server Data Structures

Implement these exact structures:

meetings = {
    "<meeting_code>": {
        "host": <client_socket>,
        "participants": [<client_socket>, ...],
        "waiting": [<client_socket>, ...]
    }
}

client_info = {
    <client_socket>: {
        "name": "Jony",
        "meeting": "482913",
        "is_host": True/False,
        "udp_addr": (ip, port)
    }
}


No database. Everything is RAM-based.

3.3 Server Protocol (TCP Control Channel)
Commands:
CREATE_MEETING
REQUEST_JOIN
ALLOW_JOIN
DENY_JOIN
CHAT
FILE_START
FILE_CHUNK
FILE_END
VIDEO_STATS
LEAVE


Server replies using:

MEETING_CREATED
JOIN_PENDING
JOIN_ACCEPTED
JOIN_REJECTED
CHAT_BROADCAST
FILE_CHUNK_FORWARD
VIDEO_STATS_UPDATE

4. Client Requirements

The client has:

4.1 Main Pages
1. Home Screen

“Start Meeting”

“Join with Code”

2. Host Waiting Screen

meeting_code displayed

list of pending users

Approve/Deny buttons

3. Meeting Screen

Layout similar to Google Meet:

Left: Video grid
Right: Chat + file sharing
Bottom bar:

Mic toggle

Camera toggle

Leave button

Stats button (opens stats window)

5. Video Streaming (UDP)
Encoding

Capture frame via OpenCV

Resize dynamically: 144p / 240p / 360p / 480p depending on network

Compress using JPEG (cv2.imencode)

Attach header:

[frame_id (4 bytes)][timestamp (8 bytes)][payload]

Sending

Sender sends frame to server via UDP.
Server relays to all participants.

Receiving

Client:

Detect frame_loss by missing frame_id

Calculate jitter

Calculate delay

Render frame in PyQt video widget

6. Adaptive Streaming Logic (Manual, No WebRTC)

Every 1 second, receiver sends stats to sender over TCP:

VIDEO_STATS
LOSS = x%
RTT = y ms
FPS_RECV = z
BITRATE = b kbps


Sender adjusts quality:

If packet loss > 10% or RTT > 300ms:

lower resolution

lower FPS

increase JPEG compression

If stable (loss < 2%, RTT < 120ms):

increase resolution

increase FPS

reduce compression

FPS can vary: 5 → 10 → 15 → 20
Resolution can vary: 144p → 240p → 360p → 480p

This MUST be implemented manually.

7. Custom TCP Congestion Control for File Transfer

Implement a simplified TCP Reno on top of Python TCP.

Variables:

cwnd = 1
ssthresh = 8


Algorithm:

On each ACK:

if cwnd < ssthresh → cwnd *= 2

else → cwnd += 1

On timeout:

ssthresh = cwnd // 2

cwnd = 1

File transfer chunk size = cwnd * base_chunk_size.

Client must graph cwnd LIVE.

8. Real-Time Stats Dashboard (PyQt + Matplotlib)

Show the following values updating each second:

RTT

Packet loss

Jitter

FPS (sent & received)

Bitrate

cwnd (during file transfer)

The stats must match actual network events.

9. Meeting Flow
Host

Click “Start Meeting”

Server generates meeting ID

Host UI shows code and pending join requests

As participants request access → popup appears

Host clicks Allow/Deny

When allowed → participant enters meeting

Participant

Enters meeting code

Waits for host approval

When allowed → joins the meeting UI

Starts sending video/audio

10. Required Modules (Agent must generate)
Client Modules

ui_home.py

ui_waiting_room.py

ui_meeting.py

video_sender.py

video_receiver.py

audio_sender.py

audio_receiver.py

tcp_control.py

tcp_file_transfer.py

stats_collector.py

stats_window.py

Server Modules

server_main.py

control_handler.py

meeting_manager.py

stream_relay_udp.py

congestion_control.py

router.py

All interactions must follow the protocols defined above.

11. Additional Requirements

Multi-client support must be stable (≥ 3 clients)

No WebRTC, no external STUN/TURN

UDP for video/audio only

TCP for everything else

Clean PyQt interface

Automatic cleanup when client leaves

Works on LAN without port forwarding

DO NOT use shortcuts. Implement all networking logic manually as described.

This is the full blueprint — create all code files, classes, methods, and UI based strictly on this spec.