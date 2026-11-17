"""Objeto de valor ``Slot`` (``PeriodoConsulta``): intervalo ``[inicio, fim)``.

Todo slot tem 30 minutos e começa em ``:00`` ou ``:30`` (grade global, RN02).
Por isso dois slots ou são iguais ou são disjuntos, nunca se sobrepõem em parte.
É isso que permite ao banco impedir conflito por igualdade do ``inicio``.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

from clinica.compartilhado.erros import SlotInvalidoError

DURACAO = timedelta(minutes=30)
MINUTOS_DA_GRADE = (0, 30)


def esta_na_grade(momento: datetime) -> bool:
    """``True`` se o instante cai em ``:00`` ou ``:30`` exatos."""
    return (
        momento.minute in MINUTOS_DA_GRADE
        and momento.second == 0
        and momento.microsecond == 0
    )


@dataclass(frozen=True)
class Slot:
    inicio: datetime
    fim: datetime

    def __post_init__(self) -> None:
        if not esta_na_grade(self.inicio):
            raise SlotInvalidoError(f"O slot deve começar em :00 ou :30, não em {self.inicio}.")
        if self.fim - self.inicio != DURACAO:
            raise SlotInvalidoError("O slot deve durar exatamente 30 minutos.")

    @classmethod
    def a_partir_de(cls, inicio: datetime) -> "Slot":
        return cls(inicio, inicio + DURACAO)

    def sobrepoe(self, outro: "Slot") -> bool:
        return self.inicio < outro.fim and outro.inicio < self.fim
