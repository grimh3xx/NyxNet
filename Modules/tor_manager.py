import requests
import time
import socket
import random
from Modules.logger import log_info, log_error, log_warning

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "Mozilla/5.0 (X11; Linux x86_64)..."
]

TOR_SOCKS_PORT = 9050

def is_tor_socks_ready(host="127.0.0.1", port=TOR_SOCKS_PORT, retries=5, delay=1):
    """Verifica se a porta SOCKS do Tor está aberta e pronta."""
    for i in range(retries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(1)
            s.connect((host, port))
            s.close()
            log_info("Tor SOCKS is ready")
            return True
        except Exception:
            time.sleep(delay)
    log_warning("Tor SOCKS is not ready")
    return False


def get_real_ip():
    try:
        ip = requests.get("https://api.ipify.org").text
        log_info(f"Real IP: {ip}")
        return ip
    except requests.RequestException:
        log_error("Failed to get real IP")
        return "Unavailable"

def get_tor_ip(tor_port=TOR_SOCKS_PORT, rotate_user_agent=True):
    """Pega o IP via Tor usando requests e SOCKS."""
    if not is_tor_socks_ready(port=tor_port):
        return None

    proxies = {
        'http': f'socks5h://127.0.0.1:{tor_port}',
        'https': f'socks5h://127.0.0.1:{tor_port}'
    }
    headers = {}
    if rotate_user_agent:
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
