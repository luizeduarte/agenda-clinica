from datetime import timedelta

import pytest

from clinica.compartilhado.erros import (
    ConflitoDoPacienteError,
    EntidadeNaoEncontradaError,
    HorarioIndisponivelError,
    LimiteDoPacienteExcedidoError,
    NaoAutorizadoError,
    SlotInvalidoError,
)
from clinica.modulos.autenticacao.portas.servico_autenticacao import Papel, Usuario
from clinica.modulos.agenda.dominio.horarios import Bloqueio
from clinica.modulos.cadastros.dominio.cadastros import Especialidade, Profissional
from clinica.modulos.consultas.aplicacao.agendar_consulta import (
    AgendarConsulta,
    AgendarConsultaComando,
)
from clinica.modulos.consultas.dominio.consulta import StatusConsulta
from clinica.modulos.notificacoes.dominio.notificacao import EstadoNotificacao, TipoNotificacao
from tests.aplicacao.conftest import AGORA, dt
from tests.aplicacao.fakes import UnidadeDeTrabalhoEmMemoria


@pytest.fixture
def agendar(uow):
    return AgendarConsulta(uow, relogio=lambda: AGORA)


def comando(paciente=7, profissional=10, hora=10, minuto=0):
    return AgendarConsultaComando(Usuario(paciente, Papel.PACIENTE), profissional, dt(hora, minuto))


class TestFluxoPrincipal:
    def test_agenda_a_consulta_como_agendada(self, agendar, banco):
        consulta = agendar.executar(comando())

        assert consulta.id is not None
        assert consulta.status == StatusConsulta.AGENDADA
        assert consulta.especialidade_id == 1  # copiada do profissional
        assert banco.consultas == [consulta]

    def test_registra_a_notificacao_pendente_junto_da_consulta(self, agendar, banco):
        agendar.executar(comando())

        (pendente,) = banco.pendentes
        assert pendente.estado == EstadoNotificacao.PENDENTE
        assert pendente.notificacao.tipo == TipoNotificacao.AGENDAMENTO
        assert pendente.notificacao.destinatario == "ana@exemplo.com"
        assert "10:00" in pendente.notificacao.texto

    def test_horario_cancelado_pode_ser_reagendado_por_outro_paciente(self, agendar, banco):
        primeira = agendar.executar(comando(paciente=7))
        primeira.status = StatusConsulta.CANCELADA  # o cancelamento em si está fora do recorte

        segunda = agendar.executar(comando(paciente=8))

        assert segunda.status == StatusConsulta.AGENDADA


class TestFluxosAlternativos:
    def test_horario_ja_ocupado_pelo_profissional(self, agendar, banco):
        agendar.executar(comando(paciente=7))

        with pytest.raises(HorarioIndisponivelError, match="ocupado"):
            agendar.executar(comando(paciente=8))

        assert len(banco.consultas) == 1
        assert len(banco.pendentes) == 1

    def test_horario_bloqueado(self, agendar, banco):
        banco.bloqueios.append((10, Bloqueio(dt(9, 0), dt(11, 0), "reunião")))

        with pytest.raises(HorarioIndisponivelError, match="bloqueado"):
            agendar.executar(comando(hora=10))

        assert banco.consultas == []

    def test_bloqueio_coletivo_vale_para_todos(self, agendar, banco):
        banco.bloqueios.append((None, Bloqueio(dt(0, 0), dt(23, 30), "feriado")))

        with pytest.raises(HorarioIndisponivelError):
            agendar.executar(comando(profissional=11))

    def test_fora_do_periodo_de_atendimento(self, agendar):
        with pytest.raises(HorarioIndisponivelError, match="fora"):
            agendar.executar(comando(hora=15))

    def test_horario_fora_da_grade(self, agendar, banco):
        with pytest.raises(SlotInvalidoError):
            agendar.executar(comando(minuto=15))

        assert banco.consultas == []

    @pytest.mark.parametrize("agora", [dt(10), dt(10, 1), dt(10) + timedelta(days=1)])
    def test_horario_ja_iniciado_nao_pode_ser_agendado(self, uow, banco, agora):
        agendar = AgendarConsulta(uow, relogio=lambda: agora)

        with pytest.raises(SlotInvalidoError, match="futuro"):
            agendar.executar(comando())

        assert banco.consultas == banco.pendentes == []

    def test_paciente_ja_tem_consulta_no_mesmo_horario_com_outro_profissional(self, agendar):
        agendar.executar(comando(profissional=10))

        with pytest.raises(ConflitoDoPacienteError):
            agendar.executar(comando(profissional=11))

    def test_limite_de_uma_consulta_futura_por_especialidade(self, agendar):
        agendar.executar(comando(hora=10))

        with pytest.raises(LimiteDoPacienteExcedidoError, match="especialidade"):
            agendar.executar(comando(hora=11))

    def test_limite_de_duas_consultas_no_dia(self, agendar, banco):
        agendar.executar(comando(profissional=10, hora=8))
        agendar.executar(comando(profissional=11, hora=9))
        banco.profissionais[12] = Profissional(12, "Dra. Lia", Especialidade(3, "Pediatria"))
        banco.horarios[12] = banco.horarios[10]

        with pytest.raises(LimiteDoPacienteExcedidoError, match="dia"):
            agendar.executar(comando(profissional=12, hora=10))

    def test_paciente_inexistente(self, agendar):
        with pytest.raises(EntidadeNaoEncontradaError, match="Paciente"):
            agendar.executar(comando(paciente=999))

    def test_profissional_inexistente(self, agendar):
        with pytest.raises(EntidadeNaoEncontradaError, match="Profissional"):
            agendar.executar(comando(profissional=999))


