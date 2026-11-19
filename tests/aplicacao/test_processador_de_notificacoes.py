import pytest

from clinica.infraestrutura.notificacoes.notificador_fake import NotificadorFake
from clinica.modulos.notificacoes.aplicacao.processador_de_notificacoes import (
    ProcessadorDeNotificacoes,
)
from clinica.modulos.notificacoes.dominio.notificacao import (
    EstadoNotificacao,
    Notificacao,
    NotificacaoPendente,
    TipoNotificacao,
)
from tests.aplicacao.fakes import NotificacaoPendenteRepositorioEmMemoria


@pytest.fixture
def repositorio(banco):
    return NotificacaoPendenteRepositorioEmMemoria(banco)


def test_registra_mensagens_enviadas_respeitando_o_limite(repositorio):
    mensagens = [Notificacao("ana@exemplo.com", TipoNotificacao.AGENDAMENTO, str(i)) for i in range(3)]
    for mensagem in mensagens:
        repositorio.adicionar(NotificacaoPendente(mensagem))

    canal = NotificadorFake()
    processador = ProcessadorDeNotificacoes(canal, repositorio)
    lote = processador.executar(limite=2)

    assert canal.enviadas == mensagens[:2]
    assert [(p.estado, p.tentativas, p.ultimo_erro) for p in lote] == [(EstadoNotificacao.ENVIADA, 1, None)] * 2
    assert len(processador.executar(limite=2)) == 1
    assert canal.enviadas == mensagens
    assert processador.executar() == []


@pytest.mark.parametrize("limite", [0, -1])
def test_limite_invalido(repositorio, limite):
    canal = NotificadorFake()
    with pytest.raises(ValueError, match="limite"):
        ProcessadorDeNotificacoes(canal, repositorio).executar(limite)
    assert canal.enviadas == []
