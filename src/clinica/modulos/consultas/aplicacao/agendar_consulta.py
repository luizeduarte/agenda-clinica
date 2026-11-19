"""Caso de uso ``AgendarConsulta`` (RF03, RF06, RF08; ASR-01, ASR-03)."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from clinica.compartilhado.erros import (
    ConflitoDePersistenciaError,
    ConflitoDoPacienteError,
    HorarioIndisponivelError,
    NaoAutorizadoError,
    SlotInvalidoError,
)
from clinica.modulos.agenda.contratos import Agenda, Slot
from clinica.modulos.autenticacao.contratos import Papel, Usuario
from clinica.modulos.cadastros.contratos import Cadastros
from clinica.modulos.consultas.dominio.agenda_paciente import AgendaPaciente
from clinica.modulos.consultas.dominio.consulta import Consulta
from clinica.modulos.consultas.portas.consulta_repositorio import ConsultaRepositorio
from clinica.modulos.notificacoes.contratos import Notificacoes


@dataclass(frozen=True)
class AgendarConsultaComando:
    usuario: Usuario  # quem pede; o paciente da consulta é o próprio usuário
    profissional_id: int
    inicio: datetime


class AgendarConsulta:
    """Coordena o agendamento; as regras ficam no domínio."""

    def __init__(
        self,
        consultas: ConsultaRepositorio,
        relogio: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._consultas = consultas
        self._relogio = relogio

    def executar(self, comando: AgendarConsultaComando) -> Consulta:
        """Registra a consulta como ``AGENDADA`` e a notificação pendente, atomicamente."""
        # Só o paciente agenda (RF03, RNF03).
        if comando.usuario.papel != Papel.PACIENTE:
            raise NaoAutorizadoError("Apenas pacientes podem agendar consultas.")

        # Grade e "no futuro" dependem só do horário pedido e do relógio:
        # recusa antes de ocupar o bloqueio de escrita (ADR-003).
        slot = Slot.a_partir_de(comando.inicio)
        if not slot.esta_no_futuro(self._relogio()):
            raise SlotInvalidoError("O horário da consulta deve estar no futuro.")

        # Consulta e notificação pendente só valem juntas, na mesma transação.
        with self._consultas.transacao():
            # O horário pode ter começado durante a espera por BEGIN IMMEDIATE.
            if not slot.esta_no_futuro(self._relogio()):
                raise SlotInvalidoError("O horário da consulta deve estar no futuro.")

            paciente = Cadastros.obter_paciente(comando.usuario.id)
            profissional = Cadastros.obter_profissional(comando.profissional_id)

            Agenda.verificar_disponibilidade(profissional.id, slot)

            agenda_paciente = AgendaPaciente(
                paciente.id, self._consultas.listar_consultas_ativas_paciente(paciente.id)
            )
            agenda_paciente.verificar_pode_agendar(
                slot, profissional.especialidade.id, self._relogio()
            )

            consulta = Consulta(
                paciente_id=paciente.id,
                profissional_id=profissional.id,
                especialidade_id=profissional.especialidade.id,
                slot=slot,
            )
            try:
                consulta = self._consultas.adicionar(consulta)
            except ConflitoDePersistenciaError as erro:
                # Outra reserva concorrente venceu a corrida (ASR-01).
                if erro.participante == "paciente":
                    raise ConflitoDoPacienteError(
                        "O paciente já tem uma consulta ativa nesse horário."
                    ) from erro
                raise HorarioIndisponivelError(
                    "O horário foi ocupado por outra reserva."
                ) from erro

            Notificacoes.registrar_agendamento(
                destinatario=paciente.email,
                nome_paciente=paciente.nome,
                nome_profissional=profissional.nome,
                nome_especialidade=profissional.especialidade.nome,
                inicio=slot.inicio,
            )
            return consulta
