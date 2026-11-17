"""Persistência em SQLite.

Ponto de entrada para a composição da aplicação::

    inicializar_banco("clinica.db")
    uow_factory = criar_uow_factory("clinica.db")
    AgendarConsulta(uow_factory)
"""
from collections.abc import Callable
from pathlib import Path

from clinica.infraestrutura.persistencia.conexao import inicializar_banco
from clinica.infraestrutura.persistencia.unidade_de_trabalho import SQLiteUnidadeDeTrabalho

__all__ = ["SQLiteUnidadeDeTrabalho", "criar_uow_factory", "inicializar_banco"]


def criar_uow_factory(caminho: str | Path) -> Callable[[], SQLiteUnidadeDeTrabalho]:
    """Fábrica que os casos de uso chamam a cada execução (uma transação cada)."""
    return lambda: SQLiteUnidadeDeTrabalho(caminho)
