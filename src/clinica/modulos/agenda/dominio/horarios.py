"""Períodos de atendimento recorrentes e bloqueios datados (RN01, RN04)."""
from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class HorarioAtendimento:
    """Período semanal recorrente. ``dia_semana``: 0 = segunda ... 6 = domingo."""

    dia_semana: int
    hora_inicio: time
    hora_fim: time


@dataclass(frozen=True)
class Bloqueio:
    """Exceção datada. ``id`` é ``None`` até ser persistido."""

    inicio: datetime
    fim: datetime
    motivo: str
    id: int | None = None
