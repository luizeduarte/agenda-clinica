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
        """O paciente confirma (RF07). Só vale para consulta ``AGENDADA``."""
        self._exigir(self.status == StatusConsulta.AGENDADA, "confirmar")
        self.status = StatusConsulta.CONFIRMADA

    def cancelar(self) -> None:
        """Libera o slot (RN03). Só vale para consulta ativa."""
        self._exigir(self.esta_ativa, "cancelar")
        self.status = StatusConsulta.CANCELADA

    def registrar_realizada(self) -> None:
        self._exigir(self.esta_ativa, "registrar como realizada")
        self.status = StatusConsulta.REALIZADA

    def registrar_falta(self) -> None:
        self._exigir(self.esta_ativa, "registrar falta")
        self.status = StatusConsulta.FALTOU

    def _exigir(self, condicao: bool, acao: str) -> None:
        if not condicao:
            raise TransicaoInvalidaError(
                f"Não é possível {acao} uma consulta {self.status.value}."
            )
