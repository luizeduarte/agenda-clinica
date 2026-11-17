"""Persistência em SQLite.

Ponto de entrada para a composição da aplicação::

    inicializar_banco("clinica.db")
    uow = SQLiteUnidadeDeTrabalho("clinica.db")
    AgendarConsulta(uow)
"""
from clinica.infraestrutura.persistencia.conexao import inicializar_banco
from clinica.infraestrutura.persistencia.unidade_de_trabalho import SQLiteUnidadeDeTrabalho

__all__ = ["SQLiteUnidadeDeTrabalho", "inicializar_banco"]
