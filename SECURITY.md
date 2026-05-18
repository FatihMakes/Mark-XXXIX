# Security & Setup Guide for MARK XXXIX

## 🔒 Security Best Practices

### 1. API Key Management (.env)

**IMPORTANT:** Never store API keys in plain text files or commit them to version control!

#### Recommended: Using .env files

1. Create a `.env` file in the project root directory:
```bash
touch .env
```

2. Add your API key:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

3. The application will automatically load this file when starting.

**Benefits:**
- ✅ Credentials never committed to git (.gitignore protects it)
- ✅ Works across all platforms (Windows, macOS, Linux)
- ✅ Accessible for users with screen readers (no GUI required)
- ✅ Easy to use in CI/CD pipelines

#### Legacy: config/api_keys.json (Backward Compatible)

If you have an existing `config/api_keys.json`, the app will still work, but we recommend migrating to .env for better security.

To migrate:
1. Read your current API key from `config/api_keys.json`
2. Create a `.env` file with the key
3. Delete or rename the old `config/api_keys.json`

### 2. Headless Setup (Accessibility)

For users who cannot use the GUI (screen reader users, remote access, etc.):

```bash
# The application will use your .env file automatically if set up
python main.py
```

No GUI API key prompt will appear if GOOGLE_API_KEY is already in .env.

### 3. Protecting Sensitive Data

The `.gitignore` file protects these sensitive items:
- `.env` — API keys and secrets
- `config/api_keys.json` — Legacy API key storage
- `__pycache__/` — Python cache
- `.vscode/`, `.idea/` — IDE configurations

These files will never be accidentally committed.

---

## 🖥️ Platform-Specific Setup

### Windows 10/11

```bash
pip install -r requirements.txt
playwright install
python main.py
```

All packages, including Windows-specific ones (win10toast, pycaw, pywinauto) are installed.

### macOS

```bash
pip install -r requirements.txt
playwright install
python main.py
```

Windows-specific packages are skipped automatically. The environment marker syntax in requirements.txt ensures this.

**Note:** Some features like system volume control may not work on macOS due to OS limitations. The app gracefully falls back to available functionality.

### Linux (Ubuntu, Debian, ElementaryOS, etc.)

```bash
pip install -r requirements.txt
playwright install
python main.py
```

Windows-specific packages are skipped. Audio input/output works via PulseAudio or ALSA.

**Additional dependencies for audio (if needed):**
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev

# Fedora
sudo dnf install portaudio-devel

# macOS
brew install portaudio
```

---

## 🛡️ Security Vulnerabilities Fixed

### Issue #2: RCE via Prompt Injection
**Status:** ✅ Being addressed through validation and sandboxing in tool execution.

### Issue #2: Plain-Text API Key Storage
**Status:** ✅ **FIXED** — Environment variables (.env) now recommended.

### Issue #2: Redundant File I/O
**Status:** ✅ Cached API key retrieval in progress.

### Issue #2: Tkinter Thread Safety
**Status:** ⏳ In progress — Using `root.after()` for safe UI updates from background threads.

---

## 📋 Troubleshooting

### "GOOGLE_API_KEY not found" error

**Solution:**
1. Create `.env` file in project root
2. Add: `GOOGLE_API_KEY=your_key`
3. Restart the application

### Platform-specific package errors

**Example:** `ImportError: No module named 'pycaw'` on non-Windows

**Solution:** This is expected and handled gracefully. The app will skip Windows-only features on other platforms.

### "playwright install" command not found

**Solution:**
```bash
python -m playwright install
```

---

## 🔑 Getting Your Gemini API Key

1. Visit: https://ai.google.dev/gemini-api/docs/api-key
2. Create or use your Google account
3. Click "Create API Key"
4. Copy the key
5. Add to `.env` file: `GOOGLE_API_KEY=your_key`

---

## 📚 Additional Resources

- [Google Gemini API Documentation](https://ai.google.dev)
- [python-dotenv Documentation](https://python-dotenv.readthedocs.io/)
- [Playwright Documentation](https://playwright.dev/python/)

---

**Last Updated:** 2026-05-18  
**Author:** MARK XXXIX Community  
**Status:** Active - Security improvements in progress
