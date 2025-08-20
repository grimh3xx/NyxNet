import subprocess
import platform
import time
import socket
from Modules.logger import log_error, log_info, log_warning


# ---------- Cores ----------
RED, GREEN, YELLOW, DEFAULT = '\033[1;31m', '\033[1;92m', '\033[1;33m', '\033[0m'

# ---------- Logs ----------
def log_info(message):
    print(f"{GREEN}[*]{DEFAULT} {message}")

def log_warning(message):
    print(f"{YELLOW}[!]{DEFAULT} {message}")

def log_error(message):
    print(f"{RED}[!]{DEFAULT} {message}")

# ---------- Tor ----------
def install_tor():
    system = platform.system()
    try:
        subprocess.run(['which', 'tor'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log_info("Tor is already installed")
        return True
    except subprocess.CalledProcessError:
        log_warning("Tor not found. Installing...")
        try:
            if system == "Linux":
                subprocess.run(['sudo', 'apt', 'update'], check=True)
                subprocess.run(['sudo', 'apt', 'install', '-y', 'tor'], check=True)
            elif system == "Darwin":  # MacOS
                subprocess.run(['brew', 'install', 'tor'], check=True)
            elif system == "Windows":
                log_error("Automatic installation not supported on Windows. Install Tor manually.")
                return False
            log_info("Tor installed successfully")
            return True
        except Exception as e:
            log_error(f"Failed to install Tor: {e}")
            return False

def wait_for_tor(port=9050, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', port))
            s.close()
            log_info("Tor is running and ready")
            return True
        except:
            time.sleep(1)
    log_error("Tor did not start in time")
    return False

def restart_tor_service():
    system = platform.system()
    try:
        if system in ["Linux", "Darwin"]:
            subprocess.run(
                ['sudo', 'systemctl', 'restart', 'tor'],
                check=True,
                stdout=subprocess.DEVNULL,  # <- suprime saída
                stderr=subprocess.DEVNULL
            )
        log_info("Tor service restarted")  # ainda podemos logar, mas no painel
    except Exception as e:
        log_error(f"Failed to restart Tor: {e}")
