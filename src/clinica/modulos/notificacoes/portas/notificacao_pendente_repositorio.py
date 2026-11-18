from typing import Protocol

from clinica.modulos.notificacoes.dominio.notificacao import NotificacaoPendente


class NotificacaoPendenteRepositorio(Protocol):
    """Tabela de pendências (Transactional Outbox, ADR-002)."""

    def adicionar(self, pendente: NotificacaoPendente) -> NotificacaoPendente:
        """Registra a pendência; participa da transação da ``UnidadeDeTrabalho``."""
        ...

    def listar_para_envio(self, limite: int = 50) -> list[NotificacaoPendente]:
        """Pendências ``PENDENTE`` ou ``FALHA``, priorizando as menos tentadas."""
        ...

    def obter_por_id(self, pendente_id: int) -> NotificacaoPendente | None:
        """Obtém o estado atual de uma pendência pelo identificador."""
        ...

    def atualizar(self, pendente: NotificacaoPendente) -> None:
        """Registra estado, tentativas e último erro após uma tentativa de envio."""
        ...