class TestConsistencia:
    """ASR-01 e atomicidade (ASR-03) vistos pelo caso de uso."""

    def test_perda_da_corrida_no_banco_vira_horario_indisponivel(self, banco):
        """Duas requisições passam pela checagem em memória; o índice único barra a segunda."""
        agendar = AgendarConsulta(UnidadeDeTrabalhoEmMemoria(banco), relogio=lambda: AGORA)
        agendar.executar(comando(paciente=7))

        uow = UnidadeDeTrabalhoEmMemoria(banco)
        leitura_antiga = uow.consultas.listar_consultas_ativas_profissional
        uow.consultas.listar_consultas_ativas_profissional = lambda *a, **k: []  # leitura obsoleta
        concorrente = AgendarConsulta(uow, relogio=lambda: AGORA)

        with pytest.raises(HorarioIndisponivelError, match="outra reserva"):
            concorrente.executar(comando(paciente=8))
        uow.consultas.listar_consultas_ativas_profissional = leitura_antiga

        assert len(banco.consultas) == 1

    def test_perda_da_corrida_do_paciente_vira_conflito_do_paciente(self, banco):
        agendar = AgendarConsulta(UnidadeDeTrabalhoEmMemoria(banco), relogio=lambda: AGORA)
        agendar.executar(comando(profissional=10))

        uow = UnidadeDeTrabalhoEmMemoria(banco)
        uow.consultas.listar_consultas_ativas_paciente = lambda *a, **k: []  # leitura obsoleta
        concorrente = AgendarConsulta(uow, relogio=lambda: AGORA)

        with pytest.raises(ConflitoDoPacienteError):
            concorrente.executar(comando(profissional=11))

    def test_falha_ao_gravar_a_pendencia_desfaz_a_consulta(self, banco):
        uow = UnidadeDeTrabalhoEmMemoria(banco)

        def falha(_pendente):
            raise RuntimeError("banco indisponível")

        uow.notificacoes_pendentes.adicionar = falha
        agendar = AgendarConsulta(uow, relogio=lambda: AGORA)

        with pytest.raises(RuntimeError):
            agendar.executar(comando())

        assert banco.consultas == []
        assert banco.pendentes == []


class TestAutorizacao:
    """RNF03: só o paciente agenda; a recusa não altera nenhum dado."""

    PROFISSIONAL = Usuario(10, Papel.PROFISSIONAL)

    def test_profissional_nao_agenda(self, agendar, banco):
        with pytest.raises(NaoAutorizadoError, match="pacientes"):
            agendar.executar(AgendarConsultaComando(self.PROFISSIONAL, 10, dt(10)))

        assert banco.consultas == []
        assert banco.pendentes == []

    def test_o_mesmo_pedido_feito_por_um_paciente_e_aceito(self, agendar, banco):
        agendar.executar(comando(paciente=7))

        assert len(banco.consultas) == 1

    def test_a_recusa_vem_antes_das_outras_validacoes(self, agendar):
        # horário fora da grade e profissional inexistente: o usuário já é recusado antes
        with pytest.raises(NaoAutorizadoError):
            agendar.executar(AgendarConsultaComando(self.PROFISSIONAL, 999, dt(10, 15)))

    def test_o_paciente_da_consulta_e_o_proprio_usuario(self, agendar):
        consulta = agendar.executar(comando(paciente=8))

        assert consulta.paciente_id == 8
