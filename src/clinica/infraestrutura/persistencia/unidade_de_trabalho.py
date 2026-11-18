import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Self

from clinica.infraestrutura.persistencia.agenda_repositorio import SQLiteAgendaRepositorio
from clinica.infraestrutura.persistencia.cadastros_repositorios import (
    SQLitePacienteRepositorio,
    SQLiteProfissionalRepositorio,
)
from clinica.infraestrutura.persistencia.conexao import abrir_conexao
from clinica.infraestrutura.persistencia.consulta_repositorio import SQLiteConsultaRepositorio
from clinica.infraestrutura.persistencia.notificacao_pendente_repositorio import (
    SQLiteNotificacaoPendenteRepositorio,
)


class SQLiteUnidadeDeTrabalho:
    """Implementa ``UnidadeDeTrabalho`` com uma transação SQLite.

    Ao entrar, abre uma conexão e inicia ``BEGIN IMMEDIATE`` (ADR-003): o
    bloqueio de escrita é tomado antes das verificações de disponibilidade,
    então duas reservas concorrentes são serializadas. Todos os repositórios
    usam essa conexão, logo participam da mesma transação (ADR-002).
    ``leitura()`` usa ``BEGIN`` diferido e impede escritas na própria conexão.

    Uma única instância atende todas as requisições. Para uma não interferir na
    outra, a conexão fica guardada por thread: cada thread que entra no
    ``with`` tem a sua conexão e a sua transação.

    Sair sem ``commit()``, ou por exceção, desfaz tudo.
    """

    def __init__(self, caminho: str | Path) -> None:
        self._caminho = caminho
        self._local = threading.local()

    def __enter__(self) -> Self:
        return self._iniciar(somente_leitura=False)

    @contextmanager
    def leitura(self) -> Iterator[Self]:
        self._iniciar(somente_leitura=True)
        try:
            yield self
        finally:
            self._encerrar()

    def _iniciar(self, *, somente_leitura: bool) -> Self:
        if getattr(self._local, "conexao", None) is not None:
            raise RuntimeError("Esta unidade de trabalho já está aberta nesta thread.")
        conexao = abrir_conexao(self._caminho)
        try:
            if somente_leitura:
                conexao.execute("PRAGMA query_only = ON")
            conexao.execute("BEGIN" if somente_leitura else "BEGIN IMMEDIATE")
        except Exception:
            conexao.close()
            raise
        self._local.conexao = conexao
        return self

    def __exit__(self, tipo_exc, exc, tb) -> None:
        self._encerrar()

    def _encerrar(self) -> None:
        conexao = self._conexao
        try:
            self.rollback()
        finally:
            conexao.close()
            self._local.conexao = None

    def commit(self) -> None:
        if self._conexao.in_transaction:
            self._conexao.execute("COMMIT")

    def rollback(self) -> None:
        if self._conexao.in_transaction:
            self._conexao.execute("ROLLBACK")

    # --- repositórios (todos sobre a conexão desta thread) -----------------

    @property
    def _conexao(self):
        conexao = getattr(self._local, "conexao", None)
        if conexao is None:
            raise RuntimeError("Use a unidade de trabalho dentro de um bloco 'with'.")
        return conexao

    @property
    def consultas(self) -> SQLiteConsultaRepositorio:
        return SQLiteConsultaRepositorio(self._conexao)

    @property
    def agendas(self) -> SQLiteAgendaRepositorio:
        return SQLiteAgendaRepositorio(self._conexao)

    @property
    def pacientes(self) -> SQLitePacienteRepositorio:
        return SQLitePacienteRepositorio(self._conexao)

    @property
    def profissionais(self) -> SQLiteProfissionalRepositorio:
        return SQLiteProfissionalRepositorio(self._conexao)

    @property
    def notificacoes_pendentes(self) -> SQLiteNotificacaoPendenteRepositorio:
        return SQLiteNotificacaoPendenteRepositorio(self._conexao)
