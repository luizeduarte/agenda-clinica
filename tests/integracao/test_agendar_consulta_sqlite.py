"""`AgendarConsulta` ponta a ponta sobre o SQLite, incluindo concorrência (ASR-01)."""
import threading
from collections import Counter
from datetime import datetime, timedelta

import pytest

from clinica.compartilhado.erros import (
    HorarioIndisponivelError,
    NaoAutorizadoError,
    SlotInvalidoError,
)
from clinica.infraestrutura.persistencia import ConexaoSQLite, inicializar_banco
from clinica.infraestrutura.persistencia.agenda_repositorio import SQLiteAgendaRepositorio
from clinica.infraestrutura.persistencia.cadastros_repositorios import (
    SQLitePacienteRepositorio,
    SQLiteProfissionalRepositorio,
)
from clinica.infraestrutura.persistencia.conexao import abrir_conexao
from clinica.infraestrutura.persistencia.consulta_repositorio import SQLiteConsultaRepositorio
from clinica.infraestrutura.persistencia.dados_exemplo import popular_dados_de_exemplo
from clinica.infraestrutura.persistencia.notificacao_pendente_repositorio import (
    SQLiteNotificacaoPendenteRepositorio,
)
from clinica.modulos.agenda.aplicacao import ConsultarDisponibilidade
from clinica.modulos.agenda.contratos import Agenda, Slot
from clinica.modulos.autenticacao.contratos import Papel, Usuario
from clinica.modulos.cadastros.contratos import Cadastros
from clinica.modulos.consultas.aplicacao import AgendarConsulta, AgendarConsultaComando
from clinica.modulos.consultas.contratos import Consultas
from clinica.modulos.consultas.dominio.consulta import Consulta
from clinica.modulos.notificacoes.contratos import Notificacoes

AGORA = datetime(2026, 11, 20, 9, 0)
TERCA = datetime(2026, 12, 1)


def inicio(hora, minuto=0):
    return datetime(2026, 12, 1, hora, minuto)


def configurar_sqlite(caminho, pendentes_repo=None) -> tuple[ConexaoSQLite, SQLiteConsultaRepositorio]:
    banco = ConexaoSQLite(caminho)
    consultas_repo = SQLiteConsultaRepositorio(banco)
    Agenda.configurar(SQLiteAgendaRepositorio(banco))
    Cadastros.configurar(
        SQLitePacienteRepositorio(banco),
        SQLiteProfissionalRepositorio(banco),
    )
    Consultas.configurar(consultas_repo)
    Notificacoes.configurar(pendentes_repo or SQLiteNotificacaoPendenteRepositorio(banco))
    return banco, consultas_repo


@pytest.fixture
def caminho(tmp_path):
    caminho = tmp_path / "agendar.db"
    inicializar_banco(caminho)
    popular_dados_de_exemplo(caminho)
    return caminho


@pytest.fixture
def agendar(caminho):
    _, consultas_repo = configurar_sqlite(caminho)
    return AgendarConsulta(consultas_repo, relogio=lambda: AGORA)


def consultas_ativas(caminho):
    con = abrir_conexao(caminho)
    try:
        return con.execute(
            "SELECT paciente_id, profissional_id FROM consulta"
            " WHERE status IN ('AGENDADA', 'CONFIRMADA')"
        ).fetchall()
    finally:
        con.close()


def total(caminho, tabela):
    con = abrir_conexao(caminho)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
    finally:
        con.close()


def test_agenda_persiste_consulta_e_notificacao(agendar, caminho):
    consulta = agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, inicio(10)))

    assert consulta.id is not None
    assert len(consultas_ativas(caminho)) == 1
    assert total(caminho, "notificacao_pendente") == 1


