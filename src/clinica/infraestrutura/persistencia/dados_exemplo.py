"""Dados de demonstração para o protótipo.

Não existe porta para cadastrar pacientes e profissionais (fora do recorte do
protótipo), então esta função insere direto no SQLite. É idempotente.
"""
from pathlib import Path

from clinica.infraestrutura.persistencia.conexao import abrir_conexao

ESPECIALIDADES = [(1, "Clínica Geral"), (2, "Odontologia")]
PROFISSIONAIS = [(10, "Dr. João", 1), (11, "Dra. Marta", 2)]
PACIENTES = [(7, "Ana", "ana@exemplo.com"), (8, "Bia", "bia@exemplo.com")]
# Segunda a sexta, manhã e tarde (0 = segunda).
PERIODOS = [("08:00", "12:00"), ("14:00", "18:00")]


def popular_dados_de_exemplo(caminho: str | Path) -> None:
    con = abrir_conexao(caminho)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.executemany("INSERT OR IGNORE INTO especialidade VALUES (?, ?)", ESPECIALIDADES)
        con.executemany("INSERT OR IGNORE INTO profissional VALUES (?, ?, ?)", PROFISSIONAIS)
        con.executemany("INSERT OR IGNORE INTO paciente VALUES (?, ?, ?)", PACIENTES)
        for profissional_id, _, _ in PROFISSIONAIS:
            ja_tem = con.execute(
                "SELECT 1 FROM horario_atendimento WHERE profissional_id = ?", (profissional_id,)
            ).fetchone()
            if ja_tem:
                continue
            con.executemany(
                "INSERT INTO horario_atendimento (profissional_id, dia_semana, hora_inicio, hora_fim)"
                " VALUES (?, ?, ?, ?)",
                [
                    (profissional_id, dia, inicio, fim)
                    for dia in range(5)
                    for inicio, fim in PERIODOS
                ],
            )
        con.execute("COMMIT")
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()
