"""Inventário passivo de subdomínios.

Todo certificado TLS emitido por uma autoridade pública vai para os logs de
Certificate Transparency, que qualquer um pode consultar. O crt.sh indexa
esses logs. Isso significa que dá para listar os subdomínios de um domínio
sem mandar um único pacote para os servidores dele.
"""
from __future__ import annotations

import json
import re
import socket
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

CRT_URL = "https://crt.sh/?q={}&output=json"
DOMAIN_RX = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
INTERESTING = ("dev", "staging", "homolog", "hml", "test", "teste", "qa", "admin", "painel", "vpn",
               "jenkins", "gitlab", "grafana", "kibana", "old", "legacy", "backup", "api", "internal")


@dataclass
class Host:
    name: str
    ips: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @property
    def alive(self) -> bool:
        return bool(self.ips)


def validate_domain(domain: str) -> str:
    domain = domain.strip().lower().rstrip(".")
    if domain.startswith(("http://", "https://")):
        domain = urllib.parse.urlparse(domain).hostname or ""
    if not DOMAIN_RX.match(domain):
        raise ValueError(f"{domain!r} não parece um domínio válido")
    return domain


def fetch_crtsh(domain: str, timeout: float = 30.0) -> list[dict]:
    url = CRT_URL.format(urllib.parse.quote(f"%.{domain}"))
    req = urllib.request.Request(url, headers={"User-Agent": "subdomain-recon-estudo/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body) if body.strip() else []


def extract_names(records: list[dict], domain: str) -> list[str]:
    """Um certificado pode cobrir vários nomes, um por linha em name_value."""
    names = set()
    for rec in records:
        for raw in str(rec.get("name_value", "")).splitlines():
            name = raw.strip().lower().lstrip("*.")
            if name == domain or name.endswith("." + domain):
                if DOMAIN_RX.match(name):
                    names.add(name)
    return sorted(names)


def tag(name: str) -> list[str]:
    labels = re.split(r"[.-]", name)
    return [word for word in INTERESTING if word in labels]


def resolve(name: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(name, None)
    except (socket.gaierror, UnicodeError):
        return []
    return sorted({info[4][0] for info in infos})


def enumerate_domain(domain: str, do_resolve: bool = True, workers: int = 30, fetch=fetch_crtsh,
                     resolver=resolve) -> list[Host]:
    domain = validate_domain(domain)
    names = extract_names(fetch(domain), domain)
    hosts = [Host(n, tags=tag(n)) for n in names]
    if do_resolve and hosts:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for host, ips in zip(hosts, pool.map(resolver, names)):
                host.ips = ips
    return hosts