@pytest.mark.parametrize("segundos_apos_inicio", [-1, 0, 1])
def test_revalida_horario_apos_obter_bloqueio_de_escrita(caminho, segundos_apos_inicio):
    _, consultas_repo = configurar_sqlite(caminho)
    horario = inicio(10)
    instante = [horario - timedelta(seconds=2)]
    validou = threading.Event()
    resultados = []

    def relogio():
        agora = instante[0]
        validou.set()
        return agora

    def executar():
        try:
            agendar = AgendarConsulta(consultas_repo, relogio=relogio)
            resultados.append(
                agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, horario))
            )
        except Exception as erro:
            resultados.append(erro)

    reserva = abrir_conexao(caminho)
    reserva.execute("BEGIN IMMEDIATE")
    thread = threading.Thread(target=executar)
    thread.start()
    try:
        assert validou.wait(timeout=5), "O pedido não chegou à validação inicial."
        instante[0] = horario + timedelta(seconds=segundos_apos_inicio)
    finally:
        reserva.execute("ROLLBACK")
        reserva.close()
        thread.join(timeout=10)

    assert not thread.is_alive(), "O pedido não terminou após liberar o bloqueio."
    (resultado,) = resultados
    if segundos_apos_inicio < 0:
        assert isinstance(resultado, Consulta), resultado
        assert total(caminho, "consulta") == total(caminho, "notificacao_pendente") == 1
    else:
        assert isinstance(resultado, SlotInvalidoError), resultado
        assert total(caminho, "consulta") == total(caminho, "notificacao_pendente") == 0


def test_horario_ocupado_nao_grava_nada_alem_da_primeira(agendar, caminho):
    agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, inicio(10)))

    with pytest.raises(HorarioIndisponivelError):
        agendar.executar(AgendarConsultaComando(Usuario(8, Papel.PACIENTE), 10, inicio(10)))

    assert len(consultas_ativas(caminho)) == 1
    assert total(caminho, "notificacao_pendente") == 1


def test_falha_ao_gravar_a_pendencia_desfaz_a_consulta(caminho):
    class PendentesComDefeito(SQLiteNotificacaoPendenteRepositorio):
        """Simula falha ao gravar a notificação pendente."""

        def adicionar(self, pendente):
            raise RuntimeError("banco indisponível")

    _, consultas_repo = configurar_sqlite(caminho, pendentes_repo=PendentesComDefeito(caminho))
    agendar = AgendarConsulta(consultas_repo, relogio=lambda: AGORA)

    with pytest.raises(RuntimeError):
        agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, inicio(10)))

    assert total(caminho, "consulta") == 0


def test_disponibilidade_reflete_o_que_foi_agendado(agendar, caminho):
    agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, inicio(8, 30)))

    (resultado,) = ConsultarDisponibilidade(relogio=lambda: AGORA).executar(
        TERCA.date(), profissional_id=10
    )

    inicios = [s.inicio for s in resultado.slots]
    assert inicio(8, 30) not in inicios
    assert inicio(8, 0) in inicios
    assert len(inicios) == 15  # 8 slots de manhã + 8 de tarde, menos o ocupado


def test_disponibilidade_nao_espera_uma_reserva_em_andamento(caminho):
    """A consulta de disponibilidade só lê: não disputa o bloqueio de escrita (ADR-003)."""
    configurar_sqlite(caminho)
    reserva = abrir_conexao(caminho)
    try:
        reserva.execute("BEGIN IMMEDIATE")  # outra requisição segurando o bloqueio de escrita
        (resultado,) = ConsultarDisponibilidade(relogio=lambda: AGORA).executar(
            TERCA.date(), profissional_id=10
        )
    finally:
        reserva.execute("ROLLBACK")
        reserva.close()

    assert len(resultado.slots) == 16


def test_consultar_disponibilidade_durante_uma_escrita(caminho):
    configurar_sqlite(caminho)
    consultar = ConsultarDisponibilidade(relogio=lambda: AGORA)
    banco_escrita = ConexaoSQLite(caminho)
    consultas_escrita = SQLiteConsultaRepositorio(banco_escrita)
    with banco_escrita.transacao():
        consultas_escrita.adicionar(Consulta(7, 10, 1, Slot.a_partir_de(inicio(10))))
        (resultado,) = consultar.executar(TERCA.date(), profissional_id=10)
        assert inicio(10) in [slot.inicio for slot in resultado.slots]

    (resultado,) = consultar.executar(TERCA.date(), profissional_id=10)
    assert inicio(10) not in [slot.inicio for slot in resultado.slots]


