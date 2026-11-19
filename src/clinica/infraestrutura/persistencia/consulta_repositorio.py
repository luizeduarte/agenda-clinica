import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from clinica.compartilhado.erros import ConflitoDePersistenciaError
from clinica.infraestrutura.persistencia.conexao import ConexaoSQLite
from clinica.infraestrutura.persistencia.conversao import para_texto
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.dominio.consulta import Consulta, StatusConsulta
from clinica.modulos.consultas.portas.consulta_repositorio import ConsultaRepositorio

_ATIVAS = "status IN ('AGENDADA', 'CONFIRMADA')"
_RESTRICOES_DE_RESERVA = {
    "UNIQUE constraint failed: consulta.profissional_id, consulta.inicio": "profissional",
    "UNIQUE constraint failed: consulta.paciente_id, consulta.inicio": "paciente",
}


class SQLiteConsultaRepositorio(ConsultaRepositorio):
    """Implementa ``ConsultaRepositorio`` sobre ``ConexaoSQLite``."""

    def __init__(self, banco: ConexaoSQLite | str | Path) -> None:
        self._banco = banco if isinstance(banco, ConexaoSQLite) else ConexaoSQLite(banco)

    @contextmanager
    def transacao(self) -> Iterator[None]:
        with self._banco.transacao():
            yield

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
        """Converte a violação de um índice único de reserva em ``ConflitoDePersistenciaError``."""
        if erro.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
            participante = _RESTRICOES_DE_RESERVA.get(str(erro))
            if participante is not None:
                return ConflitoDePersistenciaError(participante)
        return erro

    def adicionar(self, consulta: Consulta) -> Consulta:
        try:
            with self._banco.escrita() as con:
                cursor = con.execute(
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
        return replace(consulta, id=cursor.lastrowid)

    def listar_consultas_ativas_profissional(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Consulta]:
        with self._banco.leitura() as con:
            linhas = con.execute(
                f"SELECT * FROM consulta WHERE {_ATIVAS} AND profissional_id = ?"
                " AND inicio < ? AND fim > ? ORDER BY inicio",
                (profissional_id, para_texto(fim), para_texto(inicio)),
            ).fetchall()
        return [self._para_consulta(linha) for linha in linhas]

    def listar_consultas_ativas_paciente(self, paciente_id: int) -> list[Consulta]:
        with self._banco.leitura() as con:
            linhas = con.execute(
                f"SELECT * FROM consulta WHERE {_ATIVAS} AND paciente_id = ? ORDER BY inicio",
                (paciente_id,),
            ).fetchall()
        return [self._para_consulta(linha) for linha in linhas]
