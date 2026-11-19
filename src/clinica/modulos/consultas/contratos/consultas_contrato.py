"""Contrato público do módulo ``consultas`` para comunicação entre módulos."""
from datetime import datetime

from clinica.modulos.agenda.contratos import Slot
from clinica.modulos.consultas.portas.consulta_repositorio import ConsultaRepositorio


class Consultas:
    """Fachada contratual do módulo ``consultas`` com ``@classmethod``s."""

    _consultas: ConsultaRepositorio | None = None

    @classmethod
    def configurar(cls, consultas: ConsultaRepositorio) -> None:
        cls._consultas = consultas

    @classmethod
    def _repositorio(cls) -> ConsultaRepositorio:
        if cls._consultas is None:
            raise RuntimeError("Consultas não configurado com ConsultaRepositorio.")
        return cls._consultas

    @classmethod
    def listar_slots_ocupados_profissional(
        cls, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Slot]:
        """Retorna os ``Slot``s ocupados por consultas ativas do profissional em ``[inicio, fim)``."""
        return [
            consulta.slot
            for consulta in cls._repositorio().listar_consultas_ativas_profissional(
                profissional_id, inicio, fim
            )
        ]
