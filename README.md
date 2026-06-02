# 🎬 AutoShorts AI

**AutoShorts AI** is a fully local, CPU-based video processing system that automatically converts long videos into short viral clips (9:16) with smart captions, zoom effects, and engaging visuals. No paid APIs, no cloud services — everything runs offline on your machine.

---

## 🚀 Project Goal

Transform long-form videos into multiple ready-to-post vertical shorts for YouTube Shorts, TikTok, Instagram Reels, etc., using intelligent clip selection and cinematic effects.

---

## 🧠 System Pipeline

1. **Transcription** — Convert speech to timestamped text using Faster-Whisper
2. **Scoring** — Analyze content to find the most engaging moments
3. **Clip Selection** — Choose the best segments based on scores
4. **Rendering** — Cut and convert clips into vertical (9:16) format
5. **Effects** — Apply zoom, transitions, and overlays
6. **Captions** — Generate beautiful subtitles and word-level highlights
7. **Export** — Save final shorts in `shorts_output/`

---

## 🧩 Modules

- `pipeline/transcriber.py` — Audio transcription
- `pipeline/scorer.py` — Clip importance scoring
- `pipeline/selector.py` — Best clip selection logic
- `pipeline/renderer.py` — Video cutting and rendering
- `pipeline/effects.py` — Zoom, captions, and visual effects
- `app.py` — Flask web server + frontend integration
- `static/` — CSS and JavaScript (Dark UI)
- `templates/` — HTML templates

---

## 🛠 Tech Stack

- **Python** 3.10+
- **Flask** — Web framework
- **Faster-Whisper** — High-speed transcription
- **MoviePy** + **FFmpeg** — Video editing
- **Vanilla JS** + **CSS** — Frontend
- **OpenCV / NumPy / Pillow** (as needed)

---

## 📁 Project Structure

```bash
autoshorts/
├── app.py                      # Flask web server
├── pipeline/
│   ├── transcriber.py          # Faster-Whisper wrapper
│   ├── scorer.py               # Clip scoring logic
│   ├── selector.py             # Window selection
│   ├── renderer.py             # MoviePy + FFmpeg render
│   └── effects.py              # Zoom, captions, overlays
├── static/
│   ├── style.css               # Dark theme UI
│   └── app.js                  # Frontend logic
├── templates/
│   └── index.html              # Main UI template
├── uploads/                    # Temporary uploaded videos
├── shorts_output/              # Final exported shorts
├── requirements.txt            # All dependencies
├── RESEARCH.md                 # Research notes
└── README.md                   # This file


# Setup Instructions
Clone the Repository

`Bashgit clone <your-repo-url>
cd autoshorts

Create Virtual Environment

Bashpython -m venv venv
Activate it:

Windows:Bashvenv\Scripts\activate
Linux / macOS:Bashsource venv/bin/activate

Install Dependencies

Bashpip install -r requirements.txt

Run the Application

Bashpython app.py
```