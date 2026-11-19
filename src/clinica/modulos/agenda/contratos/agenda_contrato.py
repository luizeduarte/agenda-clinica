"""Contrato público do módulo ``agenda`` para comunicação entre módulos."""
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from clinica.modulos.agenda.dominio.agenda_profissional import AgendaProfissional
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.agenda.portas.agenda_repositorio import AgendaRepositorio


class Agenda:
    """Fachada contratual do módulo ``agenda`` com ``@classmethod``s."""

    _agendas: AgendaRepositorio | None = None

    @classmethod
    def configurar(cls, agendas: AgendaRepositorio) -> None:
        cls._agendas = agendas

    @classmethod
    def _repositorio(cls) -> AgendaRepositorio:
        if cls._agendas is None:
            raise RuntimeError("Agenda não configurada com AgendaRepositorio.")
        return cls._agendas

    @classmethod
    def carregar_agenda_do_dia(
        cls,
        profissional_id: int,
        dia: date,
        slots_ocupados: Iterable[Slot] | None = None,
    ) -> AgendaProfissional:
        inicio = datetime.combine(dia, time.min)
        fim = datetime.max if dia == date.max else inicio + timedelta(days=1)
        if slots_ocupados is None:
            from clinica.modulos.consultas.contratos import Consultas

            slots_ocupados = Consultas.listar_slots_ocupados_profissional(
                profissional_id, inicio, fim
            )
        repositorio = cls._repositorio()
        return AgendaProfissional(
            profissional_id=profissional_id,
            horarios_atendimento=repositorio.obter_horarios_atendimento(profissional_id),
            bloqueios=repositorio.listar_bloqueios(profissional_id, inicio, fim),
            slots_ocupados=slots_ocupados,
        )

    @classmethod
    def verificar_disponibilidade(
        cls,
        profissional_id: int,
        slot: Slot,
        slots_ocupados: Iterable[Slot] | None = None,
    ) -> None:
        """Valida se o profissional atende e está livre em ``slot``."""
        agenda = cls.carregar_agenda_do_dia(profissional_id, slot.inicio.date(), slots_ocupados)
        agenda.verificar_disponivel(slot)

    @classmethod
    def listar_slots_disponiveis(
        cls,
        profissional_id: int,
        dia: date,
        slots_ocupados: Iterable[Slot] | None = None,
        agora: datetime | None = None,
    ) -> list[Slot]:
        """Lista os slots disponíveis de um profissional em ``dia``."""
        agenda = cls.carregar_agenda_do_dia(profissional_id, dia, slots_ocupados)
        slots = agenda.slots_disponiveis(dia)
        if agora is not None:
            slots = [slot for slot in slots if slot.esta_no_futuro(agora)]
        return slots
