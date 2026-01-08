
<h1 align="center">Multi-Client Real-Time Communication System</h1>

<p align="center">
  <strong>A Pure Python Implementation of Advanced Networking Protocols</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PyQt5-41CD52?style=flat-square&logo=qt&logoColor=white" alt="PyQt5">
  <img src="https://img.shields.io/badge/Protocol-UDP_%26_TCP-FF6B35?style=flat-square" alt="Protocols">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License">
</p>

<p align="center">
  <a href="#-installation--setup">
    <img src="https://img.shields.io/badge/Installation-Jump_to_Section-blue?style=for-the-badge&logo=windows" alt="Go to Installation">
  </a>
  <a href="#-authors">
    <img src="https://img.shields.io/badge/Authors-View_Credits-black?style=for-the-badge&logo=github" alt="View Authors">
  </a>
</p>

<br/>

## 📖 Project Overview

This project is a robust video conferencing and collaboration tool built from the ground up using **standard Python sockets**. It deliberately avoids high-level libraries like WebRTC to demonstrate the core engineering challenges of real-time systems: managing latency, handling packet loss, and implementing custom flow/congestion control algorithms.

<br/>

## ✨ Key Features

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>� Core Networking</h3>
      <ul>
        <li><strong>Adaptive Video Streaming (UDP)</strong>: Dynamically adjusts resolution (144p-480p) based on real-time packet loss and RTT analysis.</li>
        <li><strong>Low-Latency Audio (UDP)</strong>: Raw PCM audio transmission for instant voice communication.</li>
        <li><strong>Reliable Chat (TCP)</strong>: Persistent connection for broadcast and private messaging.</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>�️ Advanced Mechanisms</h3>
      <ul>
        <li><strong>Congestion Control</strong>: Custom implementation of <strong>TCP Reno</strong> (Slow Start, Fast Retransmit) for file sharing.</li>
        <li><strong>Traffic Shaping</strong>: Token bucket algorithms to smooth out data bursts.</li>
        <li><strong>Meeting Management</strong>: Host-controlled room system with join requests.</li>
      </ul>
    </td>
  </tr>
</table>

<br/>

## � Project Directory Structure

A look at the codebase organization:

```bash
Networking/
├── server/                     # 🖥️ Server-side Logic
│   ├── server_main.py          # Entry point for the server
│   ├── meeting_manager.py      # Handles room creation & joining logic
│   ├── control_handler.py      # Manages TCP control signaling
│   ├── stream_relay_udp.py     # Relays UDP media packets between clients
│   └── congestion_control.py   # Reno algorithm implementation
│
├── client/                     # 👤 Client-side Application
│   ├── main.py                 # Application launcher
│   ├── ui_meeting.py           # Main GUI (PyQt5)
│   ├── video_sender.py         # Captures & streams video
│   ├── video_receiver.py       # Decodes & renders video
│   ├── audio_sender.py         # Mic input handling
│   ├── audio_receiver.py       # Audio playback
│   └── stats_collector.py      # Network metrics monitoring
│
├── common/                     # 🔗 Shared Resources
│   ├── protocol.py             # Packet definitions & constants
│   └── utils.py                # Helper functions
│
└── requirements.txt            # Project dependencies
```

<br/>

## 💿 Installation & Setup

Follow these steps to get the system running on your local machine.

### Prerequisites
*   Python 3.8 or higher
*   A webcam and microphone
*   OS: Windows (Preferred), Linux, or macOS

### 1. Clone the Repository
```bash
git clone https://github.com/SHJony121/Networking.git
cd Networking
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
> **⚠️ Windows Audio Fix:** If you encounter errors installing `PyAudio`, download the appropriate `.whl` file from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) and install it manually: `pip install PyAudio‑0.2.11‑cp310‑win_amd64.whl`

### 3. Run the Application

**Step A: Start the Server**
Open a terminal and run:
```bash
cd server
python server_main.py
```
*The server will start listening on TCP Port 5000 and UDP Port 5001.*

**Step B: Start Clients**
Open new terminal windows for each client you want to simulate:
```bash
cd client
python main.py
```

<br/>

## 👥 Authors

This project was designed and implemented by:

<div align="center">
  <table>
    <tr>
      <td align="center" width="200px">
        <a href="https://github.com/Mdsadmansakib">
          <img src="https://github.com/Mdsadmansakib.png" width="100px" style="border-radius: 50%;" alt="Md. Sadman Sakib"/><br />
          <b>Md. Sadman Sakib</b>
        </a>
      </td>
      <td align="center" width="200px">
        <a href="https://github.com/SHJony121">
          <img src="https://github.com/SHJony121.png" width="100px" style="border-radius: 50%;" alt="Shahria Hasan Jony"/><br />
          <b>Shahria Hasan Jony</b>
        </a>
      </td>
    </tr>
  </table>
</div>

---

<p align="center">
  <i>Developed for Computer Networking Course Project</i>
</p>
