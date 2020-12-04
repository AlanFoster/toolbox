from flask import (
    Blueprint,
    Flask,
    render_template,
    make_response,
    app,
    abort,
    current_app,
    request,
    redirect,
    url_for,
)
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import ipaddress
import netifaces
from pathlib import Path


TEMPLATE_DIRECTORY = Path(__file__).parent / "templates"


@dataclass
class DataStore:
    lhost: str
    lport: int
    srvhost_url: str


class PayloadGenerator:
    VALID_INTERFACES = ["tun0", "lo", "lo0"]

    def __init__(self):
        pass

    def generate(
        self, name: str, lhost: Optional[str], lport: Optional[str]
    ) -> Optional[str]:
        if name not in self:
            return None

        # TODO: Decide if it would be better to remove render_template and call jinja or similar directly
        payload = render_template(name, datastore=self._get_datastore(lhost, lport))
        return payload

    def __contains__(self, name):
        return name in self.template_names

    @property
    def template_names(self):
        # TODO: Decide if this should honor jinja's templates_auto_reload mechanism
        return [
            template.name
            for template in Path(TEMPLATE_DIRECTORY).iterdir()
            if template.name != "index.html"
        ]

    @property
    def default_lport(self) -> int:
        return 4444

    @property
    def default_lhost(self) -> str:
        for interface in PayloadGenerator.VALID_INTERFACES:
            result = self._get_ip_address(interface)
            if result is not None:
                return result
        raise ValueError(
            f"Unable to get ip address for default interfaces: '{str.join(PayloadGenerator.VALID_INTERFACES, ', ')}'"
        )

    def _get_datastore(self, lhost: Optional[str], lport: Optional[str]) -> DataStore:
        return DataStore(
            lhost=(lhost if lhost else self.default_lhost),
            lport=(int(lport) if lport else self.default_lport),
            srvhost_url=request.host_url,
        )

    def _is_valid_ipv4_address(self, ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def _get_ip_address(self, interface: str) -> Optional[str]:
        try:
            return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]
        except ValueError:
            return None

    def _get_lhost(self, lhost: Optional[str]) -> str:
        if lhost is None:
            return self.default_lhost()

        if lhost in PayloadGenerator.VALID_INTERFACES:
            address = self._get_ip_address(lhost)
            if address is None:
                raise ValueError(f"interface not found: '{lhost}'")
            return address

        if self.is_valid_ipv4_address(lhost):
            return lhost

        raise ValueError(f"Unexpected lhost: '{lhost}'")
