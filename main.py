import subprocess
import platform
import time
import socket
from Modules.logger import log_error, log_info, log_warning
from stem import Signal
from stem.control import Controller
import time

# ---------- Cores ----------
RED, GREEN, YELLOW, DEFAULT = '\033[1;31m', '\033[1;92m', '\033[1;33m', '\033[0m'

# ---------- Logs ----------
def log_info(message):
    print(f"{GREEN}[*]{DEFAULT} {message}")

def log_warning(message):
    print(f"{YELLOW}[!]{DEFAULT} {message}")

def log_error(message):
    print(f"{RED}[!]{DEFAULT} {message}")


TOR_CONTROL_PORT = 9051
WAIT = 5


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

def wait_for_tor(port=9050, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', port))
            s.close()
            log_info("Tor SOCKS is running")
            return True
        except:
            time.sleep(1)
    log_error("Tor SOCKS not running")
    return False

def restart_tor_service():
    try:
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            controller.authenticate()  # autenticação via cookie ou password
            controller.signal(Signal.NEWNYM)
            log_info("Requested new Tor identity (NEWNYM)")
            time.sleep(WAIT)  # dá tempo para o Tor atribuir novo IP
            return True
    except Exception as e:
        log_error(f"Failed to request NEWNYM: {e}")
        return False
