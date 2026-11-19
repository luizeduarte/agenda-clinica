from abc import ABC, abstractmethod

from clinica.modulos.autenticacao.dominio.usuario import Papel, Usuario


class ServicoAutenticacao(ABC):
    """Contrato com a autenticação universitária (RNF03, restrição 5.2)."""

    @abstractmethod
    def identificar(self, credencial: str) -> Usuario:
        """Resolve a credencial (ex.: token do cabeçalho) em um ``Usuario``.

        Raises:
            NaoAutenticadoError: credencial desconhecida ou inválida.
        """


__all__ = ["Papel", "ServicoAutenticacao", "Usuario"]
