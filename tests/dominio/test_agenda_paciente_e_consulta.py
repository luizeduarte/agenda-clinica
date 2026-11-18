from datetime import datetime, timedelta

import pytest

from clinica.compartilhado.erros import (
    CancelamentoForaDoPrazoError,
    ConflitoDoPacienteError,
    LimiteDoPacienteExcedidoError,
    TransicaoInvalidaError,
)
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.autenticacao.portas.servico_autenticacao import Papel
from clinica.modulos.consultas.dominio.agenda_paciente import AgendaPaciente
from clinica.modulos.consultas.dominio.consulta import Consulta, StatusConsulta
from clinica.modulos.consultas.dominio.politica_cancelamento import PoliticaDeCancelamento

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

    def test_confirmar_altera_status_para_confirmada(self):
        c = consulta(1, 10)
        c.confirmar()
        assert c.status == StatusConsulta.CONFIRMADA
        assert c.esta_ativa

    @pytest.mark.parametrize(
        "status",
        [StatusConsulta.CONFIRMADA, StatusConsulta.CANCELADA, StatusConsulta.REALIZADA, StatusConsulta.FALTOU],
    )
    def test_confirmar_fora_de_agendada_levanta_erro(self, status):
        c = consulta(1, 10, status=status)
        with pytest.raises(TransicaoInvalidaError):
            c.confirmar()

    @pytest.mark.parametrize("status", [StatusConsulta.AGENDADA, StatusConsulta.CONFIRMADA])
    def test_cancelar_consulta_ativa_libera_slot(self, status):
        c = consulta(1, 10, status=status)
        c.cancelar()
        assert c.status == StatusConsulta.CANCELADA
        assert not c.esta_ativa

    @pytest.mark.parametrize(
        "status",
        [StatusConsulta.CANCELADA, StatusConsulta.REALIZADA, StatusConsulta.FALTOU],
    )
    def test_cancelar_consulta_inativa_levanta_erro(self, status):
        c = consulta(1, 10, status=status)
        with pytest.raises(TransicaoInvalidaError):
            c.cancelar()


class TestPoliticaDeCancelamento:
    def test_paciente_pode_cancelar_ate_24h_antes_no_padrao(self):
        c = consulta(10, 10)
        politica = PoliticaDeCancelamento()
        no_limite = c.slot.inicio - timedelta(hours=24)
        assert politica.permite_cancelar(c, Papel.PACIENTE, no_limite, "Clínica Geral")
        politica.verificar_pode_cancelar(c, Papel.PACIENTE, no_limite, "Clínica Geral")

    def test_paciente_nao_pode_cancelar_com_menos_de_24h_no_padrao(self):
        c = consulta(10, 10)
        politica = PoliticaDeCancelamento()
        atrasado = c.slot.inicio - timedelta(hours=23, minutes=59)
        assert not politica.permite_cancelar(c, Papel.PACIENTE, atrasado, "Clínica Geral")
        with pytest.raises(CancelamentoForaDoPrazoError, match="24h"):
            politica.verificar_pode_cancelar(c, Papel.PACIENTE, atrasado, "Clínica Geral")

    @pytest.mark.parametrize("especialidade", ["Odontologia", "Dentista", "Odontologia (Dentista)"])
    def test_paciente_exige_72h_para_odontologia(self, especialidade):
        c = consulta(10, 10, especialidade=ODONTOLOGIA)
        politica = PoliticaDeCancelamento()
        com_72h = c.slot.inicio - timedelta(hours=72)
        com_71h = c.slot.inicio - timedelta(hours=71, minutes=59)
        assert politica.permite_cancelar(c, Papel.PACIENTE, com_72h, especialidade)
        assert not politica.permite_cancelar(c, Papel.PACIENTE, com_71h, especialidade)
        with pytest.raises(CancelamentoForaDoPrazoError, match="72h"):
            politica.verificar_pode_cancelar(c, Papel.PACIENTE, com_71h, especialidade)

    def test_profissional_pode_cancelar_sem_antecedencia_minima(self):
        c = consulta(10, 10, especialidade=ODONTOLOGIA)
        politica = PoliticaDeCancelamento()
        em_cima_da_hora = c.slot.inicio - timedelta(minutes=5)
        assert politica.permite_cancelar(c, Papel.PROFISSIONAL, em_cima_da_hora, "Odontologia")
        politica.verificar_pode_cancelar(c, Papel.PROFISSIONAL, em_cima_da_hora, "Odontologia")


class TestAgendaPaciente:
    def test_paciente_sem_consultas_pode_agendar(self):
        agenda = AgendaPaciente(7, [])
        agenda.verificar_pode_agendar(slot(1, 10), CLINICA_GERAL, AGORA)
        assert agenda.pode_agendar(slot(1, 10), CLINICA_GERAL, AGORA)

    def test_conflito_com_consulta_ativa_no_mesmo_horario(self):
        agenda = AgendaPaciente(7, [consulta(1, 10, especialidade=ODONTOLOGIA)])
        assert not agenda.pode_agendar(slot(1, 10), CLINICA_GERAL, AGORA)
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
