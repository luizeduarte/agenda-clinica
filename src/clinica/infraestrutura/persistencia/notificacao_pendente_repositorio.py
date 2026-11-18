import sqlite3

from clinica.modulos.notificacoes.dominio.notificacao import (
    EstadoNotificacao,
    Notificacao,
    NotificacaoPendente,
    TipoNotificacao,
)


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


class SQLiteNotificacaoPendenteRepositorio:
    """Implementa a tabela de pendências (Transactional Outbox, ADR-002).

    Usa a conexão da unidade de trabalho: a pendência só existe se a consulta
    que a originou for confirmada na mesma transação.
    """

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._con = conexao

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
            " ORDER BY tentativas, id LIMIT ?",
            (limite,),
        )
        return [_para_pendente(linha) for linha in linhas]

    def obter_por_id(self, pendente_id: int) -> NotificacaoPendente | None:
        linha = self._con.execute(
            "SELECT * FROM notificacao_pendente WHERE id = ?", (pendente_id,)
        ).fetchone()
        return _para_pendente(linha) if linha is not None else None

    def atualizar(self, pendente: NotificacaoPendente) -> None:
        self._con.execute(
            "UPDATE notificacao_pendente SET estado = ?, tentativas = ?, ultimo_erro = ?"
            " WHERE id = ?",
            (pendente.estado.value, pendente.tentativas, pendente.ultimo_erro, pendente.id),
        )
