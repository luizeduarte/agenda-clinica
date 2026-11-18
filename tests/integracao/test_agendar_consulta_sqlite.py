"""`AgendarConsulta` ponta a ponta sobre o SQLite, incluindo concorrência (ASR-01)."""
import threading
from collections import Counter
from datetime import datetime

import pytest

from clinica.compartilhado.erros import HorarioIndisponivelError, NaoAutorizadoError
from clinica.infraestrutura.persistencia import SQLiteUnidadeDeTrabalho, inicializar_banco
from clinica.infraestrutura.persistencia.conexao import abrir_conexao
from clinica.infraestrutura.persistencia.dados_exemplo import popular_dados_de_exemplo
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.autenticacao.portas.servico_autenticacao import Papel, Usuario
from clinica.modulos.consultas.aplicacao.agendar_consulta import (
    AgendarConsulta,
    AgendarConsultaComando,
)
from clinica.modulos.consultas.aplicacao.consultar_disponibilidade import ConsultarDisponibilidade
from clinica.modulos.consultas.dominio.consulta import Consulta

AGORA = datetime(2026, 11, 20, 9, 0)
TERCA = datetime(2026, 12, 1)


def inicio(hora, minuto=0):
    return datetime(2026, 12, 1, hora, minuto)


@pytest.fixture
def caminho(tmp_path):
    caminho = tmp_path / "agendar.db"
    inicializar_banco(caminho)
    popular_dados_de_exemplo(caminho)
    return caminho


@pytest.fixture
def agendar(caminho):
    return AgendarConsulta(SQLiteUnidadeDeTrabalho(caminho), relogio=lambda: AGORA)


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


def test_horario_ocupado_nao_grava_nada_alem_da_primeira(agendar, caminho):
    agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, inicio(10)))

    with pytest.raises(HorarioIndisponivelError):
        agendar.executar(AgendarConsultaComando(Usuario(8, Papel.PACIENTE), 10, inicio(10)))

    assert len(consultas_ativas(caminho)) == 1
    assert total(caminho, "notificacao_pendente") == 1


def test_falha_ao_gravar_a_pendencia_desfaz_a_consulta(caminho):
    class UnidadeComDefeito:
        """Delega à unidade real, mas a gravação da pendência falha."""

        def __init__(self):
            self._uow = SQLiteUnidadeDeTrabalho(caminho)

        def __enter__(self):
            self._uow.__enter__()
            return self

        def __exit__(self, *args):
            return self._uow.__exit__(*args)

        def __getattr__(self, nome):
            return getattr(self._uow, nome)

        @property
        def notificacoes_pendentes(self):
            class Falha:
                @staticmethod
                def adicionar(_pendente):
                    raise RuntimeError("banco indisponível")

            return Falha()

    agendar = AgendarConsulta(UnidadeComDefeito(), relogio=lambda: AGORA)

    with pytest.raises(RuntimeError):
        agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, inicio(10)))

    assert total(caminho, "consulta") == 0


def test_disponibilidade_reflete_o_que_foi_agendado(agendar, caminho):
    agendar.executar(AgendarConsultaComando(Usuario(7, Papel.PACIENTE), 10, inicio(8, 30)))

    (resultado,) = ConsultarDisponibilidade(SQLiteUnidadeDeTrabalho(caminho), lambda: AGORA).executar(
        TERCA.date(), profissional_id=10
    )

    inicios = [s.inicio for s in resultado.slots]
    assert inicio(8, 30) not in inicios
    assert inicio(8, 0) in inicios
    assert len(inicios) == 15  # 8 slots de manhã + 8 de tarde, menos o ocupado


def test_consultar_disponibilidade_durante_uma_escrita(caminho):
    consultar = ConsultarDisponibilidade(SQLiteUnidadeDeTrabalho(caminho), lambda: AGORA)
    with SQLiteUnidadeDeTrabalho(caminho) as escrita:
        escrita.consultas.adicionar(Consulta(7, 10, 1, Slot.a_partir_de(inicio(10))))
        (resultado,) = consultar.executar(TERCA.date(), profissional_id=10)
        assert inicio(10) in [slot.inicio for slot in resultado.slots]
        escrita.commit()

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
    agendar = AgendarConsulta(SQLiteUnidadeDeTrabalho(caminho), relogio=lambda: AGORA)

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
    agendar = AgendarConsulta(SQLiteUnidadeDeTrabalho(caminho), relogio=lambda: AGORA)

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
    agendar = AgendarConsulta(SQLiteUnidadeDeTrabalho(caminho), relogio=lambda: AGORA)

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
