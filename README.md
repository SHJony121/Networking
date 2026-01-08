# 🎥 Multi-Client Real-Time Communication System

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green?style=for-the-badge&logo=qt&logoColor=white)
![Networking](https://img.shields.io/badge/Networking-TCP%2FUDP-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-lightgrey?style=for-the-badge)

> A powerful, desktop-based video conferencing application built entirely with **pure Python sockets**. Experience real-time video, audio, chat, and file sharing without the need for third-party WebRTC libraries.

---

## 🌟 Key Features

- **📹 Real-Time Video Streaming**
  Low-latency UDP streaming with adaptive quality (144p - 480p) that adjusts to your network speed.

- **🎤 Interactive Audio**
  Clear, real-time voice communication using raw PCM audio data over UDP.

- **💬 Robust Chat System**
  Reliable TCP-based instant messaging supporting both broadcast (everyone) and private user-to-user chats.

- **📁 Smart File Transfer**
  Send files reliably with a custom implementation of **TCP Reno** congestion control (Slow Start, Congestion Avoidance, Fast Retransmit).

- **🛡️ Secure Meeting Rooms**
  Host-controlled environment with approval workflows for new participants.

- **📊 Live Network Analytics**
  Visualize network health in real-time with graphs for RTT, Packet Loss, Jitter, and Bitrate.

---

## 📁 Project Structure

```bash
Networking/
├── server/                 # Central server logic
│   ├── server_main.py      # Entry point
│   ├── stream_relay_udp.py # UDP Media Relay
│   └── meeting_manager.py  # specific meeting logic
├── client/                 # Client application
│   ├── main.py             # Entry point
│   ├── video_sender.py     # Camera capture & streaming
│   ├── audio_sender.py     # Mic capture & streaming
│   └── ui_meeting.py       # Main GUI Layout
└── common/                 # Shared protocols & utils
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+**
- A webcam and microphone
- Operatins System: Windows, Linux, or macOS

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/networking-project.git
   cd networking-project
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   > **⚠️ Note for Windows Users:** If `pip install PyAudio` fails, please download the correct `.whl` file from [Christoph Gohlke's Library](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) and install it manually.

---

## 📖 Usage Guide

### 1. Start the Server
The server must be running to handle connections.
```bash
cd server
python server_main.py
```
*The server listens on **TCP:5000** containing control logic and **UDP:5001** for media streaming.*

### 2. Start the Client
Open a new terminal for each user.
```bash
cd client
python main.py
```

### 3. Connect & Collaborate
- **Host:** Enter your name -> Click **"Start Meeting"** -> Share the **6-digit Code**.
- **Guest:** Enter your name -> Enter the **Code** -> Click **"Join Meeting"**.

---

## 🔧 Technical Highlights

This project serves as a comprehensive example of advanced network programming:

| Concept | Implementation |
|---------|----------------|
| **Streaming** | Custom UDP protocol with binary headers for video/audio frames. |
| **Reliability** | TCP for critical control signals (Join/Leave/Chat). |
| **Congestion Control** | **TCP Reno** algorithm implemented at the application layer for file transfers. |
| **Traffic Shaping** | Token bucket / Sleep injection to control transmission rates. |
| **Concurrency** | Extensive use of Python `threading` to handle UI, Net-I/O, and AV processing simultaneously. |

---

## 👥 Authors

- **Md. Sadman Sakib** - [GitHub](https://github.com/Mdsadmansakib)
- **Shahria Hasan Jony** - [GitHub](https://github.com/SHJony121)

---

<p align="center">
  <i>Built for the Computer Networking Project</i>
</p>
