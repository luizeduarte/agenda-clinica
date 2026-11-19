from datetime import date, datetime, time, timedelta

from clinica.modulos.agenda.dominio.agenda_profissional import AgendaProfissional
from clinica.modulos.consultas.portas.unidade_de_trabalho import UnidadeDeTrabalho


def carregar_agenda_do_profissional(
    uow: UnidadeDeTrabalho, profissional_id: int, dia: date
) -> AgendaProfissional:
    """Reúne, pelos repositórios, os dados do dia e monta a ``AgendaProfissional``.

    Fica em ``consultas`` porque os slots ocupados vêm das consultas, e o módulo
    ``agenda`` não pode depender de ``consultas``.
    """
    inicio = datetime.combine(dia, time.min)
    fim = datetime.max if dia == date.max else inicio + timedelta(days=1)
    return AgendaProfissional(
        profissional_id=profissional_id,
        horarios_atendimento=uow.agendas.obter_horarios_atendimento(profissional_id),
        bloqueios=uow.agendas.listar_bloqueios(profissional_id, inicio, fim),
        slots_ocupados=[
            c.slot for c in uow.consultas.listar_consultas_ativas_profissional(profissional_id, inicio, fim)
        ],
    )
