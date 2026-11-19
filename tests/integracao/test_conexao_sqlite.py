import sqlite3
from contextlib import closing
from datetime import datetime

import pytest

from clinica.infraestrutura.persistencia import ConexaoSQLite, inicializar_banco
from clinica.infraestrutura.persistencia.conexao import abrir_conexao
from clinica.infraestrutura.persistencia.consulta_repositorio import SQLiteConsultaRepositorio
from clinica.infraestrutura.persistencia.dados_exemplo import popular_dados_de_exemplo
from clinica.infraestrutura.persistencia.notificacao_pendente_repositorio import (
    SQLiteNotificacaoPendenteRepositorio,
)
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.dominio.consulta import Consulta
from clinica.modulos.notificacoes.dominio.notificacao import (
    Notificacao,
    NotificacaoPendente,
    TipoNotificacao,
)


@pytest.fixture
def caminho(tmp_path):
    caminho = tmp_path / "transacao.db"
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
    banco = ConexaoSQLite(caminho)
    consultas = SQLiteConsultaRepositorio(banco)
    with consultas.transacao():
        consultas.adicionar(consulta())

    assert contar(caminho, "consulta") == 1


def test_somente_leitura_recusa_gravacao(caminho):
    banco = ConexaoSQLite(caminho)
    consultas = SQLiteConsultaRepositorio(banco)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        with banco.leitura():
            consultas.adicionar(consulta())

    assert contar(caminho, "consulta") == 0


def test_somente_leitura_enxerga_o_que_ja_foi_confirmado(caminho):
    banco = ConexaoSQLite(caminho)
    consultas = SQLiteConsultaRepositorio(banco)
    with consultas.transacao():
        consultas.adicionar(consulta())

    assert len(consultas.listar_consultas_ativas_paciente(7)) == 1


def test_excecao_desfaz(caminho):
    banco = ConexaoSQLite(caminho)
    consultas = SQLiteConsultaRepositorio(banco)
    with pytest.raises(RuntimeError):
        with consultas.transacao():
            consultas.adicionar(consulta())
            raise RuntimeError("falhou")

    assert contar(caminho, "consulta") == 0


def test_alteracoes_nao_confirmadas_nao_aparecem_em_outra_conexao(caminho):
    banco = ConexaoSQLite(caminho)
    consultas = SQLiteConsultaRepositorio(banco)
    with consultas.transacao():
        consultas.adicionar(consulta())
        assert contar(caminho, "consulta") == 0  # outra conexão ainda não vê
    assert contar(caminho, "consulta") == 1


def test_consulta_e_pendencia_compartilham_a_transacao(caminho):
    """ASR-03: não pode sobrar consulta sem a notificação correspondente."""
    banco = ConexaoSQLite(caminho)
    consultas = SQLiteConsultaRepositorio(banco)
    pendentes = SQLiteNotificacaoPendenteRepositorio(banco)
    with pytest.raises(RuntimeError):
        with consultas.transacao():
            consultas.adicionar(consulta())
            pendentes.adicionar(pendente())
            raise RuntimeError("falhou antes de concluir")

    assert contar(caminho, "consulta") == 0
    assert contar(caminho, "notificacao_pendente") == 0


def test_consulta_e_pendencia_confirmadas_juntas(caminho):
    banco = ConexaoSQLite(caminho)
    consultas = SQLiteConsultaRepositorio(banco)
    pendentes = SQLiteNotificacaoPendenteRepositorio(banco)
    with consultas.transacao():
        consultas.adicionar(consulta())
        pendentes.adicionar(pendente())

    assert contar(caminho, "consulta") == 1
    assert contar(caminho, "notificacao_pendente") == 1


def test_a_conexao_e_fechada_ao_sair(caminho):
    banco = ConexaoSQLite(caminho)
    with banco.transacao() as con:
        pass
    with pytest.raises(Exception, match="closed"):
        con.execute("SELECT 1")


def test_popular_dados_de_exemplo_e_idempotente(caminho):
    popular_dados_de_exemplo(caminho)
    assert contar(caminho, "paciente") == 2
    assert contar(caminho, "horario_atendimento") == 2 * 10  # 2 profissionais x 5 dias x 2 períodos


def test_nao_aceita_abrir_duas_transacoes_na_mesma_thread(caminho):
    banco = ConexaoSQLite(caminho)
    with banco.transacao():
        with pytest.raises(RuntimeError, match="Já existe uma transação ativa"):
            with banco.transacao():
                pass


def test_leitura_mantem_snapshot_sem_reservar_escrita(caminho):
    leitura = ConexaoSQLite(caminho)
    consultas_leitura = SQLiteConsultaRepositorio(leitura)
    pendentes_leitura = SQLiteNotificacaoPendenteRepositorio(leitura)

    escrita = ConexaoSQLite(caminho)
    consultas_escrita = SQLiteConsultaRepositorio(escrita)

    with leitura.leitura():
        assert consultas_leitura.listar_consultas_ativas_paciente(7) == []
        with escrita.transacao():
            consulta_registrada = consultas_escrita.adicionar(consulta())
        assert consultas_leitura.listar_consultas_ativas_paciente(7) == []

    with leitura.leitura():
        assert consultas_leitura.listar_consultas_ativas_paciente(7) == [consulta_registrada]
        with pytest.raises(sqlite3.OperationalError) as erro:
            pendentes_leitura.adicionar(pendente())
        assert erro.value.sqlite_errorcode == sqlite3.SQLITE_READONLY


def test_transacao_de_escrita_reserva_o_bloqueio_ao_entrar(caminho):
    banco = ConexaoSQLite(caminho)
    with banco.transacao(), closing(abrir_conexao(caminho)) as outra:
        outra.execute("PRAGMA busy_timeout = 0")
        with pytest.raises(sqlite3.OperationalError) as erro:
            outra.execute("BEGIN IMMEDIATE")
        assert erro.value.sqlite_errorcode == sqlite3.SQLITE_BUSY


def test_uma_instancia_compartilhada_da_a_cada_thread_a_sua_transacao(caminho):
    """A mesma instância atende todas as requisições, cada thread com a sua conexão."""
    import threading

    banco = ConexaoSQLite(caminho)
    consultas = SQLiteConsultaRepositorio(banco)
    conexoes = []
    largada = threading.Barrier(2)

    def trabalhar(paciente_id):
        largada.wait()
        with banco.transacao() as con:
            conexoes.append(con)
            consultas.adicionar(
                Consulta(paciente_id, 10, 1, Slot.a_partir_de(datetime(2026, 12, 1, paciente_id, 0)))
            )

    threads = [threading.Thread(target=trabalhar, args=(i,)) for i in (7, 8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert len(conexoes) == 2 and conexoes[0] is not conexoes[1]
    assert contar(caminho, "consulta") == 2
