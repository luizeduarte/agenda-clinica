from datetime import datetime
from typing import Protocol

from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento


class AgendaRepositorio(Protocol):
    """Persistência de períodos de atendimento e bloqueios."""

    def obter_horarios_atendimento(self, profissional_id: int) -> list[HorarioAtendimento]: ...

    def salvar_horarios_atendimento(
        self, profissional_id: int, horarios: list[HorarioAtendimento]
    ) -> None:
        """Substitui a grade semanal do profissional (RF01)."""
        ...

    def listar_bloqueios(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Bloqueio]:
        """Bloqueios do profissional **e coletivos** que intersectam ``[inicio, fim)`` (RN04)."""
        ...

    def adicionar_bloqueio(self, profissional_id: int | None, bloqueio: Bloqueio) -> Bloqueio:
        """``profissional_id=None`` registra bloqueio coletivo (feriado). Devolve com ``id``."""
        ...
