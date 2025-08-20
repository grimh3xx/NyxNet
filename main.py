#!/usr/bin/env python3
import os, time, yaml, platform, subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.align import Align
from Modules.tor_manager import install_tor, wait_for_tor, restart_tor_service
from Modules.ip_manager import get_real_ip, get_tor_ip
from Modules.logger import log_info, log_error, log_warning
from Modules.utils import clear_screen, check_root
from stem import Signal
from stem.control import Controller

console = Console()

# ---------- Cores ----------
RED, GREEN, YELLOW, BLUE, DEFAULT = '\033[1;31m', '\033[1;92m', '\033[1;33m', '\033[1;34m', '\033[0m'

# ---------- Banner ----------
def display_banner():
    banner_text = """
███╗   ██╗██╗   ██╗██╗  ██╗███╗   ██╗███████╗████████╗
████╗  ██║╚██╗ ██╔╝╚██╗██╔╝████╗  ██║██╔════╝╚══██╔══╝
██╔██╗ ██║ ╚████╔╝  ╚███╔╝ ██╔██╗ ██║█████╗     ██║   
██║╚██╗██║  ╚██╔╝   ██╔██╗ ██║╚██╗██║██╔══╝     ██║   
██║ ╚████║   ██║   ██╔╝ ██╗██║ ╚████║███████╗   ██║   
╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝
Version: 1.0   Author: 0xBl4ckn3t   Project: NyxNet
"""
    panel = Panel(banner_text, title="NyxNet 🌐🕵️‍♂️", border_style="blue", expand=False)
    console.print(panel)
    
# ---------- Tor NEWNYM ----------
TOR_CONTROL_PORT = 9051
def restart_tor_service(wait=5):
    try:
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            log_info("Requested new Tor identity (NEWNYM)")
            time.sleep(wait)  # espera o Tor mudar o IP
            return True
    except Exception as e:
        log_error(f"Failed to request NEWNYM: {e}")
        return False


# ---------- Config ----------
with open("config.yaml") as f:
    config = yaml.safe_load(f)

INTERVAL = config.get("interval", 5)        # mais rápido
MAX_CHANGES = config.get("max_changes", -1)
ROTATE_UA = config.get("rotate_user_agent", True)

# ---------- Main ----------
def main():
    if os.geteuid() != 0:
        console.print("[!] This script must be run as root.", style="bold red")
        return
    
    clear_screen()
    console.print(display_banner())

    # Instala e verifica Tor
    if not install_tor():
        return
    if not wait_for_tor():
        return
    # ---------- Config ----------
    try:
        interval = int(input(f"{GREEN}[>] Interval to change IP (Interval, default 3): {DEFAULT}") or 3)
        if interval < 1:
            interval = 1
    except ValueError:
        interval = 3
    try:
        max_changes = int(input(f"{GREEN}[>] Max changes (-1 infinite, default -1): {DEFAULT}") or -1)
    except ValueError:
        max_changes = -1

    real_ip = get_real_ip()
    tor_ip = get_tor_ip()
    change_count = 0

    # ---------- Live painel ----------
    with Live(refresh_per_second=2, screen=True) as live:
        while max_changes == -1 or change_count < max_changes:
            if restart_tor_service():
                for _ in range(10):
                    new_tor_ip = get_tor_ip()
                    if new_tor_ip != tor_ip and new_tor_ip is not None:
                        tor_ip = new_tor_ip
                        break
                    time.sleep(0.5)
            
            # Cria tabela de IPs
            table = Table(title="🌐 IP Status", title_style="bold blue", show_lines=True)
            table.add_column("Type", justify="center", style="bold cyan")
            table.add_column("IP Address", justify="center", style="bold green")
            table.add_row("Real IP 🌍", real_ip)
            table.add_row("Tor IP 🕵️‍♂️", tor_ip if tor_ip else "[bold red]Failed[/bold red]")

            # Painel centralizado
            panel = Panel(
                Align.center(table),
                title="NyxNet IP Tracker",
                border_style="bold magenta",
                padding=(1, 2),
                subtitle=f"Changes: {change_count} | Interval: {interval}s"
            )

            live.update(Align.center(panel))

            # Incrementa contador e reinicia Tor silenciosamente
            change_count += 1
            time.sleep(interval)
            restart_tor_service()  # sem print extra no terminal

if __name__ == "__main__":
    main()


