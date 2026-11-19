"""Conexão SQLite, criação do esquema e controle transparente de transação."""
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ESQUEMA = Path(__file__).with_name("esquema.sql")
ESPERA_MAXIMA_MS = 5000


def abrir_conexao(caminho: str | Path) -> sqlite3.Connection:
    """Abre uma conexão com controle manual de transação.

    ``isolation_level=None`` desliga os BEGIN automáticos do módulo ``sqlite3``;
    quem decide quando a transação começa é a ``ConexaoSQLite``
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


class ConexaoSQLite:
    """Gerencia conexões e transações SQLite por thread de forma transparente.

    Dentro de ``with banco.transacao():``, leituras e escritas na mesma thread
    compartilham a mesma conexão e transação ``BEGIN IMMEDIATE`` (ASR-01, ASR-03).
    Fora de uma transação explícita, leituras abrem um retrato somente-leitura e
    escritas abrem e confirmam sua própria transação.
    """

    def __init__(self, caminho: str | Path) -> None:
        self._caminho = caminho
        self._local = threading.local()

    @contextmanager
    def transacao(self) -> Iterator[sqlite3.Connection]:
        if getattr(self._local, "conexao", None) is not None:
            raise RuntimeError("Já existe uma transação ativa nesta thread.")
        conexao = abrir_conexao(self._caminho)
        try:
            conexao.execute("BEGIN IMMEDIATE")
            self._local.conexao = conexao
            yield conexao
            if conexao.in_transaction:
                conexao.execute("COMMIT")
        except BaseException:
            if conexao.in_transaction:
                conexao.execute("ROLLBACK")
            raise
        finally:
            self._local.conexao = None
            conexao.close()

    @contextmanager
    def leitura(self) -> Iterator[sqlite3.Connection]:
        ativa = getattr(self._local, "conexao", None)
        if ativa is not None:
            yield ativa
            return
        conexao = abrir_conexao(self._caminho)
        try:
            conexao.execute("PRAGMA query_only = ON")
            conexao.execute("BEGIN")
            self._local.conexao = conexao
            yield conexao
        finally:
            if conexao.in_transaction:
                conexao.execute("ROLLBACK")
            self._local.conexao = None
            conexao.close()

    @contextmanager
    def escrita(self) -> Iterator[sqlite3.Connection]:
        ativa = getattr(self._local, "conexao", None)
        if ativa is not None:
            yield ativa
            return
        with self.transacao() as conexao:
            yield conexao
