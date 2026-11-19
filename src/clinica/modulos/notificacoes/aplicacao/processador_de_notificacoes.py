"""Envio posterior de notificações e registro de tentativas (ADR-002)."""
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
        repositorio: NotificacaoPendenteRepositorio,
    ) -> None:
        self._notificador = notificador
        self._repositorio = repositorio

    def executar(self, limite: int = LIMITE_PADRAO) -> list[NotificacaoPendente]:
        if limite < 1:
            raise ValueError("O limite deve ser um inteiro positivo.")

        candidatas = self._repositorio.listar_para_envio(limite)

        resultados = []
        for candidata in candidatas:
            if candidata.id is None:
                raise RuntimeError("A pendência deve estar registrada para ser processada.")

            pendente = self._repositorio.obter_por_id(candidata.id)
            if pendente is None or pendente.estado == EstadoNotificacao.ENVIADA:
                continue

            # As conexões são fechadas antes de chamar o canal.
            falha = None
            try:
                self._notificador.enviar(pendente.notificacao)
            except FalhaNoEnvioError as erro:
                falha = erro

            with self._repositorio.transacao():
                atual = self._repositorio.obter_por_id(candidata.id)
                if atual is None:
                    raise RuntimeError("A pendência não foi encontrada ao registrar a tentativa.")
                if falha is None:
                    atual.marcar_enviada()
                else:
                    atual.registrar_falha(str(falha))
                self._repositorio.atualizar(atual)
            resultados.append(atual)

        return resultados
