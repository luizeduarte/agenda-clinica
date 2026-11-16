from typing import Protocol

from clinica.modulos.notificacoes.dominio.notificacao import Notificacao


class Notificador(Protocol):
    """Contrato de envio, independente do canal (ASR-02).

    Implementações (``NotificadorFake``, e-mail, WhatsApp...) devem ser
    substituíveis entre si (LSP) sem que os casos de uso mudem.
    """

    def enviar(self, notificacao: Notificacao) -> None:
        """Entrega a notificação.

        Raises:
            FalhaNoEnvioError: o canal não conseguiu entregar (ASR-03).
        """
        ...
