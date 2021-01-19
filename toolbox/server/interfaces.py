import netifaces
import ipaddress
from typing import Optional


def allowed_interfaces():
    return ["tun0", "tun1", "lo", "lo0"]


def get_ip_address(interface: str) -> Optional[str]:
    try:
        return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]
    except (KeyError, ValueError):
        return None


def is_valid_ipv4_address(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False
