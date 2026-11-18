from contextlib import contextmanager

import pytest

from clinica.infraestrutura.notificacoes.notificador_fake import NotificadorFake
from clinica.modulos.notificacoes.aplicacao.processador_de_notificacoes import ProcessadorDeNotificacoes
from clinica.modulos.notificacoes.dominio.notificacao import (
    EstadoNotificacao,
    Notificacao,
    NotificacaoPendente,
    TipoNotificacao,
)


@pytest.fixture
def configurar_processador(uow):
    @contextmanager
    def ler():
        with uow.leitura():
            yield uow.notificacoes_pendentes

    @contextmanager
    def gravar():
        with uow:
            yield uow.notificacoes_pendentes
            uow.commit()

    return lambda canal: ProcessadorDeNotificacoes(canal, ler, gravar)


def test_registra_mensagens_enviadas_respeitando_o_limite(uow, configurar_processador):
    mensagens = [Notificacao("ana@exemplo.com", TipoNotificacao.AGENDAMENTO, str(i)) for i in range(3)]
    with uow:
        for mensagem in mensagens:
            uow.notificacoes_pendentes.adicionar(NotificacaoPendente(mensagem))
        uow.commit()

    canal = NotificadorFake()
    processador = configurar_processador(canal)
    lote = processador.executar(limite=2)

    assert canal.enviadas == mensagens[:2]
    assert [(p.estado, p.tentativas, p.ultimo_erro) for p in lote] == [(EstadoNotificacao.ENVIADA, 1, None)] * 2
    assert len(processador.executar(limite=2)) == 1
    assert canal.enviadas == mensagens
    assert processador.executar() == []


@pytest.mark.parametrize("limite", [0, -1])
def test_limite_invalido(configurar_processador, limite):
    canal = NotificadorFake()
    with pytest.raises(ValueError, match="limite"):
        configurar_processador(canal).executar(limite)
    assert canal.enviadas == []