def _disparar_em_paralelo(tarefas):
    """Executa as tarefas ao mesmo tempo e devolve o resultado (ou a exceção) de cada uma."""
    largada = threading.Barrier(len(tarefas))
    resultados = [None] * len(tarefas)

    def rodar(i, tarefa):
        largada.wait()
        try:
            resultados[i] = tarefa()
        except Exception as erro:  # noqa: BLE001 - queremos ver qualquer falha
            resultados[i] = erro

    threads = [threading.Thread(target=rodar, args=(i, t)) for i, t in enumerate(tarefas)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return resultados


def test_asr01_pacientes_diferentes_disputam_o_mesmo_horario(caminho):
    """Oito pacientes tentam o mesmo slot do mesmo profissional: só um consegue."""
    con = abrir_conexao(caminho)
    con.executemany(
        "INSERT INTO paciente VALUES (?, ?, ?)", [(20 + i, f"P{i}", f"p{i}@x") for i in range(8)]
    )
    con.close()
    _, consultas_repo = configurar_sqlite(caminho)
    agendar = AgendarConsulta(consultas_repo, relogio=lambda: AGORA)

    resultados = _disparar_em_paralelo(
        [
            (lambda pid=20 + i: agendar.executar(AgendarConsultaComando(Usuario(pid, Papel.PACIENTE), 10, inicio(10))))
            for i in range(8)
        ]
    )

    tipos = Counter(type(r).__name__ for r in resultados)
    assert tipos == {"Consulta": 1, "HorarioIndisponivelError": 7}
    assert len(consultas_ativas(caminho)) == 1
    assert total(caminho, "notificacao_pendente") == 1


def test_asr01_mesmo_paciente_com_profissionais_diferentes_no_mesmo_horario(caminho):
    """O paciente não pode ficar em dois lugares ao mesmo tempo (RN03)."""
    _, consultas_repo = configurar_sqlite(caminho)
    agendar = AgendarConsulta(consultas_repo, relogio=lambda: AGORA)

    resultados = _disparar_em_paralelo(
        [
            lambda: agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, inicio(10))),
            lambda: agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 11, inicio(10))),
        ]
    )

    tipos = Counter(type(r).__name__ for r in resultados)
    assert tipos == {"Consulta": 1, "ConflitoDoPacienteError": 1}
    assert len(consultas_ativas(caminho)) == 1
    assert total(caminho, "notificacao_pendente") == 1


def test_asr01_mesmo_paciente_disputa_o_limite_por_especialidade(agendar, caminho):
    paciente = Usuario(7, Papel.PACIENTE)
    resultados = _disparar_em_paralelo(
        [
            lambda: agendar.executar(AgendarConsultaComando(paciente, 10, inicio(10))),
            lambda: agendar.executar(AgendarConsultaComando(paciente, 10, inicio(11))),
        ]
    )

    assert Counter(type(r).__name__ for r in resultados) == {"Consulta": 1, "LimiteDoPacienteExcedidoError": 1}
    assert total(caminho, "consulta") == total(caminho, "notificacao_pendente") == 1


def test_asr01_horarios_diferentes_nao_se_atrapalham(caminho):
    _, consultas_repo = configurar_sqlite(caminho)
    agendar = AgendarConsulta(consultas_repo, relogio=lambda: AGORA)

    resultados = _disparar_em_paralelo(
        [
            lambda: agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, inicio(8))),
            lambda: agendar.executar(AgendarConsultaComando(Usuario(8, Papel.PACIENTE), 10, inicio(9))),
            lambda: agendar.executar(AgendarConsultaComando(Usuario(8, Papel.PACIENTE), 11, inicio(14))),
        ]
    )

    assert all(not isinstance(r, Exception) for r in resultados), resultados
    assert len(consultas_ativas(caminho)) == 3


def test_profissional_recusado_nao_deixa_nada_no_banco(agendar, caminho):
    with pytest.raises(NaoAutorizadoError):
        agendar.executar(AgendarConsultaComando(Usuario(10, Papel.PROFISSIONAL), 10, inicio(10)))

    assert total(caminho, "consulta") == 0
    assert total(caminho, "notificacao_pendente") == 0
