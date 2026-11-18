import sqlite3

from clinica.modulos.notificacoes.dominio.notificacao import (
    EstadoNotificacao,
    Notificacao,
    NotificacaoPendente,
    TipoNotificacao,
)
from clinica.modulos.notificacoes.portas.notificacao_pendente_repositorio import (
    NotificacaoPendenteRepositorio,
)


class SQLiteNotificacaoPendenteRepositorio(NotificacaoPendenteRepositorio):
    """Implementa a tabela de pendências (Transactional Outbox, ADR-002).

    Usa a conexão da unidade de trabalho: a pendência só existe se a consulta
    que a originou for confirmada na mesma transação.
    """

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._con = conexao

    @staticmethod
    def _para_pendente(linha: sqlite3.Row) -> NotificacaoPendente:
        return NotificacaoPendente(
            notificacao=Notificacao(
                linha["destinatario"], TipoNotificacao(linha["tipo"]), linha["texto"]
            ),
            estado=EstadoNotificacao(linha["estado"]),
            tentativas=linha["tentativas"],
            ultimo_erro=linha["ultimo_erro"],
            id=linha["id"],
        )

    def adicionar(self, pendente: NotificacaoPendente) -> NotificacaoPendente:
        n = pendente.notificacao
        cursor = self._con.execute(
            "INSERT INTO notificacao_pendente"
            " (destinatario, tipo, texto, estado, tentativas, ultimo_erro)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                n.destinatario,
                n.tipo.value,
                n.texto,
                pendente.estado.value,
                pendente.tentativas,
                pendente.ultimo_erro,
            ),
        )
        pendente.id = cursor.lastrowid
        return pendente

    def listar_para_envio(self, limite: int = 50) -> list[NotificacaoPendente]:
        linhas = self._con.execute(
            "SELECT * FROM notificacao_pendente WHERE estado IN ('PENDENTE', 'FALHA')"
            " ORDER BY id LIMIT ?",
            (limite,),
        )
        return [self._para_pendente(linha) for linha in linhas]

    def atualizar(self, pendente: NotificacaoPendente) -> None:
        self._con.execute(
            "UPDATE notificacao_pendente SET estado = ?, tentativas = ?, ultimo_erro = ?"
            " WHERE id = ?",
            (pendente.estado.value, pendente.tentativas, pendente.ultimo_erro, pendente.id),
        )
