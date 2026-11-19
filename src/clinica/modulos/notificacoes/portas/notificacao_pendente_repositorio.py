from abc import ABC, abstractmethod

from clinica.modulos.notificacoes.dominio.notificacao import NotificacaoPendente


class NotificacaoPendenteRepositorio(ABC):
    """Tabela de pendências (Transactional Outbox, ADR-002)."""

    @abstractmethod
    def adicionar(self, pendente: NotificacaoPendente) -> NotificacaoPendente:
        """Registra a pendência; participa da transação da ``UnidadeDeTrabalho``."""

    @abstractmethod
    def listar_para_envio(self, limite: int = 50) -> list[NotificacaoPendente]:
        """Pendências ``PENDENTE`` ou ``FALHA``, priorizando as menos tentadas."""

    @abstractmethod
    def obter_por_id(self, pendente_id: int) -> NotificacaoPendente | None:
        """Estado atual de uma pendência, ou ``None`` se não existir."""

    @abstractmethod
    def atualizar(self, pendente: NotificacaoPendente) -> None:
        """Registra estado, tentativas e último erro após uma tentativa de envio."""
