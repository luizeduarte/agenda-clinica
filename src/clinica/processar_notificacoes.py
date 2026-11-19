"""Executa um lote de notificações no banco do protótipo."""
import argparse
import os
from contextlib import contextmanager
from pathlib import Path

from clinica.infraestrutura.notificacoes.notificador_fake import NotificadorFake
from clinica.infraestrutura.persistencia import SQLiteUnidadeDeTrabalho
from clinica.modulos.notificacoes.aplicacao.processador_de_notificacoes import (
    LIMITE_PADRAO,
    ProcessadorDeNotificacoes,
)
from clinica.modulos.notificacoes.portas.notificador import Notificador


def criar_processador(caminho: str | Path, notificador: Notificador) -> ProcessadorDeNotificacoes:
    uow = SQLiteUnidadeDeTrabalho(caminho)

    @contextmanager
    def ler():
        with uow.leitura():
            yield uow.notificacoes_pendentes

    @contextmanager
    def gravar():
        with uow:
            yield uow.notificacoes_pendentes
            uow.commit()

    return ProcessadorDeNotificacoes(notificador, ler, gravar)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--banco", type=Path, default=os.environ.get("CLINICA_DB", "clinica.db"),
        help="Arquivo SQLite (por padrão, CLINICA_DB ou clinica.db).",
    )
    parser.add_argument(
        "--limite", type=int, default=LIMITE_PADRAO,
        help="Máximo de tentativas neste lote (padrão: %(default)s).",
    )
    parser.add_argument(
        "--simular-falha", action="store_true", help="Faz o canal simulado falhar em cada envio.",
    )
    opcoes = parser.parse_args()
    if opcoes.limite < 1:
        parser.error("O limite deve ser um inteiro positivo.")
    if not opcoes.banco.is_file():
        parser.error("Banco não encontrado. Inicie a API antes de processar as notificações.")

    processador = criar_processador(opcoes.banco, NotificadorFake(falhar=opcoes.simular_falha))
    resultados = processador.executar(opcoes.limite)
    if not resultados:
        print("Nenhuma notificação disponível para envio.")
    for pendente in resultados:
        mensagem = f"Notificação {pendente.id} · {pendente.estado.value} · tentativas {pendente.tentativas}"
        if pendente.ultimo_erro:
            mensagem += f" · {pendente.ultimo_erro}"
        print(mensagem)


if __name__ == "__main__":
    main()
