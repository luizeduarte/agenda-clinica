from clinica.modulos.notificacoes.dominio.notificacao import (
    EstadoNotificacao,
    Notificacao,
    NotificacaoPendente,
    TipoNotificacao,
)


def test_registra_falha_e_sucesso_posterior():
    pendente = NotificacaoPendente(Notificacao("ana@exemplo.com", TipoNotificacao.AGENDAMENTO, "Olá"))
    assert (pendente.estado, pendente.tentativas, pendente.ultimo_erro) == (EstadoNotificacao.PENDENTE, 0, None)

    pendente.registrar_falha("Canal indisponível")
    assert (pendente.estado, pendente.tentativas, pendente.ultimo_erro) == (
        EstadoNotificacao.FALHA, 1, "Canal indisponível"
    )

    pendente.marcar_enviada()
    assert (pendente.estado, pendente.tentativas, pendente.ultimo_erro) == (EstadoNotificacao.ENVIADA, 2, None)

    # Se outra tentativa já estava em curso, uma falha tardia preserva o sucesso.
    pendente.registrar_falha("Falha tardia")
    assert (pendente.estado, pendente.tentativas, pendente.ultimo_erro) == (EstadoNotificacao.ENVIADA, 3, None)


def test_estado_so_muda_pelos_metodos():
    pendente = NotificacaoPendente(Notificacao("ana@exemplo.com", TipoNotificacao.AGENDAMENTO, "Olá"))
    for atributo, valor in [("estado", EstadoNotificacao.ENVIADA), ("tentativas", 5), ("ultimo_erro", "x"), ("id", 1)]:
        try:
            setattr(pendente, atributo, valor)
        except AttributeError:
            continue
        raise AssertionError(f"{atributo} pôde ser alterado por fora")


def test_com_id_devolve_copia_sem_alterar_a_original():
    pendente = NotificacaoPendente(Notificacao("ana@exemplo.com", TipoNotificacao.AGENDAMENTO, "Olá"))
    registrada = pendente.com_id(7)
    assert (pendente.id, registrada.id) == (None, 7)
    assert registrada.notificacao == pendente.notificacao
