"""Mesma bateria contra os repositórios em memória e contra os SQLite.

Garante que o fake usado nos testes dos casos de uso se comporta como o banco.
"""
from datetime import datetime, time

import pytest

from clinica.compartilhado.erros import ConflitoDePersistenciaError
from clinica.infraestrutura.persistencia import ConexaoSQLite, inicializar_banco
from clinica.infraestrutura.persistencia.agenda_repositorio import SQLiteAgendaRepositorio
from clinica.infraestrutura.persistencia.cadastros_repositorios import (
    SQLitePacienteRepositorio,
    SQLiteProfissionalRepositorio,
)
from clinica.infraestrutura.persistencia.conexao import abrir_conexao
from clinica.infraestrutura.persistencia.consulta_repositorio import SQLiteConsultaRepositorio
from clinica.infraestrutura.persistencia.conversao import para_texto
from clinica.infraestrutura.persistencia.dados_exemplo import popular_dados_de_exemplo
from clinica.infraestrutura.persistencia.notificacao_pendente_repositorio import (
    SQLiteNotificacaoPendenteRepositorio,
)
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
from tests.aplicacao.fakes import (
    AgendaRepositorioEmMemoria,
    BancoEmMemoria,
    ConsultaRepositorioEmMemoria,
    NotificacaoPendenteRepositorioEmMemoria,
    PacienteRepositorioEmMemoria,
    ProfissionalRepositorioEmMemoria,
)


def dt(hora, minuto=0, dia=1):
    return datetime(2026, 12, dia, hora, minuto)


class Ambiente:
    """Repositórios de um dos bancos, mais a preparação de dados para a leitura."""

    def __init__(
        self,
        consultas,
        agendas,
        pacientes,
        profissionais,
        notificacoes_pendentes,
        semear_horarios,
        semear_bloqueio,
    ):
        self.consultas = consultas
        self.agendas = agendas
        self.pacientes = pacientes
        self.profissionais = profissionais
        self.notificacoes_pendentes = notificacoes_pendentes
        self.semear_horarios = semear_horarios
        self.semear_bloqueio = semear_bloqueio


@pytest.fixture(params=["memoria", "sqlite"])
def ambiente(request, tmp_path):
    """Mesmos cadastros nos dois: pacientes 7 e 8; profissionais 10 (Clínica Geral) e 11 (Odontologia)."""
    if request.param == "sqlite":
        caminho = tmp_path / "contrato.db"
        inicializar_banco(caminho)
        popular_dados_de_exemplo(caminho)

        def semear_horarios(profissional_id, horarios):
            con = abrir_conexao(caminho)
            con.execute("DELETE FROM horario_atendimento WHERE profissional_id = ?", (profissional_id,))
            con.executemany(
                "INSERT INTO horario_atendimento (profissional_id, dia_semana, hora_inicio, hora_fim)"
                " VALUES (?, ?, ?, ?)",
                [
                    (profissional_id, h.dia_semana, h.hora_inicio.strftime("%H:%M"), h.hora_fim.strftime("%H:%M"))
                    for h in horarios
                ],
            )
            con.close()

        def semear_bloqueio(profissional_id, bloqueio):
            con = abrir_conexao(caminho)
            con.execute(
                "INSERT INTO bloqueio (profissional_id, inicio, fim, motivo) VALUES (?, ?, ?, ?)",
                (profissional_id, para_texto(bloqueio.inicio), para_texto(bloqueio.fim), bloqueio.motivo),
            )
            con.close()

        banco = ConexaoSQLite(caminho)
        return Ambiente(
            SQLiteConsultaRepositorio(banco),
            SQLiteAgendaRepositorio(banco),
            SQLitePacienteRepositorio(banco),
            SQLiteProfissionalRepositorio(banco),
            SQLiteNotificacaoPendenteRepositorio(banco),
            semear_horarios,
            semear_bloqueio,
        )

    banco = BancoEmMemoria()
    clinica, odonto = Especialidade(1, "Clínica Geral"), Especialidade(2, "Odontologia")
    banco.pacientes = {7: Paciente(7, "Ana", "ana@exemplo.com"), 8: Paciente(8, "Bia", "bia@exemplo.com")}
    banco.profissionais = {10: Profissional(10, "Dr. João", clinica), 11: Profissional(11, "Dra. Marta", odonto)}

    def semear_horarios(profissional_id, horarios):
        banco.horarios[profissional_id] = list(horarios)

    def semear_bloqueio(profissional_id, bloqueio):
        banco.bloqueios.append((profissional_id, bloqueio))

    return Ambiente(
        ConsultaRepositorioEmMemoria(banco),
        AgendaRepositorioEmMemoria(banco),
        PacienteRepositorioEmMemoria(banco),
        ProfissionalRepositorioEmMemoria(banco),
        NotificacaoPendenteRepositorioEmMemoria(banco),
        semear_horarios,
        semear_bloqueio,
    )


