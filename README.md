
<!-- Uses the user's requested style -->

<h1 align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=28&pause=1000&color=F59E0B&center=true&vCenter=true&random=false&width=435&lines=Multi-Client+Communication;Pure+Python+Sockets;Real-Time+Video+%26+Audio;Secure+File+Sharing" alt="Typing SVG" />
</h1>

<p align="center">
  <strong>🌐 Advanced Real-Time Communication System from Scratch</strong>
  <br/>
  <sub>A distributed networking system showcasing custom protocol implementations in Pure Python</sub>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-→-6366F1?style=for-the-badge" alt="Quick Start"/></a>

  <a href="#-authors"><img src="https://img.shields.io/badge/Authors-→-181717?style=for-the-badge&logo=github" alt="Authors"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PyQt5-41CD52?style=flat-square&logo=qt&logoColor=white" alt="PyQt5">
  <img src="https://img.shields.io/badge/Protocol-UDP_%26_TCP-FF6B35?style=flat-square" alt="Protocols">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License">
</p>

<br/>

<!-- Fancy Divider -->
<p align="center">
  <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">
</p>

## 🎯 What is this Project?

This **Multi-Client Real-Time Communication System** is a comprehensive application built entirely from scratch using **pure Python sockets**. Unlike modern apps that rely on WebRTC, this project demonstrates the raw engineering behind:
- **UDP** for low-latency Real-Time Streaming (Video/Audio)
- **TCP** for reliable Control Signaling and Chat
- **Application-Layer Congestion Control** (TCP Reno)
- **Adaptive Quality** based on network metrics

<br/>

## ⚡ Key Features

<table>
<tr>
<td width="50%">

### 📹 Real-Time Streaming
- **Video:** Custom UDP packetization with adaptive resolution (144p-480p).
- **Audio:** Low-latency raw PCM audio over UDP.
- **Traffic Shaping:** Token bucket algorithm for smooth delivery.
- **Header:** Custom binary struct header (24 bytes).

</td>
<td width="50%">

### 💬 Collaborative Tools
- **Rich Chat:** Persistent TCP connection for instant messaging.
- **File Transfer:** Custom reliable transfer with **TCP Reno** congestion control.
- **Visual Stats:** Real-time graphs for RTT, Jitter, Packet Loss, and Bitrate.

</td>
</tr>
<tr>
<td width="50%">

### 🛡️ Meeting Management
- **Security:** Host approval workflow for joining participants.
- **Privacy:** Private messaging and private file sharing.
- **Architecture:** Centralized Server-Relay topology.

</td>
<td width="50%">

### 💻 Modern Interface
- **PyQt5 GUI:** Responsive grid layout similar to Google Meet.
- **Async UI:** Threaded architecture prevents freezing during network I/O.
- **Feedback:** Live status updates and connection health indicators.

</td>
</tr>
</table>

<br/>



## 🚀 Quick Start

### Prerequisites
- **Python 3.8+**
- Webcam & Microphone
- Windows / Linux / macOS

### Installation

```bash
# Clone the repository
git clone https://github.com/SHJony121/Networking.git
cd Networking

# Install dependencies
pip install -r requirements.txt
```

> **Note:** On Windows, if `pip install PyAudio` fails, install it from a `.whl` file [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio).

### Running Use

**1. Start the Server:**
```bash
cd server
python server_main.py
```

**2. Start Client(s):**
```bash
cd client
python main.py
```

<br/>

<p align="center">
  <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%">
</p>

## �‍💻 Authors

<p align="center" id="-authors">
  <a href="https://github.com/Mdsadmansakib">
    <img src="https://github.com/Mdsadmansakib.png" width="100" height="100" style="border-radius:50%"/>
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://github.com/SHJony121">
    <img src="https://github.com/SHJony121.png" width="100" height="100" style="border-radius:50%"/>
  </a>
</p>

<p align="center">
  <a href="https://github.com/Mdsadmansakib"><strong>Md. Sadman Sakib</strong></a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <a href="https://github.com/SHJony121"><strong>Shahria Hasan Jony</strong></a>
</p>

<p align="center">
  <a href="https://github.com/Mdsadmansakib">
    <img src="https://img.shields.io/badge/GitHub-Mdsadmansakib-181717?style=flat-square&logo=github" alt="GitHub"/>
  </a>
  &nbsp;
  <a href="https://github.com/SHJony121">
    <img src="https://img.shields.io/badge/GitHub-SHJony121-181717?style=flat-square&logo=github" alt="GitHub"/>
  </a>
</p>

<br/>

---

<p align="center">
  <strong>Built with ❤️ using Python Sockets</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Made_with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Sockets-TCP_&_UDP-10B981?style=for-the-badge" alt="Sockets">
</p>
