import pytest

from recon.core import enumerate_domain, extract_names, tag, validate_domain

REGISTROS = [
    {"name_value": "exemplo.com.br\nwww.exemplo.com.br"},
    {"name_value": "*.api.exemplo.com.br"},
    {"name_value": "homolog.exemplo.com.br"},
    {"name_value": "outrosite.com.br"},
    {"name_value": "WWW.EXEMPLO.COM.BR"},
]


def test_extrai_sem_repetir_e_sem_dominio_alheio():
    nomes = extract_names(REGISTROS, "exemplo.com.br")
    assert nomes == ["api.exemplo.com.br", "exemplo.com.br", "homolog.exemplo.com.br", "www.exemplo.com.br"]


def test_valida_dominio():
    assert validate_domain("https://Exemplo.com.br/") == "exemplo.com.br"
    with pytest.raises(ValueError):
        validate_domain("nao é domínio")


def test_marca_nomes_interessantes():
    assert tag("homolog.exemplo.com.br") == ["homolog"]
    assert tag("dev-api.exemplo.com.br") == ["dev", "api"]
    assert tag("www.exemplo.com.br") == []


def test_fluxo_completo_sem_internet():
    fake_dns = {"www.exemplo.com.br": ["192.0.2.10"]}
    hosts = enumerate_domain("exemplo.com.br", fetch=lambda d: REGISTROS,
                             resolver=lambda n: fake_dns.get(n, []))
    vivos = [h.name for h in hosts if h.alive]
    assert vivos == ["www.exemplo.com.br"]
    assert len(hosts) == 4
