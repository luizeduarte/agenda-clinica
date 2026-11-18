import sqlite3
from datetime import datetime, time

from clinica.infraestrutura.persistencia.conversao import para_texto
from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento
from clinica.modulos.agenda.portas.agenda_repositorio import AgendaRepositorio


class SQLiteAgendaRepositorio(AgendaRepositorio):
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
                l["dia_semana"], time.fromisoformat(l["hora_inicio"]), time.fromisoformat(l["hora_fim"])
            )
            for l in linhas
        ]

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
            Bloqueio(datetime.fromisoformat(l["inicio"]), datetime.fromisoformat(l["fim"]), l["motivo"], l["id"])
            for l in linhas
        ]
