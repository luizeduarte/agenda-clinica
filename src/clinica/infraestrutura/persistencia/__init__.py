"""Persistência em SQLite.

Ponto de entrada para a composição da aplicação::

    inicializar_banco("clinica.db")
    banco = ConexaoSQLite("clinica.db")
"""
from clinica.infraestrutura.persistencia.conexao import ConexaoSQLite, inicializar_banco

__all__ = ["ConexaoSQLite", "inicializar_banco"]
