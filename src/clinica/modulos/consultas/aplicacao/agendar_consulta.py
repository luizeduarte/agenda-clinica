"""Caso de uso ``AgendarConsulta`` (RF03, RF06, RF08; ASR-01, ASR-03)."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from clinica.compartilhado.erros import (
    ConflitoDePersistenciaError,
    ConflitoDoPacienteError,
    EntidadeNaoEncontradaError,
    HorarioIndisponivelError,
)
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.aplicacao.agenda_do_profissional import (
    carregar_agenda_do_profissional,
)
from clinica.modulos.consultas.dominio.agenda_paciente import AgendaPaciente
from clinica.modulos.consultas.dominio.consulta import Consulta
from clinica.modulos.consultas.portas.unidade_de_trabalho import UnidadeDeTrabalho
from clinica.modulos.notificacoes.aplicacao.mensagens import notificacao_de_agendamento
from clinica.modulos.notificacoes.dominio.notificacao import NotificacaoPendente


@dataclass(frozen=True)
class AgendarConsultaComando:
    paciente_id: int
    profissional_id: int
    inicio: datetime


class AgendarConsulta:
    """Coordena o agendamento; as regras ficam no domínio.

    Recebe uma *fábrica* de ``UnidadeDeTrabalho``: cada execução tem a sua
    transação, o que permite requisições concorrentes (ASR-01).
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnidadeDeTrabalho],
        relogio: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._uow_factory = uow_factory
        self._relogio = relogio

    def executar(self, comando: AgendarConsultaComando) -> Consulta:
        """Registra a consulta como ``AGENDADA`` e a notificação pendente, atomicamente.

        Raises:
            SlotInvalidoError: horário fora da grade de 30 minutos.
            EntidadeNaoEncontradaError: paciente ou profissional inexistente.
            HorarioIndisponivelError: fora do atendimento, bloqueado ou ocupado.
            ConflitoDoPacienteError: o paciente já tem consulta nesse horário.
            LimiteDoPacienteExcedidoError: viola a RN08.
        """
        slot = Slot.a_partir_de(comando.inicio)

        with self._uow_factory() as uow:
            paciente = uow.pacientes.obter_por_id(comando.paciente_id)
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
                paciente.id, uow.consultas.listar_ativas_do_paciente(paciente.id)
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
                NotificacaoPendente(notificacao_de_agendamento(paciente, profissional, slot))
            )
            uow.commit()
            return consulta
