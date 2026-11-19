"""Canal de notificações simulado para a demonstração."""
from clinica.compartilhado.erros import FalhaNoEnvioError
from clinica.modulos.notificacoes.dominio.notificacao import Notificacao
from clinica.modulos.notificacoes.portas.notificador import Notificador


class NotificadorFake(Notificador):
    def __init__(self, *, falhar: bool = False) -> None:
        self._falhar = falhar
        self.enviadas: list[Notificacao] = []

    def enviar(self, notificacao: Notificacao) -> None:
        if self._falhar:
            raise FalhaNoEnvioError("Falha simulada no canal de notificações.")
        self.enviadas.append(notificacao)
