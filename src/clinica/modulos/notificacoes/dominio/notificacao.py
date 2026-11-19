"""Notificação e seu registro de pendência (ASR-02, ASR-03).

A ``Notificacao`` é neutra quanto ao canal (sem assunto/HTML de e-mail), para
que trocar e-mail por WhatsApp/SMS não altere o contrato.
"""
from dataclasses import dataclass
from datetime import datetime
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

    @classmethod
    def de_agendamento(
        cls,
        destinatario: str,
        nome_paciente: str,
        nome_profissional: str,
        nome_especialidade: str,
        inicio: datetime,
    ) -> "Notificacao":
        quando = f"{inicio:%d/%m/%Y} às {inicio:%H:%M}"
        return cls(
            destinatario=destinatario,
            tipo=TipoNotificacao.AGENDAMENTO,
            texto=(
                f"Olá, {nome_paciente}. Sua consulta de {nome_especialidade} "
                f"com {nome_profissional} foi agendada para {quando}."
            ),
        )


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

    def marcar_enviada(self) -> None:
        """Registra que o envio teve sucesso (ASR-03)."""
        self.tentativas += 1
        self.estado = EstadoNotificacao.ENVIADA
        self.ultimo_erro = None

    def registrar_falha(self, erro: str) -> None:
        """Registra uma tentativa frustrada mantendo a pendência elegível para reenvio.

        Se outra execução já a tinha enviado, conta a tentativa mas continua
        ``ENVIADA``: voltar para ``FALHA`` faria a mensagem ser enviada de novo.
        """
        self.tentativas += 1
        if self.estado == EstadoNotificacao.ENVIADA:
            return
        self.estado = EstadoNotificacao.FALHA
        self.ultimo_erro = erro
