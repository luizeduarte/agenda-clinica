from abc import ABC, abstractmethod

from clinica.modulos.notificacoes.dominio.notificacao import NotificacaoPendente


class NotificacaoPendenteRepositorio(ABC):
    """Tabela de pendências (Transactional Outbox, ADR-002)."""

    @abstractmethod
    def adicionar(self, pendente: NotificacaoPendente) -> NotificacaoPendente:
        """Registra a pendência; participa da transação da ``UnidadeDeTrabalho``."""

    @abstractmethod
    def listar_para_envio(self, limite: int = 50) -> list[NotificacaoPendente]:
        """Pendências em estado ``PENDENTE`` ou ``FALHA`` (candidatas a reenvio)."""

    @abstractmethod
    def atualizar(self, pendente: NotificacaoPendente) -> None:
        """Registra estado, tentativas e último erro após uma tentativa de envio."""
