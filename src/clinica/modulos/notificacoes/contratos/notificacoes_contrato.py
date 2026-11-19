"""Contrato público do módulo ``notificacoes`` para comunicação entre módulos."""
from datetime import datetime

from clinica.modulos.notificacoes.dominio.notificacao import Notificacao, NotificacaoPendente
from clinica.modulos.notificacoes.portas.notificacao_pendente_repositorio import (
    NotificacaoPendenteRepositorio,
)


class Notificacoes:
    """Fachada contratual do módulo ``notificacoes`` com ``@classmethod``s."""

    _pendentes: NotificacaoPendenteRepositorio | None = None

    @classmethod
    def configurar(cls, pendentes: NotificacaoPendenteRepositorio) -> None:
        cls._pendentes = pendentes

    @classmethod
    def _repositorio(cls) -> NotificacaoPendenteRepositorio:
        if cls._pendentes is None:
            raise RuntimeError("Notificacoes não configurado com NotificacaoPendenteRepositorio.")
        return cls._pendentes

    @classmethod
    def registrar_agendamento(
        cls,
        destinatario: str,
        nome_paciente: str,
        nome_profissional: str,
        nome_especialidade: str,
        inicio: datetime,
    ) -> None:
        """Registra uma notificação de agendamento pendente na fila (ASR-03)."""
        notificacao = Notificacao.de_agendamento(
            destinatario=destinatario,
            nome_paciente=nome_paciente,
            nome_profissional=nome_profissional,
            nome_especialidade=nome_especialidade,
            inicio=inicio,
        )
        cls._repositorio().adicionar(NotificacaoPendente(notificacao))
