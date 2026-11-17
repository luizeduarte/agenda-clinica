"""Caso de uso ``ConsultarDisponibilidade`` (RF02)."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from clinica.compartilhado.erros import EntidadeNaoEncontradaError
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
    def __init__(self, uow_factory: Callable[[], UnidadeDeTrabalho]) -> None:
        self._uow_factory = uow_factory

    def executar(
        self,
        dia: date,
        profissional_id: int | None = None,
        especialidade: str | None = None,
    ) -> list[DisponibilidadeDoProfissional]:
        """Lista os slots livres em ``dia``, de um profissional ou de uma especialidade.

        Raises:
            ValueError: não informou exatamente um dos dois filtros.
            EntidadeNaoEncontradaError: ``profissional_id`` inexistente.
        """
        if (profissional_id is None) == (especialidade is None):
            raise ValueError("Informe profissional_id ou especialidade, mas não ambos.")

        with self._uow_factory() as uow:
            if profissional_id is not None:
                profissional = uow.profissionais.obter_por_id(profissional_id)
                if profissional is None:
                    raise EntidadeNaoEncontradaError("Profissional não encontrado.")
                profissionais = [profissional]
            else:
                profissionais = uow.profissionais.listar_por_especialidade(especialidade)

            return [
                DisponibilidadeDoProfissional(
                    p, carregar_agenda_do_profissional(uow, p.id, dia).slots_disponiveis(dia)
                )
                for p in profissionais
            ]