def nova_consulta(paciente=7, profissional=10, hora=10, status=StatusConsulta.AGENDADA):
    return Consulta(paciente, profissional, 1, Slot.a_partir_de(dt(hora)), status)


def gravar(ambiente, *consultas):
    for c in consultas:
        ambiente.consultas.adicionar(c)


class TestCadastros:
    def test_obtem_paciente(self, ambiente):
        assert ambiente.pacientes.obter_por_id(7) == Paciente(7, "Ana", "ana@exemplo.com")

    def test_paciente_inexistente(self, ambiente):
        assert ambiente.pacientes.obter_por_id(999) is None

    def test_obtem_profissional_com_especialidade(self, ambiente):
        profissional = ambiente.profissionais.obter_por_id(10)
        assert profissional == Profissional(10, "Dr. João", Especialidade(1, "Clínica Geral"))

    def test_profissional_inexistente(self, ambiente):
        assert ambiente.profissionais.obter_por_id(999) is None

    def test_lista_profissionais_por_especialidade(self, ambiente):
        assert [p.id for p in ambiente.profissionais.listar_por_especialidade("Odontologia")] == [11]
        assert ambiente.profissionais.listar_por_especialidade("Pediatria") == []


class TestConsultas:
    def test_adicionar_atribui_id_e_a_consulta_e_lida_de_volta(self, ambiente):
        consulta = ambiente.consultas.adicionar(nova_consulta())
        assert consulta.id is not None
        assert ambiente.consultas.listar_consultas_ativas_paciente(7) == [consulta]

    def test_conflito_do_profissional(self, ambiente):
        gravar(ambiente, nova_consulta(paciente=7))
        with pytest.raises(ConflitoDePersistenciaError) as erro:
            ambiente.consultas.adicionar(nova_consulta(paciente=8))
        assert erro.value.participante == "profissional"

    def test_conflito_do_paciente(self, ambiente):
        gravar(ambiente, nova_consulta(profissional=10))
        with pytest.raises(ConflitoDePersistenciaError) as erro:
            ambiente.consultas.adicionar(nova_consulta(profissional=11))
        assert erro.value.participante == "paciente"

    def test_consulta_cancelada_nao_bloqueia_o_horario(self, ambiente):
        gravar(ambiente, nova_consulta(status=StatusConsulta.CANCELADA))
        gravar(ambiente, nova_consulta(paciente=8))  # não levanta

    def test_ativas_do_profissional_usa_intervalo_semiaberto(self, ambiente):
        gravar(ambiente, nova_consulta(hora=10))  # 10:00–10:30
        dentro = ambiente.consultas.listar_consultas_ativas_profissional(10, dt(10, 15), dt(11))
        encostado = ambiente.consultas.listar_consultas_ativas_profissional(10, dt(10, 30), dt(11))
        outro = ambiente.consultas.listar_consultas_ativas_profissional(11, dt(9), dt(12))
        assert len(dentro) == 1
        assert encostado == []
        assert outro == []

    def test_ativas_do_profissional_ignoram_canceladas(self, ambiente):
        gravar(ambiente, nova_consulta(status=StatusConsulta.CANCELADA))
        assert ambiente.consultas.listar_consultas_ativas_profissional(10, dt(0), dt(23)) == []

    def test_ativas_do_paciente_ignoram_canceladas(self, ambiente):
        gravar(
            ambiente,
            nova_consulta(hora=9),
            nova_consulta(hora=10, status=StatusConsulta.CANCELADA),
        )
        (ativa,) = ambiente.consultas.listar_consultas_ativas_paciente(7)
        assert ativa.slot.inicio == dt(9)


