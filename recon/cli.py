from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from dataclasses import asdict

from .core import enumerate_domain


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="recon", description="Inventário passivo de subdomínios via Certificate Transparency.")
    p.add_argument("dominio")
    p.add_argument("--sem-dns", action="store_true", help="só lista, não resolve os nomes")
    p.add_argument("--vivos", action="store_true", help="mostra só os que resolvem para um IP")
    p.add_argument("-o", "--saida", help="salva em .json ou .txt")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        hosts = enumerate_domain(args.dominio, do_resolve=not args.sem_dns)
    except ValueError as exc:
        print(f"  {exc}", file=sys.stderr)
        return 2
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  o crt.sh não respondeu ({exc}), ele costuma ficar lento, tente de novo", file=sys.stderr)
        return 3

    if args.vivos:
        hosts = [h for h in hosts if h.alive]
    print(f"\n  {len(hosts)} subdomínio(s) para {args.dominio}\n")
    for h in hosts:
        ips = ", ".join(h.ips[:3]) if h.ips else ("" if args.sem_dns else "não resolve")
        tags = f"  [{', '.join(h.tags)}]" if h.tags else ""
        print(f"  {h.name:<45}{ips}{tags}")
    flagged = [h for h in hosts if h.tags]
    if flagged:
        print(f"\n  {len(flagged)} nome(s) que costumam merecer revisão (ambiente de teste, painel, CI)")
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as fh:
            if args.saida.endswith(".json"):
                json.dump([asdict(h) for h in hosts], fh, ensure_ascii=False, indent=2)
            else:
                fh.write("\n".join(h.name for h in hosts) + "\n")
        print(f"  salvo em {args.saida}")
    print()
    return 0
