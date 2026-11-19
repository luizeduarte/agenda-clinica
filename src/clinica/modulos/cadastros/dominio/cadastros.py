"""Conceitos de cadastro. Apenas dados mínimos.

Ver ``docs/responsabilidades.md`` seção 2.1.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Especialidade:
    id: int
    nome: str


@dataclass(frozen=True)
class Paciente:
    id: int
    nome: str
    email: str


@dataclass(frozen=True)
class Profissional:
    id: int
    nome: str
    especialidade: Especialidade
