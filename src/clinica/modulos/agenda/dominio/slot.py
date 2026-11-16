"""Objeto de valor ``Slot`` (``PeriodoConsulta``): intervalo ``[inicio, fim)``.

PACOTE 1: implementar a validação de duração/alinhamento (RN02) e
``sobrepoe``. Os atributos já estão fixados porque as portas dependem deles.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Slot:
    inicio: datetime
    fim: datetime
