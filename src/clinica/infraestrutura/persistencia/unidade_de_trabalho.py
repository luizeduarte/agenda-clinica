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
    """Implementa ``UnidadeDeTrabalho``: uma conexão e uma transação por ``with``.

    Ao entrar, abre a conexão e inicia ``BEGIN IMMEDIATE`` (ADR-003): o bloqueio
    de escrita é tomado *antes* das verificações de disponibilidade, então duas
    reservas concorrentes são serializadas. Todos os repositórios usam a mesma
    conexão, logo participam da mesma transação (ADR-002).

    Sair sem ``commit()``, ou por exceção, desfaz tudo.
    """

    def __init__(self, caminho: str | Path) -> None:
        self._caminho = caminho
        self._con = None
        self._aberta = False

    def __enter__(self) -> Self:
        self._con = abrir_conexao(self._caminho)
        try:
            self._con.execute("BEGIN IMMEDIATE")
        except Exception:
            self._con.close()
            raise
        self._aberta = True
        self.consultas = SQLiteConsultaRepositorio(self._con)
        self.agendas = SQLiteAgendaRepositorio(self._con)
        self.pacientes = SQLitePacienteRepositorio(self._con)
        self.profissionais = SQLiteProfissionalRepositorio(self._con)
        self.notificacoes_pendentes = SQLiteNotificacaoPendenteRepositorio(self._con)
        return self

    def __exit__(self, tipo_exc, exc, tb) -> None:
        try:
            self.rollback()
        finally:
            self._con.close()

    def commit(self) -> None:
        if self._aberta:
            self._con.execute("COMMIT")
            self._aberta = False

    def rollback(self) -> None:
        if self._aberta:
            self._con.execute("ROLLBACK")
            self._aberta = False
