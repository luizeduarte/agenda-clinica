"""Montagem das mensagens. Texto neutro quanto ao canal (ASR-02)."""
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.cadastros.dominio.cadastros import Paciente, Profissional
from clinica.modulos.notificacoes.dominio.notificacao import Notificacao, TipoNotificacao


def notificacao_de_agendamento(
    paciente: Paciente, profissional: Profissional, slot: Slot
) -> Notificacao:
    quando = f"{slot.inicio:%d/%m/%Y} às {slot.inicio:%H:%M}"
    return Notificacao(
        destinatario=paciente.email,
        tipo=TipoNotificacao.AGENDAMENTO,
        texto=(
            f"Olá, {paciente.nome}. Sua consulta de {profissional.especialidade.nome} "
            f"com {profissional.nome} foi agendada para {quando}."
        ),
    )
