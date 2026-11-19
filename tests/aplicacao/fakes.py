"""Repositórios em memória, só para testar os casos de uso.

Imitam o comportamento relevante do banco: o índice único parcial por
``(participante, inicio)`` das consultas ativas e o rollback quando uma
transação falha com exceção.
"""
import copy
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime

from clinica.compartilhado.erros import ConflitoDePersistenciaError
from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento
from clinica.modulos.agenda.portas.agenda_repositorio import AgendaRepositorio
from clinica.modulos.cadastros.dominio.cadastros import Paciente, Profissional
from clinica.modulos.cadastros.portas.repositorios import (
    PacienteRepositorio,
    ProfissionalRepositorio,
)
from clinica.modulos.consultas.dominio.consulta import Consulta
from clinica.modulos.consultas.portas.consulta_repositorio import ConsultaRepositorio
from clinica.modulos.notificacoes.dominio.notificacao import (
    EstadoNotificacao,
    NotificacaoPendente,
)
from clinica.modulos.notificacoes.portas.notificacao_pendente_repositorio import (
    NotificacaoPendenteRepositorio,
)


class BancoEmMemoria:
    def __init__(self) -> None:
        self.pacientes: dict[int, Paciente] = {}
        self.profissionais: dict[int, Profissional] = {}
        self.horarios: dict[int, list[HorarioAtendimento]] = {}
        self.bloqueios: list[tuple[int | None, Bloqueio]] = []
        self.consultas: list[Consulta] = []
        self.pendentes: list[NotificacaoPendente] = []
        self._proximo_id = 1

    def novo_id(self) -> int:
        self._proximo_id += 1
        return self._proximo_id - 1

    def _mutavel(self):
        return (self.horarios, self.bloqueios, self.consultas, self.pendentes, self._proximo_id)

    def restaurar(self, estado) -> None:
        self.horarios, self.bloqueios, self.consultas, self.pendentes, self._proximo_id = estado

    @contextmanager
    def transacao(self):
        estado = copy.deepcopy(self._mutavel())
        try:
            yield
        except BaseException:
            self.restaurar(estado)
            raise


class ConsultaRepositorioEmMemoria(ConsultaRepositorio):
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    @contextmanager
    def transacao(self):
        with self._b.transacao():
            yield

    def adicionar(self, consulta: Consulta) -> Consulta:
        if consulta.esta_ativa:
            for c in self._b.consultas:
                if c.esta_ativa and c.slot.inicio == consulta.slot.inicio:
                    if c.profissional_id == consulta.profissional_id:
                        raise ConflitoDePersistenciaError("profissional")
                    if c.paciente_id == consulta.paciente_id:
                        raise ConflitoDePersistenciaError("paciente")
        consulta = replace(consulta, id=self._b.novo_id())
        self._b.consultas.append(consulta)
        return consulta

    def listar_consultas_ativas_profissional(self, profissional_id, inicio: datetime, fim: datetime):
        return [
            c for c in self._b.consultas
            if c.esta_ativa and c.profissional_id == profissional_id
            and c.slot.inicio < fim and inicio < c.slot.fim
        ]

    def listar_consultas_ativas_paciente(self, paciente_id):
        return [c for c in self._b.consultas if c.esta_ativa and c.paciente_id == paciente_id]


class AgendaRepositorioEmMemoria(AgendaRepositorio):
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    def obter_horarios_atendimento(self, profissional_id):
        return list(self._b.horarios.get(profissional_id, []))

    def listar_bloqueios(self, profissional_id, inicio, fim):
        return [
            b for dono, b in self._b.bloqueios
            if dono in (profissional_id, None) and b.inicio < fim and inicio < b.fim
        ]


class PacienteRepositorioEmMemoria(PacienteRepositorio):
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    def obter_por_id(self, paciente_id):
        return self._b.pacientes.get(paciente_id)


class ProfissionalRepositorioEmMemoria(ProfissionalRepositorio):
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    def obter_por_id(self, profissional_id):
        return self._b.profissionais.get(profissional_id)

    def listar_por_especialidade(self, nome_especialidade):
        return [
            p for p in self._b.profissionais.values()
            if p.especialidade.nome == nome_especialidade
        ]


class NotificacaoPendenteRepositorioEmMemoria(NotificacaoPendenteRepositorio):
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    @contextmanager
    def transacao(self):
        with self._b.transacao():
            yield

    def adicionar(self, pendente):
        pendente = pendente.com_id(self._b.novo_id())
        self._b.pendentes.append(pendente)
        return pendente

    def listar_para_envio(self, limite=50):
        candidatas = [
            p for p in self._b.pendentes
            if p.estado in (EstadoNotificacao.PENDENTE, EstadoNotificacao.FALHA)
        ]
        return sorted(candidatas, key=lambda p: (p.tentativas, p.id))[:limite]

    def obter_por_id(self, pendente_id):
        return next((p for p in self._b.pendentes if p.id == pendente_id), None)

    def atualizar(self, pendente):
        self._b.pendentes = [pendente if p.id == pendente.id else p for p in self._b.pendentes]
