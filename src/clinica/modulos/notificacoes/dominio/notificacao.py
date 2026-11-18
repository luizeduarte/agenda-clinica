"""Notificação e seu registro de pendência (ASR-02, ASR-03).

A ``Notificacao`` é neutra quanto ao canal (sem assunto/HTML de e-mail), para
que trocar e-mail por WhatsApp/SMS não altere o contrato.
"""
from dataclasses import dataclass
from enum import Enum


class TipoNotificacao(str, Enum):
    AGENDAMENTO = "AGENDAMENTO"


class EstadoNotificacao(str, Enum):
    PENDENTE = "PENDENTE"
    ENVIADA = "ENVIADA"
    FALHA = "FALHA"


@dataclass(frozen=True)
class Notificacao:
    """Mensagem a entregar. ``destinatario`` é o contato do canal (e-mail, telefone...)."""

    destinatario: str
    tipo: TipoNotificacao
    texto: str


@dataclass
class NotificacaoPendente:
    """Linha da tabela de pendências (Transactional Outbox).

    Permanece ``PENDENTE`` ou ``FALHA`` até o envio ter sucesso (reenvio).
    """

    notificacao: Notificacao
    estado: EstadoNotificacao = EstadoNotificacao.PENDENTE
    tentativas: int = 0
    ultimo_erro: str | None = None
    id: int | None = None
