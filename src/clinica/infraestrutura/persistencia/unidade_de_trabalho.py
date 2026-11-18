import threading
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

    Uma única instância atende todas as requisições. Para uma não interferir na
    outra, a conexão fica guardada por thread: cada thread que entra no
    ``with`` tem a sua conexão e a sua transação.

    Sair sem ``commit()``, ou por exceção, desfaz tudo.
    """

    def __init__(self, caminho: str | Path) -> None:
        self._caminho = caminho
        self._local = threading.local()

    def __enter__(self) -> Self:
        if getattr(self._local, "conexao", None) is not None:
            raise RuntimeError("Esta unidade de trabalho já está aberta nesta thread.")
        conexao = abrir_conexao(self._caminho)
        try:
            conexao.execute("BEGIN IMMEDIATE")
        except Exception:
            conexao.close()
            raise
        self._local.conexao = conexao
        self._local.aberta = True
        return self

    def __exit__(self, tipo_exc, exc, tb) -> None:
        conexao = self._local.conexao
        try:
            self.rollback()
        finally:
            conexao.close()
            self._local.conexao = None

    def commit(self) -> None:
        if self._local.aberta:
            self._local.conexao.execute("COMMIT")
            self._local.aberta = False

    def rollback(self) -> None:
        if self._local.aberta:
            self._local.conexao.execute("ROLLBACK")
            self._local.aberta = False

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
