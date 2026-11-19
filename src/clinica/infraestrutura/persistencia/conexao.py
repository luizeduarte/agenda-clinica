"""Conexão SQLite e criação do esquema."""
import sqlite3
from pathlib import Path

ESQUEMA = Path(__file__).with_name("esquema.sql")
ESPERA_MAXIMA_MS = 5000


def abrir_conexao(caminho: str | Path) -> sqlite3.Connection:
    """Abre uma conexão com controle manual de transação.

    ``isolation_level=None`` desliga os BEGIN automáticos do módulo ``sqlite3``;
    quem decide quando a transação começa é a ``SQLiteUnidadeDeTrabalho``
    (``BEGIN IMMEDIATE`` para escrita, ADR-003, e ``BEGIN`` para leitura).
    """
    conexao = sqlite3.connect(caminho, isolation_level=None)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    # Escritas concorrentes esperam o bloqueio em vez de falhar na hora.
    conexao.execute(f"PRAGMA busy_timeout = {ESPERA_MAXIMA_MS}")
    return conexao


def inicializar_banco(caminho: str | Path) -> None:
    """Cria o esquema se ainda não existir. Pode ser chamado mais de uma vez."""
    conexao = abrir_conexao(caminho)
    try:
        # WAL: leitores (ex.: processador de notificações) não bloqueiam a escrita.
        conexao.execute("PRAGMA journal_mode = WAL")
        conexao.executescript(ESQUEMA.read_text(encoding="utf-8"))
    finally:
        conexao.close()
