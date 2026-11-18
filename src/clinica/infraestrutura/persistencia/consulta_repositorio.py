import sqlite3
from datetime import datetime

from clinica.compartilhado.erros import ConflitoDePersistenciaError
from clinica.infraestrutura.persistencia.conversao import para_texto
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.dominio.consulta import Consulta, StatusConsulta
from clinica.modulos.consultas.portas.consulta_repositorio import ConsultaRepositorio

_ATIVAS = "status IN ('AGENDADA', 'CONFIRMADA')"


class SQLiteConsultaRepositorio(ConsultaRepositorio):
    """Implementa ``ConsultaRepositorio`` sobre a conexão da unidade de trabalho."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._con = conexao

    @staticmethod
    def _para_consulta(linha: sqlite3.Row) -> Consulta:
        return Consulta(
            id=linha["id"],
            paciente_id=linha["paciente_id"],
            profissional_id=linha["profissional_id"],
            especialidade_id=linha["especialidade_id"],
            slot=Slot(datetime.fromisoformat(linha["inicio"]), datetime.fromisoformat(linha["fim"])),
            status=StatusConsulta(linha["status"]),
        )

    @staticmethod
    def _traduzir(erro: sqlite3.IntegrityError) -> Exception:
        """Converte a violação de um índice único de reserva em ``ConflitoDePersistenciaError``"""
        mensagem = str(erro)
        if "UNIQUE" in mensagem and "consulta.profissional_id" in mensagem:
            return ConflitoDePersistenciaError("profissional")
        if "UNIQUE" in mensagem and "consulta.paciente_id" in mensagem:
            return ConflitoDePersistenciaError("paciente")
        return erro

    def adicionar(self, consulta: Consulta) -> Consulta:
        try:
            cursor = self._con.execute(
                "INSERT INTO consulta"
                " (paciente_id, profissional_id, especialidade_id, inicio, fim, status)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    consulta.paciente_id,
                    consulta.profissional_id,
                    consulta.especialidade_id,
                    para_texto(consulta.slot.inicio),
                    para_texto(consulta.slot.fim),
                    consulta.status.value,
                ),
            )
        except sqlite3.IntegrityError as erro:
            raise self._traduzir(erro) from erro
        consulta.id = cursor.lastrowid
        return consulta

    def listar_consultas_ativas_profissional(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Consulta]:
        linhas = self._con.execute(
            f"SELECT * FROM consulta WHERE {_ATIVAS} AND profissional_id = ?"
            " AND inicio < ? AND fim > ? ORDER BY inicio",
            (profissional_id, para_texto(fim), para_texto(inicio)),
        )
        return [self._para_consulta(linha) for linha in linhas]

    def listar_consultas_ativas_paciente(self, paciente_id: int) -> list[Consulta]:
        linhas = self._con.execute(
            f"SELECT * FROM consulta WHERE {_ATIVAS} AND paciente_id = ? ORDER BY inicio",
            (paciente_id,),
        )
        return [self._para_consulta(linha) for linha in linhas]
