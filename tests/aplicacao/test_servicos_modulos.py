import pytest

from clinica.compartilhado.erros import (
    EntidadeNaoEncontradaError,
    HorarioIndisponivelError,
    NaoAutenticadoError,
)
from clinica.infraestrutura.autenticacao.servico_autenticacao_fake import ServicoAutenticacaoFake
from clinica.modulos.agenda.contratos import Agenda, Slot
from clinica.modulos.agenda.dominio.horarios import Bloqueio
from clinica.modulos.autenticacao.contratos import Autenticacao, Papel, Usuario
from clinica.modulos.cadastros.contratos import Cadastros
from clinica.modulos.consultas.contratos import Consultas
from clinica.modulos.consultas.dominio.consulta import Consulta, StatusConsulta
from clinica.modulos.notificacoes.contratos import Notificacoes
from clinica.modulos.notificacoes.dominio.notificacao import EstadoNotificacao, TipoNotificacao
from tests.aplicacao.conftest import TERCA, dt


class TestAgendaContrato:
    def test_verificar_disponibilidade_aceita_slot_livre(self, banco):
        Agenda.verificar_disponibilidade(10, Slot.a_partir_de(dt(10, 0)), slots_ocupados=[])

    def test_verificar_disponibilidade_rejeita_slot_ocupado(self, banco):
        slot = Slot.a_partir_de(dt(10, 0))
        with pytest.raises(HorarioIndisponivelError, match="ocupado"):
            Agenda.verificar_disponibilidade(10, slot, slots_ocupados=[slot])

    def test_verificar_disponibilidade_rejeita_bloqueio_e_fora_do_expediente(self, banco):
        banco.bloqueios.append((10, Bloqueio(dt(9, 0), dt(10, 0), "reunião")))

        with pytest.raises(HorarioIndisponivelError, match="bloqueado"):
            Agenda.verificar_disponibilidade(10, Slot.a_partir_de(dt(9, 0)), slots_ocupados=[])

        with pytest.raises(HorarioIndisponivelError, match="fora"):
            Agenda.verificar_disponibilidade(10, Slot.a_partir_de(dt(15, 0)), slots_ocupados=[])

    def test_listar_slots_disponiveis_desconta_ocupados_bloqueios_e_passado(self, banco):
        banco.bloqueios.append((10, Bloqueio(dt(9, 0), dt(10, 0), "reunião")))

        slots = Agenda.listar_slots_disponiveis(
            10,
            TERCA,
            slots_ocupados=[Slot.a_partir_de(dt(10, 30))],
            agora=dt(8, 30),
        )

        assert [s.inicio for s in slots] == [dt(10, 0), dt(11, 0), dt(11, 30)]

    def test_consulta_slots_ocupados_pelo_contrato_de_consultas(self, banco):
        ocupado = Slot.a_partir_de(dt(10, 0))
        banco.consultas.append(Consulta(7, 10, 1, ocupado))
        banco.consultas.append(
            Consulta(8, 10, 1, Slot.a_partir_de(dt(10, 30)), status=StatusConsulta.CANCELADA)
        )

        with pytest.raises(HorarioIndisponivelError, match="ocupado"):
            Agenda.verificar_disponibilidade(10, ocupado)

        disponiveis = Agenda.listar_slots_disponiveis(10, TERCA, agora=dt(9, 30))
        assert [s.inicio for s in disponiveis] == [dt(10, 30), dt(11, 0), dt(11, 30)]


class TestCadastrosContrato:
    def test_obter_paciente_e_profissional_existentes(self, banco):
        assert Cadastros.obter_paciente(7).nome == "Ana"
        assert Cadastros.obter_profissional(10).nome == "Dr. João"

    def test_entidade_inexistente_levanta_erro(self, banco):
        with pytest.raises(EntidadeNaoEncontradaError, match="Paciente"):
            Cadastros.obter_paciente(999)
        with pytest.raises(EntidadeNaoEncontradaError, match="Profissional"):
            Cadastros.obter_profissional(999)

    def test_listar_profissionais_por_especialidade(self, banco):
        profissionais = Cadastros.listar_profissionais_por_especialidade("Odontologia")
        assert [p.id for p in profissionais] == [11]


class TestConsultasContrato:
    def test_lista_apenas_slots_de_consultas_ativas_do_profissional(self, banco):
        slot_ativo = Slot.a_partir_de(dt(10, 0))
        banco.consultas.append(Consulta(7, 10, 1, slot_ativo))
        banco.consultas.append(
            Consulta(8, 10, 1, Slot.a_partir_de(dt(10, 30)), status=StatusConsulta.CANCELADA)
        )
        banco.consultas.append(Consulta(8, 11, 2, Slot.a_partir_de(dt(11, 0))))

        slots = Consultas.listar_slots_ocupados_profissional(10, dt(8, 0), dt(12, 0))
        assert slots == [slot_ativo]


class TestNotificacoesContrato:
    def test_registrar_agendamento_grava_pendencia(self, banco):
        Notificacoes.registrar_agendamento(
            destinatario="ana@exemplo.com",
            nome_paciente="Ana",
            nome_profissional="Dr. João",
            nome_especialidade="Clínica Geral",
            inicio=dt(10, 0),
        )

        (pendente,) = banco.pendentes
        assert pendente.id is not None
        assert pendente.estado == EstadoNotificacao.PENDENTE
        assert pendente.notificacao.tipo == TipoNotificacao.AGENDAMENTO
        assert pendente.notificacao.destinatario == "ana@exemplo.com"
        assert "10:00" in pendente.notificacao.texto


class TestAutenticacaoContrato:
    @pytest.fixture(autouse=True)
    def configurar_autenticacao(self):
        Autenticacao.configurar(ServicoAutenticacaoFake())

    def test_identificar_token_valido(self):
        assert Autenticacao.identificar("token-ana") == Usuario(7, Papel.PACIENTE)

    def test_identificar_por_cabecalho_valido(self):
        assert Autenticacao.identificar_por_cabecalho("Bearer token-dr-joao") == Usuario(
            10, Papel.PROFISSIONAL
        )
        assert Autenticacao.identificar_por_cabecalho("bearer token-ana") == Usuario(
            7, Papel.PACIENTE
        )

    @pytest.mark.parametrize("cabecalho", [None, "", "token-ana", "Bearer ", "Basic abc"])
    def test_cabecalho_invalido_levanta_nao_autenticado(self, cabecalho):
        with pytest.raises(NaoAutenticadoError):
            Autenticacao.identificar_por_cabecalho(cabecalho)

    def test_token_desconhecido_ou_vazio_levanta_nao_autenticado(self):
        with pytest.raises(NaoAutenticadoError):
            Autenticacao.identificar("")
        with pytest.raises(NaoAutenticadoError):
            Autenticacao.identificar("desconhecido")
