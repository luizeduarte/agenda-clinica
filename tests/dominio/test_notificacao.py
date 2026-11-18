from clinica.modulos.notificacoes.dominio.notificacao import (
    EstadoNotificacao,
    Notificacao,
    NotificacaoPendente,
    TipoNotificacao,
)


def test_registra_falha_e_sucesso_posterior():
    pendente = NotificacaoPendente(Notificacao("ana@exemplo.com", TipoNotificacao.AGENDAMENTO, "Olá"))
    assert (pendente.estado, pendente.tentativas, pendente.ultimo_erro) == (EstadoNotificacao.PENDENTE, 0, None)

    pendente.registrar_tentativa("Canal indisponível")
    assert (pendente.estado, pendente.tentativas, pendente.ultimo_erro) == (
        EstadoNotificacao.FALHA, 1, "Canal indisponível"
    )

    pendente.registrar_tentativa(None)
    assert (pendente.estado, pendente.tentativas, pendente.ultimo_erro) == (EstadoNotificacao.ENVIADA, 2, None)

    # Se outra tentativa já estava em curso, uma falha tardia preserva o sucesso.
    pendente.registrar_tentativa("Falha tardia")
    assert (pendente.estado, pendente.tentativas, pendente.ultimo_erro) == (EstadoNotificacao.ENVIADA, 3, None)
