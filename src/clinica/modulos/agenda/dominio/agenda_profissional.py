"""``AgendaProfissional``: disponibilidade de um profissional (RF02, RF06, RN01, RN03, RN04)."""
from collections.abc import Iterable
from datetime import date

from clinica.compartilhado.erros import (
    HorarioDeAtendimentoInvalidoError,
    HorarioIndisponivelError,
)
from clinica.modulos.agenda.dominio.horarios import Bloqueio, HorarioAtendimento
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
        self.validar_grade_semanal(self.horarios_atendimento)
        self.bloqueios = list(bloqueios)
        self.slots_ocupados = set(slots_ocupados)

    @staticmethod
    def validar_grade_semanal(horarios: list[HorarioAtendimento]) -> None:
        """Períodos do mesmo profissional no mesmo dia da semana não podem se sobrepor."""
        por_dia: dict[int, list[HorarioAtendimento]] = {}
        for horario in horarios:
            por_dia.setdefault(horario.dia_semana, []).append(horario)
        for periodos in por_dia.values():
            periodos.sort(key=lambda h: h.hora_inicio)
            for anterior, seguinte in zip(periodos, periodos[1:]):
                if seguinte.hora_inicio < anterior.hora_fim:
                    raise HorarioDeAtendimentoInvalidoError(
                        "Períodos de atendimento do mesmo dia não podem se sobrepor."
                    )

    def slots_de_atendimento(self, dia: date) -> list[Slot]:
        """Todos os slots que o profissional oferece em ``dia``, livres ou não."""
        slots = [s for h in self.horarios_atendimento for s in h.slots_do_dia(dia)]
        return sorted(slots, key=lambda s: s.inicio)

    def slots_disponiveis(self, dia: date) -> list[Slot]:
        return [s for s in self.slots_de_atendimento(dia) if self._motivo_indisponivel(s) is None]

    def verificar_disponivel(self, slot: Slot) -> None:
        motivo = self._motivo_indisponivel(slot)
        if motivo is not None:
            raise HorarioIndisponivelError(motivo)

    def _motivo_indisponivel(self, slot: Slot) -> str | None:
        if slot not in self.slots_de_atendimento(slot.inicio.date()):
            return "O horário está fora dos períodos de atendimento do profissional."
        if any(b.intersecta(slot) for b in self.bloqueios):
            return "O horário está bloqueado na agenda do profissional."
        if any(ocupado.sobrepoe(slot) for ocupado in self.slots_ocupados):
            return "O horário já está ocupado por outra consulta do profissional."
        return None
