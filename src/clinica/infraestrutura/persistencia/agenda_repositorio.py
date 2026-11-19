from datetime import datetime, time
from pathlib import Path

from clinica.infraestrutura.persistencia.conexao import ConexaoSQLite
from clinica.infraestrutura.persistencia.conversao import para_texto
from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento
from clinica.modulos.agenda.portas.agenda_repositorio import AgendaRepositorio


class SQLiteAgendaRepositorio(AgendaRepositorio):
    """Implementa ``AgendaRepositorio`` sobre ``ConexaoSQLite``."""

    def __init__(self, banco: ConexaoSQLite | str | Path) -> None:
        self._banco = banco if isinstance(banco, ConexaoSQLite) else ConexaoSQLite(banco)

    def obter_horarios_atendimento(self, profissional_id: int) -> list[HorarioAtendimento]:
        with self._banco.leitura() as con:
            linhas = con.execute(
                "SELECT dia_semana, hora_inicio, hora_fim FROM horario_atendimento"
                " WHERE profissional_id = ? ORDER BY dia_semana, hora_inicio",
                (profissional_id,),
            ).fetchall()
        return [
            HorarioAtendimento(
                l["dia_semana"], time.fromisoformat(l["hora_inicio"]), time.fromisoformat(l["hora_fim"])
            )
            for l in linhas
        ]

    def listar_bloqueios(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Bloqueio]:
        with self._banco.leitura() as con:
            linhas = con.execute(
                "SELECT * FROM bloqueio"
                " WHERE (profissional_id = ? OR profissional_id IS NULL)"
                " AND inicio < ? AND fim > ? ORDER BY inicio",
                (profissional_id, para_texto(fim), para_texto(inicio)),
            ).fetchall()
        return [
            Bloqueio(datetime.fromisoformat(l["inicio"]), datetime.fromisoformat(l["fim"]), l["motivo"], l["id"])
            for l in linhas
        ]
