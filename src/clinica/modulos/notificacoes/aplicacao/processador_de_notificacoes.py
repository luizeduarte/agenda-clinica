"""Envio posterior de notificações e registro de tentativas (ADR-002)."""
from collections.abc import Callable
from contextlib import AbstractContextManager

from clinica.compartilhado.erros import FalhaNoEnvioError
from clinica.modulos.notificacoes.dominio.notificacao import EstadoNotificacao, NotificacaoPendente
from clinica.modulos.notificacoes.portas.notificacao_pendente_repositorio import (
    NotificacaoPendenteRepositorio,
)
from clinica.modulos.notificacoes.portas.notificador import Notificador

LIMITE_PADRAO = 50


class ProcessadorDeNotificacoes:
    def __init__(
        self,
        notificador: Notificador,
        ler: Callable[[], AbstractContextManager[NotificacaoPendenteRepositorio]],
        gravar: Callable[[], AbstractContextManager[NotificacaoPendenteRepositorio]],
    ) -> None:
        self._notificador = notificador
        self._ler = ler
        self._gravar = gravar

    def executar(self, limite: int = LIMITE_PADRAO) -> list[NotificacaoPendente]:
        if limite < 1:
            raise ValueError("O limite deve ser um inteiro positivo.")

        with self._ler() as repositorio:
            candidatas = repositorio.listar_para_envio(limite)

        resultados = []
        for candidata in candidatas:
            if candidata.id is None:
                raise RuntimeError("A pendência deve estar registrada para ser processada.")

            with self._ler() as repositorio:
                pendente = repositorio.obter_por_id(candidata.id)
            if pendente is None or pendente.estado == EstadoNotificacao.ENVIADA:
                continue

            # As conexões são fechadas antes de chamar o canal.
            falha = None
            try:
                self._notificador.enviar(pendente.notificacao)
            except FalhaNoEnvioError as erro:
                falha = erro

            with self._gravar() as repositorio:
                atual = repositorio.obter_por_id(candidata.id)
                if atual is None:
                    raise RuntimeError("A pendência não foi encontrada ao registrar a tentativa.")
                if falha is None:
                    atual.marcar_enviada()
                else:
                    atual.registrar_falha(str(falha))
                repositorio.atualizar(atual)
            resultados.append(atual)

        return resultados
