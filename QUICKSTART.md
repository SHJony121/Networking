# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Start Server

```bash
cd server
python server_main.py
```

You should see:
```
====================================================
Multi-Client Real-Time Communication Server
====================================================
[Server] UDP relay started on port 5001
[Server] TCP control server listening on 0.0.0.0:5000
[Server] Server is ready! Waiting for clients...
====================================================
```

### Step 3: Start First Client (Host)

Open a new terminal:

```bash
cd client
python main.py
```

In the GUI:
1. Enter your name: `Alice`
2. Click **"Start Meeting"**
3. Note the 6-digit code (e.g., `482913`)

### Step 4: Start Second Client (Participant)

Open another terminal:

```bash
cd client
python main.py
```

In the GUI:
1. Enter your name: `Bob`
2. Enter meeting code: `482913`
3. Click **"Join Meeting"**

### Step 5: Host Approves

In Alice's window:
1. You'll see a popup: "Bob wants to join the meeting"
2. Click **"Allow"**
3. Click **"Start Meeting"**

### Step 6: Enjoy the Meeting! 🎉

Both clients will enter the meeting room:
- See each other's video
- Chat in real-time
- Share files
- View network statistics

## 🎮 Try These Features

### Chat
Type a message and press Enter or click "Send"

### File Transfer
Click "📎 Send File" and select any file

### Network Stats
Click "📊 Stats" to see real-time graphs of:
- RTT
- Packet loss
- Jitter
- FPS
- Bitrate
- Congestion window (during file transfer)

### Camera/Mic Control
Toggle with the 🎤 and 📹 buttons

## 🔧 Configuration

### Change Server Port

```bash
# Server
python server_main.py --tcp-port 6000 --udp-port 6001

# Client
python main.py --server 127.0.0.1 --tcp-port 6000 --udp-port 6001
```

### Run on LAN

Find your IP address:

**Windows:**
```bash
ipconfig
```

**Linux/Mac:**
```bash
ifconfig
# or
ip addr show
```

Start server on your IP (e.g., 192.168.1.100):
```bash
python server_main.py
```

On other computers:
```bash
python main.py --server 192.168.1.100
```

## 🐛 Common Issues

### Issue: "Failed to connect to server"
**Solution:** 
- Ensure server is running
- Check firewall settings
- Verify IP address

### Issue: Camera not working
**Solution:**
- Grant camera permissions
- Try different camera index in `video_sender.py`
- Restart application

### Issue: No audio
**Solution:**
- Check microphone permissions
- Verify audio device in system settings
- Try different audio input device

### Issue: PyAudio installation fails (Windows)
**Solution:**
Download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
```bash
pip install PyAudio‑0.2.13‑cp311‑cp311‑win_amd64.whl
```

## 📊 Testing the System

### Test Adaptive Streaming

1. Start a meeting with 2 clients
2. Open stats window on both
3. Watch the quality adapt as network changes
4. Try transferring a large file to see cwnd graph

### Test Multiple Clients

Start 3-4 clients and watch the video grid adjust automatically

### Test File Transfer

1. Send a large file (e.g., 10MB)
2. Open stats window
3. Watch the congestion window (cwnd) graph
4. See TCP Reno algorithm in action

## 🎓 Understanding the Architecture

```
┌─────────────┐
│   Client 1  │ ←──TCP Control──→ ┌──────────┐ ←──TCP Control──→ │   Client 2  │
│             │                    │          │                    │             │
│  Video/Audio├──────UDP──────────→│  Server  │←──────UDP─────────┤  Video/Audio│
│   Sender    │                    │  Relay   │                   │   Receiver  │
└─────────────┘                    └──────────┘                    └─────────────┘
```

### Components:

1. **TCP Control Channel**: Meeting management, chat, file transfer
2. **UDP Relay**: Video/audio packet forwarding
3. **Stats Collector**: Network monitoring
4. **Adaptive Logic**: Quality adjustment

## 📝 Next Steps

- Read the full README.md for detailed documentation
- Explore the code in each module
- Modify video quality thresholds
- Add new features (screen sharing, recording, etc.)

Happy coding! 🚀
