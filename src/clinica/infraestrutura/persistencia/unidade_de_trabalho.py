import threading
from pathlib import Path

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
from clinica.modulos.agenda.portas.agenda_repositorio import AgendaRepositorio
from clinica.modulos.cadastros.portas.repositorios import (
    PacienteRepositorio,
    ProfissionalRepositorio,
)
from clinica.modulos.consultas.portas.consulta_repositorio import ConsultaRepositorio
from clinica.modulos.consultas.portas.unidade_de_trabalho import UnidadeDeTrabalho
from clinica.modulos.notificacoes.portas.notificacao_pendente_repositorio import (
    NotificacaoPendenteRepositorio,
)


class SQLiteUnidadeDeTrabalho(UnidadeDeTrabalho):
    """Implementa ``UnidadeDeTrabalho`` com uma transação SQLite.

    Ao entrar, abre uma conexão e inicia ``BEGIN IMMEDIATE`` (ADR-003): o
    bloqueio de escrita é tomado antes das verificações de disponibilidade,
    então duas reservas concorrentes são serializadas. Todos os repositórios
    usam essa conexão, logo participam da mesma transação (ADR-002).

    Uma única instância atende todas as requisições. Para uma não interferir na
    outra, a conexão fica guardada por thread: cada thread que entra no
    ``with`` tem a sua conexão e a sua transação.

    Sair sem ``commit()``, ou por exceção, desfaz tudo.

    Em ``somente_leitura()`` a transação abre com ``BEGIN`` comum, sem o
    bloqueio de escrita, e a conexão recusa gravações (``query_only``).
    """

    def __init__(self, caminho: str | Path) -> None:
        self._caminho = caminho
        self._local = threading.local()

    def iniciar(self, somente_leitura: bool = False) -> None:
        if getattr(self._local, "conexao", None) is not None:
            raise RuntimeError("Esta unidade de trabalho já está aberta nesta thread.")
        conexao = abrir_conexao(self._caminho)
        try:
            if somente_leitura:
                # Leitura não disputa o bloqueio de escrita: com WAL, um BEGIN
                # comum já enxerga um retrato consistente do banco sem esperar
                # nem atrasar as reservas. query_only faz qualquer gravação falhar.
                conexao.execute("PRAGMA query_only = ON")
                conexao.execute("BEGIN")
            else:
                conexao.execute("BEGIN IMMEDIATE")
        except Exception:
            conexao.close()
            raise
        self._local.conexao = conexao
        self._local.aberta = True
        self._local.consultas = SQLiteConsultaRepositorio(conexao)
        self._local.agendas = SQLiteAgendaRepositorio(conexao)
        self._local.pacientes = SQLitePacienteRepositorio(conexao)
        self._local.profissionais = SQLiteProfissionalRepositorio(conexao)
        self._local.notificacoes_pendentes = SQLiteNotificacaoPendenteRepositorio(conexao)

    def _fechar(self) -> None:
        conexao = getattr(self._local, "conexao", None)
        if conexao is not None:
            conexao.close()
        self._local.conexao = None
        self._local.aberta = False
        self._local.consultas = None
        self._local.agendas = None
        self._local.pacientes = None
        self._local.profissionais = None
        self._local.notificacoes_pendentes = None

    def commit(self) -> None:
        if getattr(self._local, "aberta", False):
            self._local.conexao.execute("COMMIT")
            self._local.aberta = False

    def rollback(self) -> None:
        if getattr(self._local, "aberta", False):
            self._local.conexao.execute("ROLLBACK")
            self._local.aberta = False

    # --- repositórios (todos sobre a conexão desta thread) -----------------

    def _da_thread(self) -> threading.local:
        """Estado desta thread; só existe dentro do bloco ``with``."""
        if getattr(self._local, "conexao", None) is None:
            raise RuntimeError("Use a unidade de trabalho dentro de um bloco 'with'.")
        return self._local

    @property
    def consultas(self) -> ConsultaRepositorio:
        return self._da_thread().consultas

    @property
    def agendas(self) -> AgendaRepositorio:
        return self._da_thread().agendas

    @property
    def pacientes(self) -> PacienteRepositorio:
        return self._da_thread().pacientes

    @property
    def profissionais(self) -> ProfissionalRepositorio:
        return self._da_thread().profissionais

    @property
    def notificacoes_pendentes(self) -> NotificacaoPendenteRepositorio:
        return self._da_thread().notificacoes_pendentes
