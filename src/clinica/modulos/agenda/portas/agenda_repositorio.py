from abc import ABC, abstractmethod
from datetime import datetime

from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento


class AgendaRepositorio(ABC):
    """Persistência de períodos de atendimento e bloqueios."""

    @abstractmethod
    def obter_horarios_atendimento(self, profissional_id: int) -> list[HorarioAtendimento]: ...

    @abstractmethod
    def listar_bloqueios(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Bloqueio]:
        """Bloqueios do profissional que intersectam ``[inicio, fim)`` (RN04)."""
