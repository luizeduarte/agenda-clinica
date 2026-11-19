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
