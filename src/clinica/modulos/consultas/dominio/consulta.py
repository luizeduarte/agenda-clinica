"""Entidade ``Consulta`` e seus estados (RN03, RN07).

PACOTE 1: implementar as transições (``confirmar``, ``cancelar``, ...) e
``esta_ativa``. Os atributos já estão fixados porque as portas dependem deles.
"""
from dataclasses import dataclass
from enum import Enum

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
    """``id`` é ``None`` até ser persistida."""

    paciente_id: int
    profissional_id: int
    slot: Slot
    status: StatusConsulta = StatusConsulta.AGENDADA
    id: int | None = None
