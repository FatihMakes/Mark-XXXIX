import os
import subprocess
import sys
from pathlib import Path

# Safeguard against UnicodeEncodeError on older Windows terminals
_stdout_encoding = getattr(sys.stdout, 'encoding', None)
if _stdout_encoding and hasattr(sys.stdout, 'reconfigure') and _stdout_encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def print_step(msg):
    print(f"\n🚀 {msg}")

def main():
    print("🤖 Starting Setup for MARK XXX...\n")
    
    venv_dir = Path("venv")
    if not venv_dir.exists():
        print_step("Creating virtual environment (venv)...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    else:
        print_step("Virtual environment already exists.")

    # Determine the venv python executable path
    if os.name == 'nt':
        venv_python = str(venv_dir / "Scripts" / "python.exe")
    else:
        venv_python = str(venv_dir / "bin" / "python")

    # Ensure the python executable exists
    if not os.path.exists(venv_python):
        print(f"❌ Error: Could not find Python executable at {venv_python}")
        sys.exit(1)

    print_step("Installing 'uv' package manager for ultra-fast installations...")
    subprocess.run([venv_python, "-m", "pip", "install", "uv"], check=True)

    print_step("Installing dependencies from requirements.txt using uv...")
    subprocess.run([venv_python, "-m", "uv", "pip", "install", "-r", "requirements.txt"], check=True)

    print_step("Installing Playwright browsers...")
    subprocess.run([venv_python, "-m", "playwright", "install"], check=True)

    print("\n" + "="*50)
    print("✅ Setup is completely finished!")
    print("="*50)
    print("To start MARK XXX, you must first activate your virtual environment:")
    
    if os.name == 'nt':
        print("\n  1. Activate the environment (choose your terminal):")
        print("     PowerShell:    .\\venv\\Scripts\\Activate.ps1")
        print("     Command Prompt: .\\venv\\Scripts\\activate.bat")
        print("     Git Bash:       source venv/Scripts/activate")
        print("\n  2. Run the assistant:")
        print("     python main.py")
    else:
        print("\n  1. Activate the environment:")
        print("     source venv/bin/activate")
        print("\n  2. Run the assistant:")
        print("     python main.py")
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()