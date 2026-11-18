from datetime import date, datetime, time

import pytest

from clinica.compartilhado.erros import HorarioDeAtendimentoInvalidoError, HorarioIndisponivelError
from clinica.modulos.agenda.dominio.agenda_profissional import AgendaProfissional
from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento
from clinica.modulos.agenda.dominio.slot import Slot

TERCA = date(2026, 12, 1)


def dt(hora, minuto=0, dia=TERCA):
    return datetime(dia.year, dia.month, dia.day, hora, minuto)


def slot(hora, minuto=0):
    return Slot.a_partir_de(dt(hora, minuto))


@pytest.fixture
def agenda():
    """Atende terças 08:00–12:00, com consulta às 08:30 e reunião 09:00–09:30."""
    return AgendaProfissional(
        profissional_id=1,
        horarios_atendimento=[HorarioAtendimento(1, time(8, 0), time(12, 0))],
        bloqueios=[Bloqueio(dt(9, 0), dt(9, 30), "reunião")],
        slots_ocupados=[slot(8, 30)],
    )


def test_slots_disponiveis_descontam_ocupados_e_bloqueios(agenda):
    inicios = [s.inicio for s in agenda.slots_disponiveis(TERCA)]
    assert inicios == [
        dt(8, 0), dt(9, 30), dt(10, 0), dt(10, 30), dt(11, 0), dt(11, 30),
    ]


def test_dia_sem_atendimento_nao_tem_slots(agenda):
    assert agenda.slots_disponiveis(date(2026, 12, 2)) == []


def test_slot_livre_passa_na_verificacao(agenda):
    agenda.verificar_disponivel(slot(10, 0))
    assert agenda.esta_disponivel(slot(10, 0))
    assert not agenda.esta_disponivel(slot(8, 30))
    assert not agenda.esta_disponivel(slot(9, 0))


def test_slot_ocupado_e_indisponivel(agenda):
    with pytest.raises(HorarioIndisponivelError, match="ocupado"):
        agenda.verificar_disponivel(slot(8, 30))


def test_slot_bloqueado_e_indisponivel(agenda):
    with pytest.raises(HorarioIndisponivelError, match="bloqueado"):
        agenda.verificar_disponivel(slot(9, 0))


def test_slot_fora_do_atendimento_e_indisponivel(agenda):
    with pytest.raises(HorarioIndisponivelError, match="fora"):
        agenda.verificar_disponivel(slot(14, 0))


def test_slot_em_dia_sem_atendimento_e_indisponivel(agenda):
    quarta = Slot.a_partir_de(datetime(2026, 12, 2, 10, 0))
    with pytest.raises(HorarioIndisponivelError):
        agenda.verificar_disponivel(quarta)


def test_rejeita_agenda_com_periodos_sobrepostos():
    with pytest.raises(HorarioDeAtendimentoInvalidoError):
        AgendaProfissional(
            1,
            [
                HorarioAtendimento(1, time(8, 0), time(12, 0)),
                HorarioAtendimento(1, time(10, 0), time(14, 0)),
            ],
            [],
            [],
        )
