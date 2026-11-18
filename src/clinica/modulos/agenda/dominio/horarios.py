"""Períodos de atendimento recorrentes e bloqueios datados (RN01, RN02, RN04)."""
from dataclasses import dataclass
from datetime import date, datetime, time

from clinica.compartilhado.erros import HorarioDeAtendimentoInvalidoError
from clinica.modulos.agenda.dominio.slot import DURACAO, MINUTOS_DA_GRADE, Slot


@dataclass(frozen=True)
class HorarioAtendimento:
    """Período semanal recorrente. ``dia_semana``: 0 = segunda ... 6 = domingo.

    Deve começar e terminar em ``:00`` ou ``:30`` (grade global, RN02).
    """

    dia_semana: int
    hora_inicio: time
    hora_fim: time

    @staticmethod
    def _hora_na_grade(hora: time) -> bool:
        return hora.minute in MINUTOS_DA_GRADE and hora.second == 0 and hora.microsecond == 0

    def __post_init__(self) -> None:
        if not 0 <= self.dia_semana <= 6:
            raise HorarioDeAtendimentoInvalidoError("dia_semana deve estar entre 0 e 6.")
        if self.hora_inicio >= self.hora_fim:
            raise HorarioDeAtendimentoInvalidoError("O período deve terminar depois de começar.")
        if not (self._hora_na_grade(self.hora_inicio) and self._hora_na_grade(self.hora_fim)):
            raise HorarioDeAtendimentoInvalidoError(
                "O período deve começar e terminar em :00 ou :30."
            )

    def slots_do_dia(self, dia: date) -> list[Slot]:
        """Slots de 30 minutos deste período em ``dia`` (vazio se o dia da semana não bate)."""
        if dia.weekday() != self.dia_semana:
            return []
        slots = []
        atual = datetime.combine(dia, self.hora_inicio)
        limite = datetime.combine(dia, self.hora_fim)
        while atual + DURACAO <= limite:
            slots.append(Slot.a_partir_de(atual))
            atual += DURACAO
        return slots


@dataclass(frozen=True)
class Bloqueio:
    inicio: datetime
    fim: datetime
    motivo: str
    id: int | None = None

    def __post_init__(self) -> None:
        if self.inicio >= self.fim:
            raise HorarioDeAtendimentoInvalidoError("O bloqueio deve terminar depois de começar.")

    def intersecta(self, slot: Slot) -> bool:
        return self.inicio < slot.fim and slot.inicio < self.fim
