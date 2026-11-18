"""Caso de uso ``AgendarConsulta`` (RF03, RF06, RF08; ASR-01, ASR-03)."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from clinica.compartilhado.erros import (
    ConflitoDePersistenciaError,
    ConflitoDoPacienteError,
    EntidadeNaoEncontradaError,
    HorarioIndisponivelError,
    NaoAutorizadoError,
)
from clinica.modulos.autenticacao.portas.servico_autenticacao import Papel, Usuario
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.aplicacao.agenda_do_profissional import (
    carregar_agenda_do_profissional,
)
from clinica.modulos.consultas.dominio.agenda_paciente import AgendaPaciente
from clinica.modulos.consultas.dominio.consulta import Consulta
from clinica.modulos.consultas.portas.unidade_de_trabalho import UnidadeDeTrabalho
from clinica.modulos.notificacoes.dominio.notificacao import Notificacao, NotificacaoPendente


@dataclass(frozen=True)
class AgendarConsultaComando:
    usuario: Usuario  # quem pede; o paciente da consulta é o próprio usuário
    profissional_id: int
    inicio: datetime


class AgendarConsulta:
    """Coordena o agendamento; as regras ficam no domínio."""

    def __init__(
        self,
        uow: UnidadeDeTrabalho,
        relogio: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._uow = uow
        self._relogio = relogio

    def executar(self, comando: AgendarConsultaComando) -> Consulta:
        """Registra a consulta como ``AGENDADA`` e a notificação pendente, atomicamente."""
        # Só o paciente agenda (RF03, RNF03).
        if comando.usuario.papel != Papel.PACIENTE:
            raise NaoAutorizadoError("Apenas pacientes podem agendar consultas.")

        slot = Slot.a_partir_de(comando.inicio)

        # Consulta e notificação pendente só valem juntas, no commit (ver
        # UnidadeDeTrabalho). Qualquer erro antes dele desfaz as duas.
        with self._uow as uow:
            paciente = uow.pacientes.obter_por_id(comando.usuario.id)
            if paciente is None:
                raise EntidadeNaoEncontradaError("Paciente não encontrado.")
            profissional = uow.profissionais.obter_por_id(comando.profissional_id)
            if profissional is None:
                raise EntidadeNaoEncontradaError("Profissional não encontrado.")

            agenda_profissional = carregar_agenda_do_profissional(
                uow, profissional.id, slot.inicio.date()
            )
            agenda_profissional.verificar_disponivel(slot)

            agenda_paciente = AgendaPaciente(
                paciente.id, uow.consultas.listar_consultas_ativas_paciente(paciente.id)
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
                consulta = uow.consultas.adicionar(consulta)
            except ConflitoDePersistenciaError as erro:
                # Outra reserva concorrente venceu a corrida (ASR-01).
                if erro.participante == "paciente":
                    raise ConflitoDoPacienteError(
                        "O paciente já tem uma consulta ativa nesse horário."
                    ) from erro
                raise HorarioIndisponivelError(
                    "O horário foi ocupado por outra reserva."
                ) from erro

            uow.notificacoes_pendentes.adicionar(
                NotificacaoPendente(
                    Notificacao.de_agendamento(
                        destinatario=paciente.email,
                        nome_paciente=paciente.nome,
                        nome_profissional=profissional.nome,
                        nome_especialidade=profissional.especialidade.nome,
                        inicio=slot.inicio,
                    )
                )
            )
            uow.commit()
            return consulta
