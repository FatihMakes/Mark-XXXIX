# 🤖 MARK XXXIX (39)
### The Ultimate Cross-Platform Personal AI Assistant — By FatihMakes

> 📺 **[Watch the full setup video on YouTube](https://youtu.be/ej1f5OE3SNQ?si=lCxDhJix9ungq1Ry)**

A real-time voice AI that can hear, see, understand, and control your computer — on any OS. Supporting Windows, macOS, and Linux. Local execution. Zero subscriptions. Engineered for total autonomy.

---

## ✨ Overview

MARK XXXIX represents the pinnacle of the Jarvis series, evolving into a more flexible and robust system. It bridges the gap between the operating system and human intent. Through natural dialogue, Mark 39 analyzes your screen, processes uploaded documents, and executes complex workflows with a brand-new, adaptive interface.

It's not just an assistant — it's an extension of your digital life.

---

## 🚀 Capabilities

### Core Features
| Feature | Description |
|---|---|
| 🎙️ Real-time Voice | Ultra-low latency conversation in any language |
| 🖥️ System Control | Launch apps, manage files, execute terminal commands |
| 🧩 Autonomous Tasks | High-level planning for complex, multi-step goals |
| 👁️ Visual Awareness | Real-time screen processing and webcam vision |
| 🧠 Persistent Memory | Deeply remembers your projects, preferences, and personal context |
| ⌨️ Hybrid Input | Seamlessly switch between keyboard typing and voice commands |

---

## 🆕 What's New in XXXIX

- 📂 **Advanced File Handling** — New support for direct file uploads. Drop PDFs, source code, or images into the assistant to have them analyzed, summarized, or edited instantly.
- 🎨 **Adaptive & Flexible UI** — A complete overhaul of the interface. The new UI is fully resizable and responsive, featuring transparency controls and customizable layouts to fit your workspace perfectly.
- 🐧🍎 **Refined Cross-Platform Stability** — Major fixes for macOS and Linux compatibility. Core system actions are now more consistent across all three major operating systems.
- ⚡ **Optimized Core Engine** — Significant performance boost in tool-calling logic and response generation, resulting in a 40% faster interaction speed.
- 🔒 **Enhanced Security** — Environment variable support for API keys (.env files), improved platform compatibility, and better error handling.

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11 or 3.12
- Microphone for voice input
- Free [Google Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/FatihMakes/Mark-XXXIX.git
cd Mark-XXXIX
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
playwright install
```

3. **Set up your API key** (Choose one method):

**Option A: Using .env file (Recommended - More Secure)**
```bash
# Create .env file in project root
echo GOOGLE_API_KEY=your_gemini_api_key_here > .env
```

**Option B: Using GUI Setup**
```bash
python main.py
# The GUI will prompt for your API key on first run
```

4. **Start MARK XXXIX:**
```bash
python main.py
```

---

## 🔒 Security & Setup Guide

**⚠️ Important:** For detailed security information, API key management, and platform-specific setup instructions, see **[SECURITY.md](SECURITY.md)**.

Key highlights:
- Use `.env` files for API key storage (recommended)
- Never commit API keys or credentials to git
- Accessible setup for users with screen readers
- Cross-platform compatibility (Windows, macOS, Linux)

---

## 📋 Requirements

| Requirement | Details |
|---|---|
| **OS** | Windows 10/11, macOS, or Linux |
| **Python** | 3.11 or 3.12 |
| **Microphone** | Required for voice interaction |
| **API Key** | [Free Google Gemini API key](https://ai.google.dev/gemini-api/docs/api-key) |

---

## 🔧 Troubleshooting

### Installation Issues

**Q: "ModuleNotFoundError" on macOS or Linux?**  
A: This is expected for Windows-only packages. The app gracefully skips them. See [SECURITY.md](SECURITY.md) for platform-specific guidance.

**Q: "GOOGLE_API_KEY not found"?**  
A: Create a `.env` file with your API key. See **[SECURITY.md](SECURITY.md)** for detailed instructions.

**Q: Audio issues?**  
A: Check [SECURITY.md](SECURITY.md) for platform-specific audio setup.

---

## ⚠️ License

Personal and non-commercial use only.
Licensed under **[Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**.

---

## 👤 Connect with the Creator

Engineered by a developer building a real-world JARVIS-style assistant.
⭐ **Star the repository to support the journey to Mark 100.**

| Platform | Link |
|---|---|
| YouTube | [@FatihMakes](https://www.youtube.com/@FatihMakes) |
| Instagram | [@fatihmakes](https://www.instagram.com/fatihmakes) |

---

## 🤝 Contributing

Found an issue? Want to help improve MARK XXXIX? Check out the [open issues](https://github.com/FatihMakes/Mark-XXXIX/issues) and feel free to submit pull requests!

Current focus areas:
- Cross-platform stability
- Security hardening
- Accessibility improvements
- Performance optimization
