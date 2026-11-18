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
    """

    def __init__(self, caminho: str | Path) -> None:
        self._caminho = caminho
        self._local = threading.local()

    def iniciar(self) -> None:
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

    def _obter_repositorio(self, nome: str):
        if getattr(self._local, "conexao", None) is None:
            raise RuntimeError("Use a unidade de trabalho dentro de um bloco 'with'.")
        return getattr(self._local, nome)

    @property
    def consultas(self) -> ConsultaRepositorio:
        return self._obter_repositorio("consultas")

    @property
    def agendas(self) -> AgendaRepositorio:
        return self._obter_repositorio("agendas")

    @property
    def pacientes(self) -> PacienteRepositorio:
        return self._obter_repositorio("pacientes")

    @property
    def profissionais(self) -> ProfissionalRepositorio:
        return self._obter_repositorio("profissionais")

    @property
    def notificacoes_pendentes(self) -> NotificacaoPendenteRepositorio:
        return self._obter_repositorio("notificacoes_pendentes")
