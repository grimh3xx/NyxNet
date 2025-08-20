#!/usr/bin/env python3
import os
import platform
import sys

# ---------- Cores ----------
RED, GREEN, YELLOW, DEFAULT = '\033[1;31m', '\033[1;92m', '\033[1;33m', '\033[0m'

# ---------- Limpa a tela ----------
def clear_screen():
    os.system('clear')

# ---------- Checa se é root (Linux/macOS) ----------
def check_root():
    if os.name != 'nt':  # Não precisa de root no Windows
        if os.geteuid() != 0:
            print(f"{RED}[!]{DEFAULT} This script must be run as root.")
            sys.exit(1)

# ---------- Detecta sistema operacional ----------
def get_system():
    return platform.system()

# ---------- Verifica se comando existe no PATH ----------
def command_exists(command):
    from shutil import which
    return which(command) is not None
