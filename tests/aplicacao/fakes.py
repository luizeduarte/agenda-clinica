"""Repositórios e unidade de trabalho em memória, só para testar os casos de uso.

Imitam o comportamento relevante do banco: o índice único parcial por
``(participante, inicio)`` das consultas ativas e o rollback ao sair sem commit.
"""
import copy
import dataclasses
from datetime import datetime

from clinica.compartilhado.erros import ConflitoDePersistenciaError
from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento
from clinica.modulos.cadastros.dominio.cadastros import Paciente, Profissional
from clinica.modulos.consultas.dominio.consulta import Consulta
from clinica.modulos.notificacoes.dominio.notificacao import (
    EstadoNotificacao,
    NotificacaoPendente,
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


class ConsultaRepositorioEmMemoria:
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    def adicionar(self, consulta: Consulta) -> Consulta:
        if consulta.esta_ativa:
            for c in self._b.consultas:
                if c.esta_ativa and c.slot.inicio == consulta.slot.inicio:
                    if c.profissional_id == consulta.profissional_id:
                        raise ConflitoDePersistenciaError("profissional")
                    if c.paciente_id == consulta.paciente_id:
                        raise ConflitoDePersistenciaError("paciente")
        consulta.id = self._b.novo_id()
        self._b.consultas.append(consulta)
        return consulta

    def atualizar(self, consulta: Consulta) -> None:
        pass  # os objetos já são compartilhados

    def obter_por_id(self, consulta_id: int) -> Consulta | None:
        return next((c for c in self._b.consultas if c.id == consulta_id), None)

    def listar_consultas_ativas_profissional(self, profissional_id, inicio: datetime, fim: datetime):
        return [
            c for c in self._b.consultas
            if c.esta_ativa and c.profissional_id == profissional_id
            and c.slot.inicio < fim and inicio < c.slot.fim
        ]

    def listar_consultas_ativas_paciente(self, paciente_id):
        return [c for c in self._b.consultas if c.esta_ativa and c.paciente_id == paciente_id]

    def listar_consultas_paciente(self, paciente_id):
        return [c for c in self._b.consultas if c.paciente_id == paciente_id]

    def listar_consultas_profissional(self, profissional_id, inicio, fim):
        return [
            c for c in self._b.consultas
            if c.profissional_id == profissional_id and c.slot.inicio < fim and inicio < c.slot.fim
        ]


class AgendaRepositorioEmMemoria:
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    def obter_horarios_atendimento(self, profissional_id):
        return list(self._b.horarios.get(profissional_id, []))

    def salvar_horarios_atendimento(self, profissional_id, horarios):
        self._b.horarios[profissional_id] = list(horarios)

    def listar_bloqueios(self, profissional_id, inicio, fim):
        return [
            b for dono, b in self._b.bloqueios
            if dono in (profissional_id, None) and b.inicio < fim and inicio < b.fim
        ]

    def adicionar_bloqueio(self, profissional_id, bloqueio):
        bloqueio = dataclasses.replace(bloqueio, id=self._b.novo_id())
        self._b.bloqueios.append((profissional_id, bloqueio))
        return bloqueio


class PacienteRepositorioEmMemoria:
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    def obter_por_id(self, paciente_id):
        return self._b.pacientes.get(paciente_id)


class ProfissionalRepositorioEmMemoria:
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    def obter_por_id(self, profissional_id):
        return self._b.profissionais.get(profissional_id)

    def listar_por_especialidade(self, nome_especialidade):
        return [
            p for p in self._b.profissionais.values()
            if p.especialidade.nome == nome_especialidade
        ]


class NotificacaoPendenteRepositorioEmMemoria:
    def __init__(self, banco: BancoEmMemoria) -> None:
        self._b = banco

    def adicionar(self, pendente):
        pendente.id = self._b.novo_id()
        self._b.pendentes.append(pendente)
        return pendente

    def listar_para_envio(self, limite=50):
        return [
            p for p in self._b.pendentes
            if p.estado in (EstadoNotificacao.PENDENTE, EstadoNotificacao.FALHA)
        ][:limite]

    def atualizar(self, pendente):
        pass


class UnidadeDeTrabalhoEmMemoria:
    """Snapshot ao entrar; restaura se sair sem ``commit()``."""

    def __init__(self, banco: BancoEmMemoria) -> None:
        self._banco = banco
        self.consultas = ConsultaRepositorioEmMemoria(banco)
        self.agendas = AgendaRepositorioEmMemoria(banco)
        self.pacientes = PacienteRepositorioEmMemoria(banco)
        self.profissionais = ProfissionalRepositorioEmMemoria(banco)
        self.notificacoes_pendentes = NotificacaoPendenteRepositorioEmMemoria(banco)
        self._estado = None
        self._confirmada = False

    def __enter__(self):
        self._estado = copy.deepcopy(self._banco._mutavel())
        self._confirmada = False
        return self

    def __exit__(self, tipo_exc, exc, tb) -> None:
        if not self._confirmada:
            self.rollback()

    def commit(self) -> None:
        self._confirmada = True

    def rollback(self) -> None:
        self._banco.restaurar(self._estado)
