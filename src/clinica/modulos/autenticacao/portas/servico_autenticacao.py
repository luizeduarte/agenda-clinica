from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Papel(str, Enum):
    PACIENTE = "PACIENTE"
    PROFISSIONAL = "PROFISSIONAL"  # inclui estagiários


@dataclass(frozen=True)
class Usuario:
    """Identidade já autenticada. ``id`` refere-se a ``Paciente`` ou ``Profissional`` conforme o papel."""

    id: int
    papel: Papel


class ServicoAutenticacao(Protocol):
    """Contrato com a autenticação universitária (RNF03, restrição 5.2)."""

    def identificar(self, credencial: str) -> Usuario:
        """Resolve a credencial (ex.: token do cabeçalho) em um ``Usuario``.

        Raises:
            NaoAutenticadoError: credencial desconhecida ou inválida.
        """
        ...
