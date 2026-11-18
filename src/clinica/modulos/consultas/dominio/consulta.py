"""Entidade ``Consulta`` e seus estados (RN03, RN07)."""
from dataclasses import dataclass
from enum import Enum

from clinica.compartilhado.erros import TransicaoInvalidaError
from clinica.modulos.agenda.dominio.slot import Slot


class StatusConsulta(str, Enum):
    AGENDADA = "AGENDADA"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    REALIZADA = "REALIZADA"
    FALTOU = "FALTOU"


# Estados que ocupam o slot (RN03).
STATUS_ATIVOS = frozenset({StatusConsulta.AGENDADA, StatusConsulta.CONFIRMADA})


@dataclass
class Consulta:
    """Nasce ``AGENDADA`` (RN07). ``id`` é ``None`` até ser persistida.

    ``especialidade_id`` é copiado do profissional no momento do agendamento.
    Assim ``AgendaPaciente`` aplica o limite por especialidade (RN08) usando
    apenas as consultas, sem consultar cadastros.
    """

    paciente_id: int
    profissional_id: int
    especialidade_id: int
    slot: Slot
    status: StatusConsulta = StatusConsulta.AGENDADA
    id: int | None = None

    @property
    def esta_ativa(self) -> bool:
        return self.status in STATUS_ATIVOS

    def confirmar(self) -> None:
        """Confirma a presença do paciente em uma consulta ``AGENDADA`` (RF07)."""
        if self.status != StatusConsulta.AGENDADA:
            raise TransicaoInvalidaError(
                f"Não é possível confirmar uma consulta no estado {self.status.value}."
            )
        self.status = StatusConsulta.CONFIRMADA

    def cancelar(self) -> None:
        """Cancela uma consulta ativa, liberando o slot (RF04, RN03)."""
        if not self.esta_ativa:
            raise TransicaoInvalidaError(
                f"Não é possível cancelar uma consulta no estado {self.status.value}."
            )
        self.status = StatusConsulta.CANCELADA
