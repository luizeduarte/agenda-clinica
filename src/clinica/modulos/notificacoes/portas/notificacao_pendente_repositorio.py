from typing import Protocol

from clinica.modulos.notificacoes.dominio.notificacao import NotificacaoPendente


class NotificacaoPendenteRepositorio(Protocol):
    """Tabela de pendências (Transactional Outbox, ADR-002)."""

    def adicionar(self, pendente: NotificacaoPendente) -> NotificacaoPendente:
        """Registra a pendência; participa da transação da ``UnidadeDeTrabalho``."""
        ...

    def listar_para_envio(self, limite: int = 50) -> list[NotificacaoPendente]:
        """Pendências em estado ``PENDENTE`` ou ``FALHA`` (candidatas a reenvio)."""
        ...

    def atualizar(self, pendente: NotificacaoPendente) -> None:
        """Registra estado, tentativas e último erro após uma tentativa de envio."""
        ...
