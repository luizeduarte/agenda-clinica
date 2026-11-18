from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class Papel(str, Enum):
    PACIENTE = "PACIENTE"
    PROFISSIONAL = "PROFISSIONAL"  # inclui estagiários


@dataclass(frozen=True)
class Usuario:
    id: int
    papel: Papel


class ServicoAutenticacao(ABC):
    """Contrato com a autenticação universitária (RNF03, restrição 5.2)."""

    @abstractmethod
    def identificar(self, credencial: str) -> Usuario:
        """Resolve a credencial (ex.: token do cabeçalho) em um ``Usuario``.

        Raises:
            NaoAutenticadoError: credencial desconhecida ou inválida.
        """
