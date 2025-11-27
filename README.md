# Multi-Client Real-Time Communication System

A complete desktop-based real-time communication system built with **pure Python sockets** (no WebRTC), featuring video/audio streaming, text chat, file transfer with custom TCP congestion control, and adaptive video quality.

## 🎯 Features

- ✅ **Multi-client meeting rooms** with host approval workflow
- ✅ **Video streaming** (UDP) with adaptive quality (144p to 480p)
- ✅ **Audio streaming** (UDP) with raw PCM
- ✅ **Text messaging** (TCP)
- ✅ **File transfer** (TCP) with custom TCP Reno congestion control
- ✅ **Real-time network statistics** (RTT, packet loss, jitter, bitrate, cwnd)
- ✅ **PyQt5 GUI** similar to Google Meet layout
- ✅ **Adaptive streaming logic** based on network conditions

## 📁 Project Structure

```
Networking/
├── server/
│   ├── server_main.py          # Server entry point
│   ├── meeting_manager.py      # Meeting state management
│   ├── control_handler.py      # TCP control message handler
│   ├── stream_relay_udp.py     # UDP video/audio relay
│   └── congestion_control.py   # File transfer congestion control
├── client/
│   ├── main.py                 # Client entry point
│   ├── tcp_control.py          # TCP control channel
│   ├── tcp_file_transfer.py    # File transfer with congestion control
│   ├── video_sender.py         # Video capture and sending
│   ├── video_receiver.py       # Video receiving and display
│   ├── audio_sender.py         # Audio capture and sending
│   ├── audio_receiver.py       # Audio receiving and playback
│   ├── stats_collector.py      # Network statistics collection
│   ├── stats_window.py         # Real-time stats visualization
│   ├── ui_home.py              # Home screen UI
│   ├── ui_waiting_room.py      # Host waiting room UI
│   └── ui_meeting.py           # Main meeting UI
├── common/
│   └── protocol.py             # Shared protocol definitions
├── requirements.txt
└── README.md
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Webcam and microphone
- Windows/Linux/Mac

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note for PyAudio on Windows:**
If `pip install PyAudio` fails, download the wheel from:
https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

Then install with:
```bash
pip install PyAudio‑0.2.13‑cp311‑cp311‑win_amd64.whl
```
(Replace with your Python version)

### 2. Start the Server

```bash
cd server
python server_main.py
```

Server will listen on:
- TCP port 5000 (control channel)
- UDP port 5001 (video/audio streaming)

You can customize ports:
```bash
python server_main.py --tcp-port 5000 --udp-port 5001
```

### 3. Start Client(s)

Open multiple terminals for multiple clients:

```bash
cd client
python main.py
```

Connect to remote server:
```bash
python main.py --server 192.168.1.100 --tcp-port 5000 --udp-port 5001
```

## 📖 Usage Guide

### Host Workflow

1. **Start Meeting**
   - Enter your name
   - Click "Start Meeting"
   - You'll see a 6-digit meeting code

2. **Approve Participants**
   - Share the meeting code
   - When participants request to join, approve or deny them
   - Click "Start Meeting" to enter the meeting room

3. **In Meeting**
   - View all participant videos in grid layout
   - Use chat panel on the right
   - Toggle mic/camera
   - Send files
   - View network stats (click "Stats" button)
   - Leave meeting when done

### Participant Workflow

1. **Join Meeting**
   - Enter your name
   - Enter the 6-digit meeting code
   - Click "Join Meeting"
   - Wait for host approval

2. **In Meeting**
   - Same features as host (except approval workflow)

## 🎮 Controls

| Button | Function |
|--------|----------|
| 🎤 Mic | Toggle microphone on/off |
| 📹 Camera | Toggle camera on/off |
| 📊 Stats | Show real-time network statistics |
| 💬 Chat | Send text messages |
| 📎 Send File | Share files with participants |
| 🚪 Leave | Exit the meeting |

## 📊 Network Statistics

The stats window shows:

1. **RTT (Round Trip Time)** - Network latency in milliseconds
2. **Packet Loss** - Percentage of lost video packets
3. **Jitter** - Variation in packet arrival times
4. **FPS** - Frames per second (sent and received)
5. **Bitrate** - Network throughput in kbps
6. **cwnd** - Congestion window size during file transfers

## 🔧 Technical Details

### Video Streaming

- **Protocol**: UDP
- **Encoding**: JPEG compression with dynamic quality
- **Quality Levels**: 144p, 240p, 360p, 480p
- **FPS Range**: 5-20 FPS (adaptive)
- **Packet Format**: `[frame_id][timestamp][sequence_num][width][height][payload_size][jpeg_data]`

### Audio Streaming

- **Protocol**: UDP
- **Format**: Raw PCM, 16-bit, mono
- **Sample Rate**: 16 kHz
- **Chunk Size**: 1024 samples
- **Packet Format**: `[audio_id][timestamp][sample_rate][channels][payload_size][pcm_data]`

### Adaptive Streaming Logic

The system automatically adjusts video quality based on:

- **Packet Loss > 10%** or **RTT > 300ms**: Lower quality
- **Packet Loss < 2%** and **RTT < 120ms**: Increase quality

Updates occur every 1 second.

### TCP Reno Congestion Control

For file transfers:

- **Slow Start**: `cwnd *= 2` (exponential growth)
- **Congestion Avoidance**: `cwnd += 1` (linear growth)
- **Timeout**: `ssthresh = cwnd // 2`, `cwnd = 1`
- **Initial cwnd**: 1
- **Initial ssthresh**: 8
- **Base chunk size**: 8 KB

