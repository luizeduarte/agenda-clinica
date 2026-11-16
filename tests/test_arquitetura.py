"""Verifica a regra de dependência (docs/arquitetura.md seção 4.1).

Domínio, aplicação e portas não podem importar infraestrutura, API nem
bibliotecas de tecnologia (SQLite, FastAPI). Mantém o código coerente com o
diagrama de componentes.
"""
import ast
import importlib
import pkgutil
from pathlib import Path

import clinica

RAIZ = Path(clinica.__file__).parent
CAMADAS_INTERNAS = {"dominio", "aplicacao", "portas"}
PROIBIDOS = ("clinica.infraestrutura", "clinica.api", "sqlite3", "fastapi", "uvicorn")


def _arquivos_das_camadas_internas():
    for caminho in (RAIZ / "modulos").rglob("*.py"):
        if CAMADAS_INTERNAS & set(caminho.relative_to(RAIZ).parts):
            yield caminho


def _imports(caminho: Path):
    for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            yield from (alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            yield no.module


def test_camadas_internas_nao_dependem_de_infraestrutura_nem_de_tecnologia():
    violacoes = [
        f"{caminho.relative_to(RAIZ)} importa {nome}"
        for caminho in _arquivos_das_camadas_internas()
        for nome in _imports(caminho)
        if nome.startswith(PROIBIDOS)
    ]
    assert not violacoes, "\n".join(violacoes)


def test_todos_os_modulos_importam():
    for info in pkgutil.walk_packages(clinica.__path__, "clinica."):
        importlib.import_module(info.name)
