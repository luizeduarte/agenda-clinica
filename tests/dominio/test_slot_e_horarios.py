from datetime import date, datetime, time

import pytest

from clinica.compartilhado.erros import HorarioDeAtendimentoInvalidoError, SlotInvalidoError
from clinica.modulos.agenda.dominio.agenda_profissional import AgendaProfissional
from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento
from clinica.modulos.agenda.dominio.slot import Slot

TERCA = date(2026, 12, 1)  # weekday() == 1


def dt(hora, minuto=0, dia=TERCA):
    return datetime(dia.year, dia.month, dia.day, hora, minuto)


class TestSlot:
    def test_a_partir_de_cria_slot_de_30_minutos(self):
        slot = Slot.a_partir_de(dt(10, 0))
        assert slot.fim == dt(10, 30)

    @pytest.mark.parametrize("minuto", [0, 30])
    def test_aceita_inicio_na_grade(self, minuto):
        Slot.a_partir_de(dt(9, minuto))

    @pytest.mark.parametrize("minuto", [15, 45, 1])
    def test_rejeita_inicio_fora_da_grade(self, minuto):
        with pytest.raises(SlotInvalidoError):
            Slot.a_partir_de(dt(10, minuto))

    def test_rejeita_duracao_diferente_de_30_minutos(self):
        with pytest.raises(SlotInvalidoError):
            Slot(dt(10, 0), dt(11, 0))

    def test_rejeita_segundos_no_inicio(self):
        with pytest.raises(SlotInvalidoError):
            Slot.a_partir_de(datetime(2026, 12, 1, 10, 0, 5))

    def test_slots_iguais_se_sobrepoem(self):
        assert Slot.a_partir_de(dt(10, 0)).sobrepoe(Slot.a_partir_de(dt(10, 0)))

    def test_slots_vizinhos_nao_se_sobrepoem(self):
        assert not Slot.a_partir_de(dt(10, 0)).sobrepoe(Slot.a_partir_de(dt(10, 30)))

    def test_slots_na_grade_nunca_se_sobrepoem_em_parte(self):
        a, b = Slot.a_partir_de(dt(10, 0)), Slot.a_partir_de(dt(10, 30))
        assert a.sobrepoe(b) == (a == b)


class TestHorarioAtendimento:
    def test_gera_slots_do_dia_na_grade(self):
        horario = HorarioAtendimento(1, time(8, 0), time(10, 0))
        inicios = [s.inicio for s in horario.slots_do_dia(TERCA)]
        assert inicios == [dt(8, 0), dt(8, 30), dt(9, 0), dt(9, 30)]

    def test_nao_gera_slots_em_outro_dia_da_semana(self):
        horario = HorarioAtendimento(1, time(8, 0), time(10, 0))
        assert horario.slots_do_dia(date(2026, 12, 2)) == []

    def test_rejeita_periodo_fora_da_grade(self):
        with pytest.raises(HorarioDeAtendimentoInvalidoError):
            HorarioAtendimento(1, time(10, 15), time(12, 0))

    def test_rejeita_periodo_invertido(self):
        with pytest.raises(HorarioDeAtendimentoInvalidoError):
            HorarioAtendimento(1, time(12, 0), time(8, 0))

    def test_rejeita_dia_da_semana_invalido(self):
        with pytest.raises(HorarioDeAtendimentoInvalidoError):
            HorarioAtendimento(7, time(8, 0), time(12, 0))

    def test_rejeita_periodos_sobrepostos_no_mesmo_dia(self):
        with pytest.raises(HorarioDeAtendimentoInvalidoError):
            AgendaProfissional.validar_grade_semanal(
                [
                    HorarioAtendimento(1, time(8, 0), time(12, 0)),
                    HorarioAtendimento(1, time(11, 30), time(14, 0)),
                ]
            )

    def test_aceita_periodos_encostados_e_em_dias_diferentes(self):
        AgendaProfissional.validar_grade_semanal(
            [
                HorarioAtendimento(1, time(8, 0), time(12, 0)),
                HorarioAtendimento(1, time(12, 0), time(14, 0)),
                HorarioAtendimento(2, time(8, 0), time(12, 0)),
            ]
        )


class TestBloqueio:
    def test_intersecta_slot_dentro_do_periodo(self):
        bloqueio = Bloqueio(dt(9, 0), dt(10, 0), "reunião")
        assert bloqueio.intersecta(Slot.a_partir_de(dt(9, 30)))

    def test_nao_intersecta_slot_que_comeca_quando_termina(self):
        bloqueio = Bloqueio(dt(9, 0), dt(10, 0), "reunião")
        assert not bloqueio.intersecta(Slot.a_partir_de(dt(10, 0)))

    def test_rejeita_bloqueio_invertido(self):
        with pytest.raises(HorarioDeAtendimentoInvalidoError):
            Bloqueio(dt(10, 0), dt(9, 0), "erro")
