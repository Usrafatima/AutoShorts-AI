#  AutoShorts AI — Local Video to Shorts Generator

**AutoShorts AI** is a self-hosted, 100% free, CPU-compatible tool that automatically transforms long-form videos into engaging vertical shorts (9:16) with burned-in animated captions. Everything runs locally on your machine — no cloud costs, no subscriptions, and no API keys required.

---

## Features

- ** AI Clip Selection**: Automatically identifies the most engaging moments using NLP scoring and keyword matching.
- ** Animated Captions**: Word-level highlighted captions (similar to 2short.ai or CapCut) burned directly into the video.
- ** 9:16 Smart Crop**: Automatic center cropping (with optional face detection) for vertical platforms.
- **  Punch-In Zoom**: Cinematic zoom effects on key moments to keep viewers engaged.
- ** CPU Optimized**: Uses `faster-whisper` (int8 quantization) for high-speed transcription even without a GPU.
- **  Web UI**: A polished, dark-themed Flask-based dashboard for easy management.

---

## 🛠 Tech Stack

- **Backend**: Python 3.10+, Flask
- **AI/ML**: `faster-whisper` (Speech-to-Text), `sentence-transformers` (Optional Scoring)
- **Video Editing**: `MoviePy v2`, `FFmpeg`, `OpenCV`
- **Frontend**: Vanilla JS, CSS (Modern Dark UI)

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- [FFmpeg](https://ffmpeg.org/download.html) installed and added to your system PATH.

### 2. Clone the Repository
```bash
git clone https://github.com/Usrafatima/AutoShorts-AI.git
cd autoshorts
```

### 3. Set Up a Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Application

You can start the application using either of the following commands:

### Option 1: Run with Python

```bash
python app.py
```

### Option 2: Run with UV

```bash
uv run app.py
```

Use the command that matches your local development setup.

Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 📜 License
This project is licensed under the MIT License. See the LICENSE file for details.
