import requests
import time
import socket
import random
from Modules.logger import log_info, log_error, log_warning
from stem import Signal
from stem.control import Controller



USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "Mozilla/5.0 (X11; Linux x86_64)..."
]

TOR_SOCKS_PORT = 9050
TOR_CONTROL_PORT = 9051

def is_tor_socks_ready(host="127.0.0.1", port=TOR_SOCKS_PORT, retries=5, delay=1):
    """Verifica se a porta SOCKS do Tor está aberta e pronta."""
    for _ in range(retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((host, port))
            s.close()
            log_info("Tor SOCKS is ready")
            return True
        except:
            time.sleep(delay)
    log_error("Tor SOCKS is not ready")
    return False


def get_real_ip():
    try:
        ip = requests.get("https://api.ipify.org").text
        log_info(f"Real IP: {ip}")
        return ip
    except requests.RequestException:
        log_error("Failed to get real IP")
        return "Unavailable"

def is_tor_socks_ready(host="127.0.0.1", port=TOR_SOCKS_PORT, retries=5, delay=1):
    for _ in range(retries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(1)
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            time.sleep(delay)
    log_warning("Tor SOCKS is not ready")
    return False


def get_tor_ip(rotate_user_agent=True):
    if not is_tor_socks_ready():
        return None

    proxies = {
        'http': f'socks5h://127.0.0.1:{TOR_SOCKS_PORT}',
        'https': f'socks5h://127.0.0.1:{TOR_SOCKS_PORT}'
    }
    headers = {}
    if rotate_user_agent and USER_AGENTS:
        headers['User-Agent'] = random.choice(USER_AGENTS)

    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxies, headers=headers, timeout=10)
        ip = response.json().get("origin")
        if ip:
            log_info(f"Tor IP: {ip}")
            return ip
        else:
            log_warning("Tor returned empty IP")
            return None
    except requests.RequestException as e:
        log_error(f"Failed to fetch Tor IP: {e}")
        return None
    
def restart_tor_service(wait=2):
    try:
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            log_info("Requested new Tor identity (NEWNYM)")
            time.sleep(wait)
            return True
    except Exception as e:
        if "SocketClosed" not in str(e):
            log_warning(f"NEWNYM warning (can be ignored): {e}")
        return False