class TestAgendas:
    def test_le_os_horarios_de_atendimento_do_profissional(self, ambiente):
        horarios = [
            HorarioAtendimento(1, time(8, 0), time(12, 0)),
            HorarioAtendimento(1, time(14, 0), time(18, 30)),
        ]
        ambiente.semear_horarios(10, horarios)
        assert ambiente.agendas.obter_horarios_atendimento(10) == horarios
        assert ambiente.agendas.obter_horarios_atendimento(11) != horarios

    def test_profissional_sem_horarios(self, ambiente):
        ambiente.semear_horarios(10, [])
        assert ambiente.agendas.obter_horarios_atendimento(10) == []

    def test_bloqueios_individual_e_coletivo(self, ambiente):
        ambiente.semear_bloqueio(10, Bloqueio(dt(9), dt(10), "reunião"))
        ambiente.semear_bloqueio(None, Bloqueio(dt(9), dt(10), "feriado"))
        ambiente.semear_bloqueio(11, Bloqueio(dt(9), dt(10), "de outra pessoa"))
        bloqueios = ambiente.agendas.listar_bloqueios(10, dt(0), dt(23))
        assert {b.motivo for b in bloqueios} == {"reunião", "feriado"}

    def test_bloqueios_respeitam_o_intervalo(self, ambiente):
        ambiente.semear_bloqueio(10, Bloqueio(dt(9), dt(10), "reunião"))
        assert ambiente.agendas.listar_bloqueios(10, dt(10), dt(11)) == []
        assert len(ambiente.agendas.listar_bloqueios(10, dt(9, 30), dt(11))) == 1


class TestNotificacoesPendentes:
    @staticmethod
    def pendente(texto="oi"):
        return NotificacaoPendente(Notificacao("ana@exemplo.com", TipoNotificacao.AGENDAMENTO, texto))

    def test_adicionar_atribui_id_e_lista_para_envio(self, ambiente):
        registrada = ambiente.notificacoes_pendentes.adicionar(self.pendente())
        assert registrada.id is not None
        (lida,) = ambiente.notificacoes_pendentes.listar_para_envio()
        assert lida.notificacao.texto == "oi"
        assert lida.estado == EstadoNotificacao.PENDENTE
        assert lida.tentativas == 0

    def test_enviada_sai_da_lista_e_falha_continua(self, ambiente):
        a = ambiente.notificacoes_pendentes.adicionar(self.pendente("a"))
        b = ambiente.notificacoes_pendentes.adicionar(self.pendente("b"))
        a.marcar_enviada()
        b.registrar_falha("timeout")
        ambiente.notificacoes_pendentes.atualizar(a)
        ambiente.notificacoes_pendentes.atualizar(b)
        (restante,) = ambiente.notificacoes_pendentes.listar_para_envio()
        assert restante.notificacao.texto == "b"
        assert restante.estado == EstadoNotificacao.FALHA
        assert restante.tentativas == 1
        assert restante.ultimo_erro == "timeout"

    def test_respeita_o_limite(self, ambiente):
        for i in range(3):
            ambiente.notificacoes_pendentes.adicionar(self.pendente(str(i)))
        assert len(ambiente.notificacoes_pendentes.listar_para_envio(limite=2)) == 2
