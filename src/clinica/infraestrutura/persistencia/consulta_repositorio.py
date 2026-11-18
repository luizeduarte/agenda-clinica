import sqlite3
from datetime import datetime

from clinica.compartilhado.erros import ConflitoDePersistenciaError
from clinica.infraestrutura.persistencia.conversao import para_texto
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.dominio.consulta import Consulta, StatusConsulta

_ATIVAS = "status IN ('AGENDADA', 'CONFIRMADA')"
_RESTRICOES_DE_RESERVA = {
    "UNIQUE constraint failed: consulta.profissional_id, consulta.inicio": "profissional",
    "UNIQUE constraint failed: consulta.paciente_id, consulta.inicio": "paciente",
}


def _para_consulta(linha: sqlite3.Row) -> Consulta:
    return Consulta(
        id=linha["id"],
        paciente_id=linha["paciente_id"],
        profissional_id=linha["profissional_id"],
        especialidade_id=linha["especialidade_id"],
        slot=Slot(datetime.fromisoformat(linha["inicio"]), datetime.fromisoformat(linha["fim"])),
        status=StatusConsulta(linha["status"]),
    )


class SQLiteConsultaRepositorio:
    """Implementa ``ConsultaRepositorio`` sobre a conexão da unidade de trabalho."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._con = conexao

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
            if erro.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
                participante = _RESTRICOES_DE_RESERVA.get(str(erro))
                if participante is not None:
                    raise ConflitoDePersistenciaError(participante) from erro
            raise
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
        return [_para_consulta(linha) for linha in linhas]

    def listar_consultas_ativas_paciente(self, paciente_id: int) -> list[Consulta]:
        linhas = self._con.execute(
            f"SELECT * FROM consulta WHERE {_ATIVAS} AND paciente_id = ? ORDER BY inicio",
            (paciente_id,),
        )
        return [_para_consulta(linha) for linha in linhas]
