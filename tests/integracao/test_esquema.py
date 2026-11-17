import sqlite3

import pytest

from clinica.infraestrutura.persistencia.conexao import abrir_conexao, inicializar_banco


@pytest.fixture
def con(tmp_path):
    caminho = tmp_path / "clinica.db"
    inicializar_banco(caminho)
    conexao = abrir_conexao(caminho)
    conexao.execute("INSERT INTO especialidade VALUES (1, 'Clínica Geral')")
    conexao.execute("INSERT INTO profissional VALUES (10, 'Dr. João', 1), (11, 'Dra. Marta', 1)")
    conexao.execute("INSERT INTO paciente VALUES (7, 'Ana', 'a@x'), (8, 'Bia', 'b@x')")
    yield conexao
    conexao.close()


def inserir(con, paciente, profissional, inicio="2026-12-01T10:00:00", status="AGENDADA"):
    con.execute(
        "INSERT INTO consulta (paciente_id, profissional_id, especialidade_id, inicio, fim, status)"
        " VALUES (?, ?, 1, ?, '2026-12-01T10:30:00', ?)",
        (paciente, profissional, inicio, status),
    )


def test_inicializar_banco_pode_ser_repetido(tmp_path):
    inicializar_banco(tmp_path / "a.db")
    inicializar_banco(tmp_path / "a.db")


def test_barra_segunda_consulta_ativa_do_mesmo_profissional_e_horario(con):
    inserir(con, paciente=7, profissional=10)
    with pytest.raises(sqlite3.IntegrityError, match="profissional_id"):
        inserir(con, paciente=8, profissional=10)


def test_barra_segunda_consulta_ativa_do_mesmo_paciente_e_horario(con):
    inserir(con, paciente=7, profissional=10)
    with pytest.raises(sqlite3.IntegrityError, match="paciente_id"):
        inserir(con, paciente=7, profissional=11)


def test_confirmada_tambem_ocupa_o_horario(con):
    inserir(con, paciente=7, profissional=10, status="CONFIRMADA")
    with pytest.raises(sqlite3.IntegrityError):
        inserir(con, paciente=8, profissional=10)


@pytest.mark.parametrize("status", ["CANCELADA", "REALIZADA", "FALTOU"])
def test_consulta_nao_ativa_nao_bloqueia_o_horario(con, status):
    inserir(con, paciente=7, profissional=10, status=status)
    inserir(con, paciente=8, profissional=10)  # não levanta


def test_horarios_diferentes_nao_conflitam(con):
    inserir(con, paciente=7, profissional=10, inicio="2026-12-01T10:00:00")
    inserir(con, paciente=7, profissional=10, inicio="2026-12-01T10:30:00")


def test_status_invalido_e_rejeitado(con):
    with pytest.raises(sqlite3.IntegrityError):
        inserir(con, paciente=7, profissional=10, status="QUALQUER")


def test_chave_estrangeira_e_exigida(con):
    with pytest.raises(sqlite3.IntegrityError):
        inserir(con, paciente=999, profissional=10)
