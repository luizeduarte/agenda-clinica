"""Mesma bateria contra os repositórios em memória e contra os SQLite.

Garante que o fake usado nos testes dos casos de uso se comporta como o banco.
"""
from datetime import datetime, time

import pytest

from clinica.compartilhado.erros import ConflitoDePersistenciaError
from clinica.infraestrutura.persistencia import SQLiteUnidadeDeTrabalho, inicializar_banco
from clinica.infraestrutura.persistencia.dados_exemplo import popular_dados_de_exemplo
from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.cadastros.dominio.cadastros import Especialidade, Paciente, Profissional
from clinica.modulos.consultas.dominio.consulta import Consulta, StatusConsulta
from clinica.modulos.notificacoes.dominio.notificacao import (
    EstadoNotificacao,
    Notificacao,
    NotificacaoPendente,
    TipoNotificacao,
)
from tests.aplicacao.fakes import BancoEmMemoria, UnidadeDeTrabalhoEmMemoria


def dt(hora, minuto=0, dia=1):
    return datetime(2026, 12, dia, hora, minuto)


@pytest.fixture(params=["memoria", "sqlite"])
def uow(request, tmp_path):
    """Mesmos cadastros nos dois: pacientes 7 e 8; profissionais 10 (Clínica Geral) e 11 (Odontologia)."""
    if request.param == "sqlite":
        caminho = tmp_path / "contrato.db"
        inicializar_banco(caminho)
        popular_dados_de_exemplo(caminho)
        return SQLiteUnidadeDeTrabalho(caminho)

    banco = BancoEmMemoria()
    clinica, odonto = Especialidade(1, "Clínica Geral"), Especialidade(2, "Odontologia")
    banco.pacientes = {7: Paciente(7, "Ana", "ana@exemplo.com"), 8: Paciente(8, "Bia", "bia@exemplo.com")}
    banco.profissionais = {10: Profissional(10, "Dr. João", clinica), 11: Profissional(11, "Dra. Marta", odonto)}
    return UnidadeDeTrabalhoEmMemoria(banco)


def nova_consulta(paciente=7, profissional=10, hora=10, status=StatusConsulta.AGENDADA):
    return Consulta(paciente, profissional, 1, Slot.a_partir_de(dt(hora)), status)


def gravar(uow, *consultas):
    with uow:
        for c in consultas:
            uow.consultas.adicionar(c)
        uow.commit()


class TestCadastros:
    def test_obtem_paciente(self, uow):
        with uow:
            assert uow.pacientes.obter_por_id(7) == Paciente(7, "Ana", "ana@exemplo.com")

    def test_paciente_inexistente(self, uow):
        with uow:
            assert uow.pacientes.obter_por_id(999) is None

    def test_obtem_profissional_com_especialidade(self, uow):
        with uow:
            profissional = uow.profissionais.obter_por_id(10)
        assert profissional == Profissional(10, "Dr. João", Especialidade(1, "Clínica Geral"))

    def test_profissional_inexistente(self, uow):
        with uow:
            assert uow.profissionais.obter_por_id(999) is None

    def test_lista_profissionais_por_especialidade(self, uow):
        with uow:
            assert [p.id for p in uow.profissionais.listar_por_especialidade("Odontologia")] == [11]
            assert uow.profissionais.listar_por_especialidade("Pediatria") == []


class TestConsultas:
    def test_adicionar_atribui_id_e_permite_obter(self, uow):
        with uow:
            consulta = uow.consultas.adicionar(nova_consulta())
            uow.commit()
        assert consulta.id is not None
        with uow:
            lida = uow.consultas.obter_por_id(consulta.id)
        assert lida == consulta

    def test_obter_inexistente(self, uow):
        with uow:
            assert uow.consultas.obter_por_id(999) is None

    def test_conflito_do_profissional(self, uow):
        gravar(uow, nova_consulta(paciente=7))
        with uow:
            with pytest.raises(ConflitoDePersistenciaError) as erro:
                uow.consultas.adicionar(nova_consulta(paciente=8))
        assert erro.value.participante == "profissional"

    def test_conflito_do_paciente(self, uow):
        gravar(uow, nova_consulta(profissional=10))
        with uow:
            with pytest.raises(ConflitoDePersistenciaError) as erro:
                uow.consultas.adicionar(nova_consulta(profissional=11))
        assert erro.value.participante == "paciente"

    def test_consulta_cancelada_nao_bloqueia_o_horario(self, uow):
        gravar(uow, nova_consulta(status=StatusConsulta.CANCELADA))
        gravar(uow, nova_consulta(paciente=8))  # não levanta

    def test_atualizar_persiste_o_estado(self, uow):
        gravar(uow, nova_consulta())
        with uow:
            (consulta,) = uow.consultas.listar_consultas_paciente(7)
            consulta.cancelar()
            uow.consultas.atualizar(consulta)
            uow.commit()
        with uow:
            assert uow.consultas.obter_por_id(consulta.id).status == StatusConsulta.CANCELADA
            assert uow.consultas.listar_consultas_ativas_paciente(7) == []

    def test_ativas_do_profissional_usa_intervalo_semiaberto(self, uow):
        gravar(uow, nova_consulta(hora=10))  # 10:00–10:30
        with uow:
            dentro = uow.consultas.listar_consultas_ativas_profissional(10, dt(10, 15), dt(11))
            encostado = uow.consultas.listar_consultas_ativas_profissional(10, dt(10, 30), dt(11))
            outro = uow.consultas.listar_consultas_ativas_profissional(11, dt(9), dt(12))
        assert len(dentro) == 1
        assert encostado == []
        assert outro == []

    def test_ativas_do_profissional_ignora_canceladas(self, uow):
        gravar(uow, nova_consulta(status=StatusConsulta.CANCELADA))
        with uow:
            assert uow.consultas.listar_consultas_ativas_profissional(10, dt(0), dt(23)) == []

    def test_listagens_do_paciente(self, uow):
        gravar(
            uow,
            nova_consulta(hora=9),
            nova_consulta(hora=10, status=StatusConsulta.CANCELADA),
        )
        with uow:
            assert len(uow.consultas.listar_consultas_ativas_paciente(7)) == 1
            assert len(uow.consultas.listar_consultas_paciente(7)) == 2

    def test_listar_consultas_profissional_traz_todos_os_estados(self, uow):
        gravar(
            uow,
            nova_consulta(hora=9),
            nova_consulta(paciente=8, hora=10, status=StatusConsulta.CANCELADA),
        )
        with uow:
            assert len(uow.consultas.listar_consultas_profissional(10, dt(0), dt(23))) == 2


