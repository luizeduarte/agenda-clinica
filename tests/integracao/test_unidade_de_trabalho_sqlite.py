import sqlite3
from contextlib import closing

import pytest

from clinica.infraestrutura.persistencia import SQLiteUnidadeDeTrabalho, inicializar_banco
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
    with SQLiteUnidadeDeTrabalho(caminho) as uow:
        uow.consultas.adicionar(consulta())
        uow.commit()

    assert contar(caminho, "consulta") == 1


def test_sair_sem_commit_desfaz(caminho):
    with SQLiteUnidadeDeTrabalho(caminho) as uow:
        uow.consultas.adicionar(consulta())

    assert contar(caminho, "consulta") == 0


def test_excecao_desfaz(caminho):
    with pytest.raises(RuntimeError):
        with SQLiteUnidadeDeTrabalho(caminho) as uow:
            uow.consultas.adicionar(consulta())
            raise RuntimeError("falhou")

    assert contar(caminho, "consulta") == 0


def test_alteracoes_nao_confirmadas_nao_aparecem_em_outra_conexao(caminho):
    with SQLiteUnidadeDeTrabalho(caminho) as uow:
        uow.consultas.adicionar(consulta())
        assert contar(caminho, "consulta") == 0  # outra conexão ainda não vê
        uow.commit()
    assert contar(caminho, "consulta") == 1


def test_consulta_e_pendencia_compartilham_a_transacao(caminho):
    """ASR-03: não pode sobrar consulta sem a notificação correspondente."""
    with pytest.raises(RuntimeError):
        with SQLiteUnidadeDeTrabalho(caminho) as uow:
            uow.consultas.adicionar(consulta())
            uow.notificacoes_pendentes.adicionar(pendente())
            raise RuntimeError("falhou antes do commit")

    assert contar(caminho, "consulta") == 0
    assert contar(caminho, "notificacao_pendente") == 0


def test_consulta_e_pendencia_confirmadas_juntas(caminho):
    with SQLiteUnidadeDeTrabalho(caminho) as uow:
        uow.consultas.adicionar(consulta())
        uow.notificacoes_pendentes.adicionar(pendente())
        uow.commit()

    assert contar(caminho, "consulta") == 1
    assert contar(caminho, "notificacao_pendente") == 1


def test_a_conexao_e_fechada_ao_sair(caminho):
    uow = SQLiteUnidadeDeTrabalho(caminho)
    with uow:
        con = uow._local.conexao
    with pytest.raises(Exception, match="closed"):
        con.execute("SELECT 1")


def test_commit_duas_vezes_ou_rollback_depois_do_commit_e_inofensivo(caminho):
    with SQLiteUnidadeDeTrabalho(caminho) as uow:
        uow.consultas.adicionar(consulta())
        uow.commit()
        uow.commit()
        uow.rollback()

    assert contar(caminho, "consulta") == 1


def test_popular_dados_de_exemplo_e_idempotente(caminho):
    popular_dados_de_exemplo(caminho)
    assert contar(caminho, "paciente") == 2
    assert contar(caminho, "horario_atendimento") == 2 * 10  # 2 profissionais x 5 dias x 2 períodos


def test_usar_fora_do_with_e_um_erro_claro(caminho):
    uow = SQLiteUnidadeDeTrabalho(caminho)
    with pytest.raises(RuntimeError, match="with"):
        uow.consultas


def test_nao_aceita_abrir_duas_vezes_na_mesma_thread(caminho):
    with SQLiteUnidadeDeTrabalho(caminho) as uow:
        with pytest.raises(RuntimeError, match="já está aberta"):
            uow.__enter__()


def test_leitura_mantem_snapshot_sem_reservar_escrita(caminho):
    with SQLiteUnidadeDeTrabalho(caminho).leitura() as leitura:
        assert leitura.consultas.listar_consultas_ativas_paciente(7) == []
        with SQLiteUnidadeDeTrabalho(caminho) as escrita:
            consulta_registrada = escrita.consultas.adicionar(consulta())
            escrita.commit()
        assert leitura.consultas.listar_consultas_ativas_paciente(7) == []

    with SQLiteUnidadeDeTrabalho(caminho).leitura() as leitura:
        assert leitura.consultas.listar_consultas_ativas_paciente(7) == [consulta_registrada]
        with pytest.raises(sqlite3.OperationalError) as erro:
            leitura.notificacoes_pendentes.adicionar(pendente())
        assert erro.value.sqlite_errorcode == sqlite3.SQLITE_READONLY


def test_transacao_de_escrita_reserva_o_bloqueio_ao_entrar(caminho):
    with SQLiteUnidadeDeTrabalho(caminho), closing(abrir_conexao(caminho)) as outra:
        outra.execute("PRAGMA busy_timeout = 0")
        with pytest.raises(sqlite3.OperationalError) as erro:
            outra.execute("BEGIN IMMEDIATE")
        assert erro.value.sqlite_errorcode == sqlite3.SQLITE_BUSY


def test_uma_instancia_compartilhada_da_a_cada_thread_a_sua_transacao(caminho):
    """A mesma instância atende todas as requisições, cada thread com a sua conexão."""
    import threading

    uow = SQLiteUnidadeDeTrabalho(caminho)
    conexoes = []
    largada = threading.Barrier(2)

    def trabalhar(paciente_id):
        largada.wait()
        with uow:
            conexoes.append(uow._local.conexao)
            uow.consultas.adicionar(
                Consulta(paciente_id, 10, 1, Slot.a_partir_de(datetime(2026, 12, 1, paciente_id, 0)))
            )
            uow.commit()

    threads = [threading.Thread(target=trabalhar, args=(i,)) for i in (7, 8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert len(conexoes) == 2 and conexoes[0] is not conexoes[1]
    assert contar(caminho, "consulta") == 2
