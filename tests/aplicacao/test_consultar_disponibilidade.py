import pytest

from clinica.compartilhado.erros import EntidadeNaoEncontradaError
from clinica.modulos.agenda.dominio.horarios import Bloqueio
from clinica.modulos.consultas.aplicacao.agendar_consulta import (
    AgendarConsulta,
    AgendarConsultaComando,
)
from clinica.modulos.consultas.aplicacao.consultar_disponibilidade import ConsultarDisponibilidade
from tests.aplicacao.conftest import AGORA, TERCA, dt


@pytest.fixture
def consultar(uow_factory):
    return ConsultarDisponibilidade(uow_factory)


def inicios(disponibilidade):
    return [s.inicio for s in disponibilidade.slots]


def test_por_profissional_lista_todos_os_slots_do_dia(consultar):
    (resultado,) = consultar.executar(TERCA, profissional_id=10)

    assert resultado.profissional.id == 10
    assert len(resultado.slots) == 8  # 08:00–12:00 em slots de 30 min
    assert inicios(resultado)[0] == dt(8, 0)
    assert inicios(resultado)[-1] == dt(11, 30)


def test_desconta_consultas_ativas_e_bloqueios(consultar, uow_factory, banco):
    AgendarConsulta(uow_factory, relogio=lambda: AGORA).executar(
        AgendarConsultaComando(7, 10, dt(8, 30))
    )
    banco.bloqueios.append((10, Bloqueio(dt(9, 0), dt(10, 0), "reunião")))

    (resultado,) = consultar.executar(TERCA, profissional_id=10)

    assert inicios(resultado) == [dt(8, 0), dt(10, 0), dt(10, 30), dt(11, 0), dt(11, 30)]


def test_consulta_cancelada_libera_o_slot(consultar, uow_factory):
    consulta = AgendarConsulta(uow_factory, relogio=lambda: AGORA).executar(
        AgendarConsultaComando(7, 10, dt(8, 30))
    )
    consulta.cancelar()

    (resultado,) = consultar.executar(TERCA, profissional_id=10)

    assert dt(8, 30) in inicios(resultado)


def test_por_especialidade_traz_so_os_profissionais_dela(consultar):
    resultado = consultar.executar(TERCA, especialidade="Odontologia")

    assert [r.profissional.id for r in resultado] == [11]
    assert len(resultado[0].slots) == 8


def test_ocupacao_de_um_profissional_nao_afeta_o_outro(consultar, uow_factory):
    AgendarConsulta(uow_factory, relogio=lambda: AGORA).executar(
        AgendarConsultaComando(7, 10, dt(8, 0))
    )

    (outro,) = consultar.executar(TERCA, profissional_id=11)

    assert dt(8, 0) in inicios(outro)


def test_dia_sem_atendimento_nao_tem_slots(consultar):
    from datetime import date

    (resultado,) = consultar.executar(date(2026, 12, 2), profissional_id=10)  # quarta

    assert resultado.slots == []


def test_profissional_inexistente(consultar):
    with pytest.raises(EntidadeNaoEncontradaError):
        consultar.executar(TERCA, profissional_id=999)


@pytest.mark.parametrize("filtros", [{}, {"profissional_id": 10, "especialidade": "Odontologia"}])
def test_exige_exatamente_um_filtro(consultar, filtros):
    with pytest.raises(ValueError):
        consultar.executar(TERCA, **filtros)
