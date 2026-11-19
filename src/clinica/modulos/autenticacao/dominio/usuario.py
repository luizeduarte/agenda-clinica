"""Entidades e objetos de valor do módulo ``autenticacao`` (RNF03)."""
from dataclasses import dataclass
from enum import Enum


class Papel(str, Enum):
    PACIENTE = "PACIENTE"
    PROFISSIONAL = "PROFISSIONAL"  # inclui estagiários


@dataclass(frozen=True)
class Usuario:
    id: int
    papel: Papel
