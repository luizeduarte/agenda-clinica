import sqlite3

from clinica.modulos.cadastros.dominio.cadastros import Especialidade, Paciente, Profissional
from clinica.modulos.cadastros.portas.repositorios import (
    PacienteRepositorio,
    ProfissionalRepositorio,
)

_SELECT_PROFISSIONAL = (
    "SELECT p.id, p.nome, e.id AS especialidade_id, e.nome AS especialidade_nome"
    " FROM profissional p JOIN especialidade e ON e.id = p.especialidade_id"
)


class SQLitePacienteRepositorio(PacienteRepositorio):
    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._con = conexao

    def obter_por_id(self, paciente_id: int) -> Paciente | None:
        linha = self._con.execute(
            "SELECT id, nome, email FROM paciente WHERE id = ?", (paciente_id,)
        ).fetchone()
        return Paciente(linha["id"], linha["nome"], linha["email"]) if linha else None


class SQLiteProfissionalRepositorio(ProfissionalRepositorio):
    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._con = conexao

    @staticmethod
    def _para_profissional(linha: sqlite3.Row) -> Profissional:
        return Profissional(
            linha["id"],
            linha["nome"],
            Especialidade(linha["especialidade_id"], linha["especialidade_nome"]),
        )

    def obter_por_id(self, profissional_id: int) -> Profissional | None:
        linha = self._con.execute(
            f"{_SELECT_PROFISSIONAL} WHERE p.id = ?", (profissional_id,)
        ).fetchone()
        return self._para_profissional(linha) if linha else None

    def listar_por_especialidade(self, nome_especialidade: str) -> list[Profissional]:
        linhas = self._con.execute(
            f"{_SELECT_PROFISSIONAL} WHERE e.nome = ? ORDER BY p.id", (nome_especialidade,)
        )
        return [self._para_profissional(linha) for linha in linhas]
