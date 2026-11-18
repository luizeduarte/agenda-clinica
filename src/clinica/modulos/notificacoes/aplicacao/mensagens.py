"""Montagem das mensagens (ASR-02)."""
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.cadastros.dominio.cadastros import Paciente, Profissional
from clinica.modulos.notificacoes.dominio.notificacao import Notificacao


def notificacao_de_agendamento(
    paciente: Paciente, profissional: Profissional, slot: Slot
) -> Notificacao:
    return Notificacao.de_agendamento(
        destinatario=paciente.email,
        nome_paciente=paciente.nome,
        nome_profissional=profissional.nome,
        nome_especialidade=profissional.especialidade.nome,
        inicio=slot.inicio,
    )
