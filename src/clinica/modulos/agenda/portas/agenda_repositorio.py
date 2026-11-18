from datetime import datetime
from typing import Protocol

from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento


class AgendaRepositorio(Protocol):
    """Persistência de períodos de atendimento e bloqueios."""

    def obter_horarios_atendimento(self, profissional_id: int) -> list[HorarioAtendimento]: ...

    def listar_bloqueios(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Bloqueio]:
        """Bloqueios do profissional que intersectam ``[inicio, fim)`` (RN04)."""
        ...
