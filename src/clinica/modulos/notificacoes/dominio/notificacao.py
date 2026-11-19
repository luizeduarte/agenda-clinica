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


class NotificacaoPendente:
    """Linha da tabela de pendências (Transactional Outbox).

    Permanece ``PENDENTE`` ou ``FALHA`` até o envio ter sucesso (reenvio).
    O estado só muda por ``marcar_enviada`` e ``registrar_falha``; ``id`` é
    ``None`` até ser persistida, e o repositório devolve uma cópia com o
    ``id`` gerado (``com_id``).
    """

    def __init__(
        self,
        notificacao: Notificacao,
        estado: EstadoNotificacao = EstadoNotificacao.PENDENTE,
        tentativas: int = 0,
        ultimo_erro: str | None = None,
        id: int | None = None,
    ) -> None:
        self._notificacao = notificacao
        self._estado = estado
        self._tentativas = tentativas
        self._ultimo_erro = ultimo_erro
        self._id = id

    @property
    def notificacao(self) -> Notificacao:
        return self._notificacao

    @property
    def estado(self) -> EstadoNotificacao:
        return self._estado

    @property
    def tentativas(self) -> int:
        return self._tentativas

    @property
    def ultimo_erro(self) -> str | None:
        return self._ultimo_erro

    @property
    def id(self) -> int | None:
        return self._id

    def com_id(self, id: int) -> "NotificacaoPendente":
        """Cópia com o ``id`` gerado pela persistência."""
        return NotificacaoPendente(
            self._notificacao, self._estado, self._tentativas, self._ultimo_erro, id
        )

    def marcar_enviada(self) -> None:
        """Registra que o envio teve sucesso (ASR-03)."""
        self._tentativas += 1
        self._estado = EstadoNotificacao.ENVIADA
        self._ultimo_erro = None

    def registrar_falha(self, erro: str) -> None:
        """Registra uma tentativa frustrada mantendo a pendência elegível para reenvio.

        Se outra execução já a tinha enviado, conta a tentativa mas continua
        ``ENVIADA``: voltar para ``FALHA`` faria a mensagem ser enviada de novo.
        """
        self._tentativas += 1
        if self._estado == EstadoNotificacao.ENVIADA:
            return
        self._estado = EstadoNotificacao.FALHA
        self._ultimo_erro = erro

    def __repr__(self) -> str:
        return (
            f"NotificacaoPendente(id={self._id}, estado={self._estado.value},"
            f" tentativas={self._tentativas}, ultimo_erro={self._ultimo_erro!r})"
        )
