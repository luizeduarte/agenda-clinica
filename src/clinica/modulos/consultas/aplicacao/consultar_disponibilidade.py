"""Caso de uso ``ConsultarDisponibilidade`` (RF02)."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from clinica.compartilhado.erros import (
    EntidadeNaoEncontradaError,
    FiltroDeDisponibilidadeInvalidoError,
)
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.cadastros.dominio.cadastros import Profissional
from clinica.modulos.consultas.aplicacao.agenda_do_profissional import (
    carregar_agenda_do_profissional,
)
from clinica.modulos.consultas.portas.unidade_de_trabalho import UnidadeDeTrabalho


@dataclass(frozen=True)
class DisponibilidadeDoProfissional:
    profissional: Profissional
    slots: list[Slot]


class ConsultarDisponibilidade:
    def __init__(
        self, uow: UnidadeDeTrabalho, relogio: Callable[[], datetime] = datetime.now
    ) -> None:
        self._uow = uow
        self._relogio = relogio

    def executar(
        self,
        dia: date,
        profissional_id: int | None = None,
        especialidade: str | None = None,
    ) -> list[DisponibilidadeDoProfissional]:
        """Lista os slots futuros livres em ``dia``, por profissional ou especialidade.

        Raises:
            ValueError: não informou exatamente um dos dois filtros.
            EntidadeNaoEncontradaError: ``profissional_id`` inexistente.
        """
        if (profissional_id is None) == (especialidade is None):
            raise FiltroDeDisponibilidadeInvalidoError(
                "Informe um profissional ou uma especialidade para consultar."
            )

        with self._uow.leitura() as uow:
            if profissional_id is not None:
                profissional = uow.profissionais.obter_por_id(profissional_id)
                if profissional is None:
                    raise EntidadeNaoEncontradaError("Profissional não encontrado.")
                profissionais = [profissional]
            else:
                especialidade = especialidade.strip()
                if not especialidade:
                    raise FiltroDeDisponibilidadeInvalidoError("Informe o nome da especialidade.")
                profissionais = uow.profissionais.listar_por_especialidade(especialidade)

            agora = self._relogio()
            resultado = []
            for profissional in profissionais:
                agenda = carregar_agenda_do_profissional(uow, profissional.id, dia)
                slots = [slot for slot in agenda.slots_disponiveis(dia) if slot.esta_no_futuro(agora)]
                resultado.append(DisponibilidadeDoProfissional(profissional, slots))
            return resultado
