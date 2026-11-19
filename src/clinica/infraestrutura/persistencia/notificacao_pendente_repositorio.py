import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from clinica.infraestrutura.persistencia.conexao import ConexaoSQLite
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
    """Implementa a tabela de pendências (Transactional Outbox, ADR-002)."""

    def __init__(self, banco: ConexaoSQLite | str | Path) -> None:
        self._banco = banco if isinstance(banco, ConexaoSQLite) else ConexaoSQLite(banco)

    @contextmanager
    def transacao(self) -> Iterator[None]:
        with self._banco.transacao():
            yield

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
        with self._banco.escrita() as con:
            cursor = con.execute(
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
        return pendente.com_id(cursor.lastrowid)

    def listar_para_envio(self, limite: int = 50) -> list[NotificacaoPendente]:
        with self._banco.leitura() as con:
            linhas = con.execute(
                "SELECT * FROM notificacao_pendente WHERE estado IN ('PENDENTE', 'FALHA')"
                " ORDER BY tentativas, id LIMIT ?",
                (limite,),
            ).fetchall()
        return [self._para_pendente(linha) for linha in linhas]

    def obter_por_id(self, pendente_id: int) -> NotificacaoPendente | None:
        with self._banco.leitura() as con:
            linha = con.execute(
                "SELECT * FROM notificacao_pendente WHERE id = ?", (pendente_id,)
            ).fetchone()
        return self._para_pendente(linha) if linha is not None else None

    def atualizar(self, pendente: NotificacaoPendente) -> None:
        with self._banco.escrita() as con:
            con.execute(
                "UPDATE notificacao_pendente SET estado = ?, tentativas = ?, ultimo_erro = ?"
                " WHERE id = ?",
                (pendente.estado.value, pendente.tentativas, pendente.ultimo_erro, pendente.id),
            )
