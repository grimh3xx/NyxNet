import requests
from Modules.logger import log_info, log_error, log_warning
import random

USER_AGENTS = [
    "Mozilla/5.0 ...",
    "Chrome/115.0 ...",
    "Safari/605.1 ..."
]

def get_real_ip():
    try:
        ip = requests.get("https://api.ipify.org").text
        log_info(f"Real IP: {ip}")
        return ip
    except requests.RequestException:
        log_error("Failed to get real IP")
        return "Unavailable"

def get_tor_ip(tor_port=9050, rotate_user_agent=True):
    proxies = {
        'http': f'socks5://127.0.0.1:{tor_port}',
        'https': f'socks5://127.0.0.1:{tor_port}'
    }
    headers = {}
    if rotate_user_agent:
        try:
            headers['User-Agent'] = random.choice(USER_AGENTS)
        except IndexError:
            log_warning("USER_AGENTS list is empty. Using default header.")
    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxies, headers=headers, timeout=10)
        ip = response.json().get('origin')
        if ip:
            log_info(f"Tor IP: {ip}")
            return ip
        else:
            log_warning("Tor returned empty IP")
            return None
    except requests.RequestException:
        log_error("Failed to fetch Tor IP")
        return None
