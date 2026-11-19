from abc import ABC, abstractmethod
from datetime import datetime

from clinica.modulos.consultas.dominio.consulta import Consulta


class ConsultaRepositorio(ABC):
    """Persistência de consultas"""

    @abstractmethod
    def adicionar(self, consulta: Consulta) -> Consulta:
        """Grava a consulta e devolve uma cópia dela com o ``id`` gerado."""

    @abstractmethod
    def listar_consultas_ativas_profissional(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Consulta]:
        """Consultas ``AGENDADA``/``CONFIRMADA`` que intersectam ``[inicio, fim)``."""

    @abstractmethod
    def listar_consultas_ativas_paciente(self, paciente_id: int) -> list[Consulta]:
        """Todas as consultas ativas do paciente (base para ``AgendaPaciente``, RN03/RN08)."""
