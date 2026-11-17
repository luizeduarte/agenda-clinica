import sqlite3
from dataclasses import replace
from datetime import datetime

from clinica.infraestrutura.persistencia.conversao import (
    de_texto,
    hora_de_texto,
    hora_para_texto,
    para_texto,
)
from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento


class SQLiteAgendaRepositorio:
    """Implementa ``AgendaRepositorio`` sobre a conexão da unidade de trabalho."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._con = conexao

    def obter_horarios_atendimento(self, profissional_id: int) -> list[HorarioAtendimento]:
        linhas = self._con.execute(
            "SELECT dia_semana, hora_inicio, hora_fim FROM horario_atendimento"
            " WHERE profissional_id = ? ORDER BY dia_semana, hora_inicio",
            (profissional_id,),
        )
        return [
            HorarioAtendimento(
                l["dia_semana"], hora_de_texto(l["hora_inicio"]), hora_de_texto(l["hora_fim"])
            )
            for l in linhas
        ]

    def salvar_horarios_atendimento(
        self, profissional_id: int, horarios: list[HorarioAtendimento]
    ) -> None:
        self._con.execute(
            "DELETE FROM horario_atendimento WHERE profissional_id = ?", (profissional_id,)
        )
        self._con.executemany(
            "INSERT INTO horario_atendimento (profissional_id, dia_semana, hora_inicio, hora_fim)"
            " VALUES (?, ?, ?, ?)",
            [
                (profissional_id, h.dia_semana, hora_para_texto(h.hora_inicio), hora_para_texto(h.hora_fim))
                for h in horarios
            ],
        )

    def listar_bloqueios(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Bloqueio]:
        linhas = self._con.execute(
            "SELECT * FROM bloqueio"
            " WHERE (profissional_id = ? OR profissional_id IS NULL)"
            " AND inicio < ? AND fim > ? ORDER BY inicio",
            (profissional_id, para_texto(fim), para_texto(inicio)),
        )
        return [
            Bloqueio(de_texto(l["inicio"]), de_texto(l["fim"]), l["motivo"], l["id"])
            for l in linhas
        ]

    def adicionar_bloqueio(self, profissional_id: int | None, bloqueio: Bloqueio) -> Bloqueio:
        cursor = self._con.execute(
            "INSERT INTO bloqueio (profissional_id, inicio, fim, motivo) VALUES (?, ?, ?, ?)",
            (profissional_id, para_texto(bloqueio.inicio), para_texto(bloqueio.fim), bloqueio.motivo),
        )
        return replace(bloqueio, id=cursor.lastrowid)
