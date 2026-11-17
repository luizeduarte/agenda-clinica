import pytest

from clinica.compartilhado.erros import (
    ConflitoDePersistenciaError,
    ConflitoDoPacienteError,
    EntidadeNaoEncontradaError,
    HorarioIndisponivelError,
    LimiteDoPacienteExcedidoError,
    SlotInvalidoError,
)
from clinica.modulos.agenda.dominio.horarios import Bloqueio
from clinica.modulos.cadastros.dominio.cadastros import Especialidade, Profissional
from clinica.modulos.consultas.aplicacao.agendar_consulta import (
    AgendarConsulta,
    AgendarConsultaComando,
)
from clinica.modulos.consultas.dominio.consulta import StatusConsulta
from clinica.modulos.notificacoes.dominio.notificacao import EstadoNotificacao, TipoNotificacao
from tests.aplicacao.conftest import AGORA, dt


@pytest.fixture
def agendar(uow_factory):
    return AgendarConsulta(uow_factory, relogio=lambda: AGORA)


def comando(paciente=7, profissional=10, hora=10, minuto=0):
    return AgendarConsultaComando(paciente, profissional, dt(hora, minuto))


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
        primeira.cancelar()

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

    def test_perda_da_corrida_no_banco_vira_horario_indisponivel(self, uow_factory, banco):
        """Duas requisições passam pela checagem em memória; o índice único barra a segunda."""
        agendar = AgendarConsulta(uow_factory, relogio=lambda: AGORA)
        agendar.executar(comando(paciente=7))

        uow = uow_factory()
        leitura_antiga = uow.consultas.listar_ativas_do_profissional
        uow.consultas.listar_ativas_do_profissional = lambda *a, **k: []  # leitura obsoleta
        concorrente = AgendarConsulta(lambda: uow, relogio=lambda: AGORA)

        with pytest.raises(HorarioIndisponivelError, match="outra reserva"):
            concorrente.executar(comando(paciente=8))
        uow.consultas.listar_ativas_do_profissional = leitura_antiga

        assert len(banco.consultas) == 1

    def test_perda_da_corrida_do_paciente_vira_conflito_do_paciente(self, uow_factory, banco):
        agendar = AgendarConsulta(uow_factory, relogio=lambda: AGORA)
        agendar.executar(comando(profissional=10))

        uow = uow_factory()
        uow.consultas.listar_ativas_do_paciente = lambda *a, **k: []  # leitura obsoleta
        concorrente = AgendarConsulta(lambda: uow, relogio=lambda: AGORA)

        with pytest.raises(ConflitoDoPacienteError):
            concorrente.executar(comando(profissional=11))

    def test_falha_ao_gravar_a_pendencia_desfaz_a_consulta(self, uow_factory, banco):
        uow = uow_factory()

        def falha(_pendente):
            raise RuntimeError("banco indisponível")

        uow.notificacoes_pendentes.adicionar = falha
        agendar = AgendarConsulta(lambda: uow, relogio=lambda: AGORA)

        with pytest.raises(RuntimeError):
            agendar.executar(comando())

        assert banco.consultas == []
        assert banco.pendentes == []
