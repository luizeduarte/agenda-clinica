import pytest

from clinica.infraestrutura.persistencia import criar_uow_factory, inicializar_banco
from clinica.infraestrutura.persistencia.conexao import abrir_conexao
from clinica.infraestrutura.persistencia.dados_exemplo import popular_dados_de_exemplo
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.dominio.consulta import Consulta
from clinica.modulos.notificacoes.dominio.notificacao import (
    Notificacao,
    NotificacaoPendente,
    TipoNotificacao,
)
from datetime import datetime


@pytest.fixture
def caminho(tmp_path):
    caminho = tmp_path / "uow.db"
    inicializar_banco(caminho)
    popular_dados_de_exemplo(caminho)
    return caminho


def contar(caminho, tabela):
    con = abrir_conexao(caminho)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
    finally:
        con.close()


def consulta():
    return Consulta(7, 10, 1, Slot.a_partir_de(datetime(2026, 12, 1, 10, 0)))


def pendente():
    return NotificacaoPendente(Notificacao("a@x", TipoNotificacao.AGENDAMENTO, "oi"))


def test_commit_torna_as_alteracoes_visiveis_para_outras_conexoes(caminho):
    with criar_uow_factory(caminho)() as uow:
        uow.consultas.adicionar(consulta())
        uow.commit()

    assert contar(caminho, "consulta") == 1


def test_sair_sem_commit_desfaz(caminho):
    with criar_uow_factory(caminho)() as uow:
        uow.consultas.adicionar(consulta())

    assert contar(caminho, "consulta") == 0


def test_excecao_desfaz(caminho):
    with pytest.raises(RuntimeError):
        with criar_uow_factory(caminho)() as uow:
            uow.consultas.adicionar(consulta())
            raise RuntimeError("falhou")

    assert contar(caminho, "consulta") == 0


def test_alteracoes_nao_confirmadas_nao_aparecem_em_outra_conexao(caminho):
    with criar_uow_factory(caminho)() as uow:
        uow.consultas.adicionar(consulta())
        assert contar(caminho, "consulta") == 0  # outra conexão ainda não vê
        uow.commit()
    assert contar(caminho, "consulta") == 1


def test_consulta_e_pendencia_compartilham_a_transacao(caminho):
    """ASR-03: não pode sobrar consulta sem a notificação correspondente."""
    with pytest.raises(RuntimeError):
        with criar_uow_factory(caminho)() as uow:
            uow.consultas.adicionar(consulta())
            uow.notificacoes_pendentes.adicionar(pendente())
            raise RuntimeError("falhou antes do commit")

    assert contar(caminho, "consulta") == 0
    assert contar(caminho, "notificacao_pendente") == 0


def test_consulta_e_pendencia_confirmadas_juntas(caminho):
    with criar_uow_factory(caminho)() as uow:
        uow.consultas.adicionar(consulta())
        uow.notificacoes_pendentes.adicionar(pendente())
        uow.commit()

    assert contar(caminho, "consulta") == 1
    assert contar(caminho, "notificacao_pendente") == 1


def test_a_conexao_e_fechada_ao_sair(caminho):
    uow = criar_uow_factory(caminho)()
    with uow:
        con = uow._con
    with pytest.raises(Exception, match="closed"):
        con.execute("SELECT 1")


def test_commit_duas_vezes_ou_rollback_depois_do_commit_e_inofensivo(caminho):
    with criar_uow_factory(caminho)() as uow:
        uow.consultas.adicionar(consulta())
        uow.commit()
        uow.commit()
        uow.rollback()

    assert contar(caminho, "consulta") == 1


def test_popular_dados_de_exemplo_e_idempotente(caminho):
    popular_dados_de_exemplo(caminho)
    assert contar(caminho, "paciente") == 2
    assert contar(caminho, "horario_atendimento") == 2 * 10  # 2 profissionais x 5 dias x 2 períodos