class TestAgendas:
    def test_salva_e_le_horarios_substituindo_os_anteriores(self, uow):
        with uow:
            uow.agendas.salvar_horarios_atendimento(
                10, [HorarioAtendimento(1, time(8, 0), time(12, 0))]
            )
            uow.agendas.salvar_horarios_atendimento(
                10, [HorarioAtendimento(2, time(14, 0), time(18, 30))]
            )
            uow.commit()
        with uow:
            assert uow.agendas.obter_horarios_atendimento(10) == [
                HorarioAtendimento(2, time(14, 0), time(18, 30))
            ]

    def test_bloqueios_individual_e_coletivo(self, uow):
        with uow:
            individual = uow.agendas.adicionar_bloqueio(10, Bloqueio(dt(9), dt(10), "reunião"))
            coletivo = uow.agendas.adicionar_bloqueio(None, Bloqueio(dt(9), dt(10), "feriado"))
            uow.agendas.adicionar_bloqueio(11, Bloqueio(dt(9), dt(10), "de outra pessoa"))
            uow.commit()
        assert individual.id is not None and coletivo.id is not None
        with uow:
            motivos = {b.motivo for b in uow.agendas.listar_bloqueios(10, dt(0), dt(23))}
        assert motivos == {"reunião", "feriado"}

    def test_bloqueios_respeitam_o_intervalo(self, uow):
        with uow:
            uow.agendas.adicionar_bloqueio(10, Bloqueio(dt(9), dt(10), "reunião"))
            uow.commit()
        with uow:
            assert uow.agendas.listar_bloqueios(10, dt(10), dt(11)) == []
            assert len(uow.agendas.listar_bloqueios(10, dt(9, 30), dt(11))) == 1


class TestNotificacoesPendentes:
    @staticmethod
    def pendente(texto="oi"):
        return NotificacaoPendente(Notificacao("ana@exemplo.com", TipoNotificacao.AGENDAMENTO, texto))

    def test_adicionar_atribui_id_e_lista_para_envio(self, uow):
        with uow:
            registrada = uow.notificacoes_pendentes.adicionar(self.pendente())
            uow.commit()
        assert registrada.id is not None
        with uow:
            (lida,) = uow.notificacoes_pendentes.listar_para_envio()
        assert lida.notificacao.texto == "oi"
        assert lida.estado == EstadoNotificacao.PENDENTE
        assert lida.tentativas == 0

    def test_enviada_sai_da_lista_e_falha_continua(self, uow):
        with uow:
            a = uow.notificacoes_pendentes.adicionar(self.pendente("a"))
            b = uow.notificacoes_pendentes.adicionar(self.pendente("b"))
            uow.commit()
        with uow:
            a.estado, a.tentativas = EstadoNotificacao.ENVIADA, 1
            b.estado, b.tentativas, b.ultimo_erro = EstadoNotificacao.FALHA, 1, "timeout"
            uow.notificacoes_pendentes.atualizar(a)
            uow.notificacoes_pendentes.atualizar(b)
            uow.commit()
        with uow:
            (restante,) = uow.notificacoes_pendentes.listar_para_envio()
        assert restante.notificacao.texto == "b"
        assert restante.estado == EstadoNotificacao.FALHA
        assert restante.tentativas == 1
        assert restante.ultimo_erro == "timeout"

    def test_respeita_o_limite(self, uow):
        with uow:
            for i in range(3):
                uow.notificacoes_pendentes.adicionar(self.pendente(str(i)))
            uow.commit()
        with uow:
            assert len(uow.notificacoes_pendentes.listar_para_envio(limite=2)) == 2
