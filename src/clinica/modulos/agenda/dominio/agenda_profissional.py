"""``AgendaProfissional``: disponibilidade de um profissional (RF02, RF06, RN01, RN03, RN04).

Avalia tudo em memória, a partir dos dados recebidos. Recebe os slots ocupados
e não objetos ``Consulta``, para que o módulo ``agenda`` não dependa de
``consultas``.
"""
from collections.abc import Iterable
from datetime import date

from clinica.compartilhado.erros import HorarioIndisponivelError
from clinica.modulos.agenda.dominio.horarios import (
    Bloqueio,
    HorarioAtendimento,
    validar_grade_semanal,
)
from clinica.modulos.agenda.dominio.slot import Slot


class AgendaProfissional:
    def __init__(
        self,
        profissional_id: int,
        horarios_atendimento: Iterable[HorarioAtendimento],
        bloqueios: Iterable[Bloqueio],
        slots_ocupados: Iterable[Slot],
    ) -> None:
        self.profissional_id = profissional_id
        self.horarios_atendimento = list(horarios_atendimento)
        validar_grade_semanal(self.horarios_atendimento)
        self.bloqueios = list(bloqueios)
        self.slots_ocupados = set(slots_ocupados)

    def slots_de_atendimento(self, dia: date) -> list[Slot]:
        """Todos os slots que o profissional oferece em ``dia``, livres ou não."""
        slots = [s for h in self.horarios_atendimento for s in h.slots_do_dia(dia)]
        return sorted(slots, key=lambda s: s.inicio)

    def slots_disponiveis(self, dia: date) -> list[Slot]:
        return [s for s in self.slots_de_atendimento(dia) if self._motivo_indisponivel(s) is None]

    def verificar_disponivel(self, slot: Slot) -> None:
        """Levanta ``HorarioIndisponivelError`` se o slot não puder ser reservado."""
        motivo = self._motivo_indisponivel(slot)
        if motivo is not None:
            raise HorarioIndisponivelError(motivo)

    def _motivo_indisponivel(self, slot: Slot) -> str | None:
        if slot not in self.slots_de_atendimento(slot.inicio.date()):
            return "O horário está fora dos períodos de atendimento do profissional."
        if any(b.intersecta(slot) for b in self.bloqueios):
            return "O horário está bloqueado na agenda do profissional."
        if slot in self.slots_ocupados:
            return "O horário já está ocupado por outra consulta do profissional."
        return None
