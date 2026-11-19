"""Entidade ``Consulta`` e seus estados (RN03, RN07)."""
from dataclasses import dataclass
from enum import Enum

from clinica.modulos.agenda.contratos import Slot


class StatusConsulta(str, Enum):
    AGENDADA = "AGENDADA"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    REALIZADA = "REALIZADA"
    FALTOU = "FALTOU"


# Estados que ocupam o slot (RN03).
STATUS_ATIVOS = frozenset({StatusConsulta.AGENDADA, StatusConsulta.CONFIRMADA})


@dataclass(frozen=True)
class Consulta:
    """Nasce ``AGENDADA`` (RN07). ``id`` é ``None`` até ser persistida.

    É imutável: nenhum código de fora altera seu estado diretamente. O
    repositório devolve uma cópia com o ``id`` gerado, e as transições de
    estado (fora do recorte do protótipo) também devolverão uma nova consulta.

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