## 🐛 Troubleshooting

### Camera not detected
```python
# In video_sender.py, change camera_index
self.camera = cv2.VideoCapture(0)  # Try 0, 1, 2...
```

### Microphone not working
```python
# List available audio devices
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    print(p.get_device_info_by_index(i))
```

### Connection refused
- Ensure server is running
- Check firewall settings
- Verify correct IP address and ports

### High packet loss
- Switch to lower quality manually
- Check network bandwidth
- Reduce number of participants

## 🔒 Security Notice

⚠️ **This is a demonstration project**. It lacks:
- Encryption (video/audio/chat sent in plaintext)
- Authentication
- Input validation
- Production-grade error handling

**Do NOT use for sensitive communications.**

## 📝 Protocol Specification

### TCP Control Messages

| Message Type | Direction | Description |
|-------------|-----------|-------------|
| CREATE_MEETING | Client → Server | Create new meeting |
| REQUEST_JOIN | Client → Server | Request to join meeting |
| ALLOW_JOIN | Host → Server | Approve participant |
| DENY_JOIN | Host → Server | Deny participant |
| CHAT | Client → Server | Send chat message |
| FILE_START | Client → Server | Start file transfer |
| FILE_CHUNK | Client → Server | Send file chunk |
| FILE_ACK | Client → Server | Acknowledge chunk |
| FILE_END | Client → Server | End file transfer |
| VIDEO_STATS | Client → Server | Send video statistics |
| LEAVE | Client → Server | Leave meeting |

### UDP Packet Types

- **Video**: 24-byte header + JPEG payload
- **Audio**: 19-byte header + PCM payload

## 🎓 Learning Objectives

This project demonstrates:

1. **Socket Programming**: TCP and UDP from scratch
2. **Multithreading**: Concurrent video/audio/control channels
3. **Protocol Design**: Custom binary and JSON protocols
4. **Congestion Control**: TCP Reno implementation
5. **Adaptive Streaming**: Network-aware quality adjustment
6. **PyQt GUI**: Complex desktop application UI
7. **Real-time Systems**: Low-latency media streaming

## 📄 License

Educational project - free to use and modify.

## 👤 Author

Built as a comprehensive networking project.

---

**Enjoy building real-time communication from scratch! 🚀**
