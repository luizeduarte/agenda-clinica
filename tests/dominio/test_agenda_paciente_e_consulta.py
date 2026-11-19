from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from clinica.compartilhado.erros import ConflitoDoPacienteError, LimiteDoPacienteExcedidoError
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.dominio.agenda_paciente import AgendaPaciente
from clinica.modulos.consultas.dominio.consulta import Consulta, StatusConsulta

AGORA = datetime(2026, 11, 20, 9, 0)
CLINICA_GERAL, ODONTOLOGIA = 1, 2


def slot(dia, hora, minuto=0):
    return Slot.a_partir_de(datetime(2026, 12, dia, hora, minuto))


def consulta(dia, hora, minuto=0, especialidade=CLINICA_GERAL, status=StatusConsulta.AGENDADA):
    return Consulta(
        paciente_id=7,
        profissional_id=10,
        especialidade_id=especialidade,
        slot=slot(dia, hora, minuto),
        status=status,
    )


class TestConsulta:
    def test_nasce_agendada_e_ativa(self):
        c = consulta(1, 10)
        assert c.status == StatusConsulta.AGENDADA
        assert c.esta_ativa

    def test_estado_nao_pode_ser_alterado_por_fora(self):
        c = consulta(1, 10)
        with pytest.raises(FrozenInstanceError):
            c.status = StatusConsulta.CANCELADA


class TestAgendaPaciente:
    def test_paciente_sem_consultas_pode_agendar(self):
        AgendaPaciente(7, []).verificar_pode_agendar(slot(1, 10), CLINICA_GERAL, AGORA)

    def test_conflito_com_consulta_ativa_no_mesmo_horario(self):
        agenda = AgendaPaciente(7, [consulta(1, 10, especialidade=ODONTOLOGIA)])
        with pytest.raises(ConflitoDoPacienteError):
            agenda.verificar_pode_agendar(slot(1, 10), CLINICA_GERAL, AGORA)

    def test_consulta_cancelada_libera_o_horario(self):
        cancelada = consulta(1, 10, status=StatusConsulta.CANCELADA)
        AgendaPaciente(7, [cancelada]).verificar_pode_agendar(slot(1, 10), CLINICA_GERAL, AGORA)

    def test_limite_de_duas_ativas_no_mesmo_dia(self):
        agenda = AgendaPaciente(
            7,
            [
                consulta(1, 8, especialidade=ODONTOLOGIA),
                consulta(1, 9, especialidade=3),
            ],
        )
        with pytest.raises(LimiteDoPacienteExcedidoError, match="dia"):
            agenda.verificar_pode_agendar(slot(1, 10), CLINICA_GERAL, AGORA)

    def test_duas_ativas_em_dias_diferentes_nao_atingem_o_limite_diario(self):
        agenda = AgendaPaciente(7, [consulta(1, 8, especialidade=ODONTOLOGIA)])
        agenda.verificar_pode_agendar(slot(2, 10), CLINICA_GERAL, AGORA)

    def test_uma_ativa_futura_por_especialidade(self):
        agenda = AgendaPaciente(7, [consulta(1, 10, especialidade=CLINICA_GERAL)])
        with pytest.raises(LimiteDoPacienteExcedidoError, match="especialidade"):
            agenda.verificar_pode_agendar(slot(3, 10), CLINICA_GERAL, AGORA)

    def test_especialidades_diferentes_nao_competem(self):
        agenda = AgendaPaciente(7, [consulta(1, 10, especialidade=CLINICA_GERAL)])
        agenda.verificar_pode_agendar(slot(3, 10), ODONTOLOGIA, AGORA)

    def test_consulta_passada_nao_conta_como_futura(self):
        passada = Consulta(
            paciente_id=7,
            profissional_id=10,
            especialidade_id=CLINICA_GERAL,
            slot=Slot.a_partir_de(datetime(2026, 11, 10, 10, 0)),
            status=StatusConsulta.CONFIRMADA,
        )
        AgendaPaciente(7, [passada]).verificar_pode_agendar(slot(3, 10), CLINICA_GERAL, AGORA)

    def test_cancelada_na_especialidade_nao_conta(self):
        cancelada = consulta(1, 10, status=StatusConsulta.CANCELADA)
        AgendaPaciente(7, [cancelada]).verificar_pode_agendar(slot(3, 10), CLINICA_GERAL, AGORA)

    def test_sobreposicao_entre_profissionais_diferentes_e_conflito(self):
        """O conflito vale em qualquer profissional (RN03)."""
        outra = Consulta(
            paciente_id=7,
            profissional_id=99,
            especialidade_id=ODONTOLOGIA,
            slot=slot(1, 10),
        )
        with pytest.raises(ConflitoDoPacienteError):
            AgendaPaciente(7, [outra]).verificar_pode_agendar(slot(1, 10), CLINICA_GERAL, AGORA)
