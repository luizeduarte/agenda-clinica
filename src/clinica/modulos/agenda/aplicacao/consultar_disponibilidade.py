"""Caso de uso ``ConsultarDisponibilidade`` (RF02)."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from clinica.compartilhado.erros import FiltroDeDisponibilidadeInvalidoError
from clinica.modulos.agenda.contratos import Agenda, Slot
from clinica.modulos.cadastros.contratos import Cadastros, Profissional


@dataclass(frozen=True)
class DisponibilidadeDoProfissional:
    profissional: Profissional
    slots: list[Slot]


class ConsultarDisponibilidade:
    _relogio: Callable[[], datetime] = datetime.now

    def __init__(self, relogio: Callable[[], datetime] | None = None) -> None:
        if relogio is not None:
            type(self)._relogio = relogio

    @classmethod
    def configurar_relogio(cls, relogio: Callable[[], datetime]) -> None:
        cls._relogio = relogio

    @classmethod
    def _validar_filtros(
        cls, profissional_id: int | None, especialidade: str | None
    ) -> str | None:
        if (profissional_id is None) == (especialidade is None):
            raise FiltroDeDisponibilidadeInvalidoError(
                "Informe um profissional ou uma especialidade para consultar."
            )
        if especialidade is not None:
            especialidade = especialidade.strip()
            if not especialidade:
                raise FiltroDeDisponibilidadeInvalidoError("Informe o nome da especialidade.")
        return especialidade

    @classmethod
    def _obter_profissionais(
        cls, profissional_id: int | None, especialidade: str | None
    ) -> list[Profissional]:
        if profissional_id is not None:
            return [Cadastros.obter_profissional(profissional_id)]
        assert especialidade is not None
        return Cadastros.listar_profissionais_por_especialidade(especialidade)

    @classmethod
    def executar(
        cls,
        dia: date,
        profissional_id: int | None = None,
        especialidade: str | None = None,
    ) -> list[DisponibilidadeDoProfissional]:
        """Lista os slots futuros livres em ``dia``, por profissional ou especialidade.

        Raises:
            FiltroDeDisponibilidadeInvalidoError: não informou exatamente um dos
                dois filtros, ou a especialidade está em branco.
            EntidadeNaoEncontradaError: ``profissional_id`` inexistente.
        """
        especialidade = cls._validar_filtros(profissional_id, especialidade)
        profissionais = cls._obter_profissionais(profissional_id, especialidade)
        agora = cls._relogio()
        return [
            DisponibilidadeDoProfissional(
                profissional,
                Agenda.listar_slots_disponiveis(profissional.id, dia, agora=agora),
            )
            for profissional in profissionais
        ]
