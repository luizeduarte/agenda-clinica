from datetime import datetime
from typing import Protocol

from clinica.modulos.consultas.dominio.consulta import Consulta


class ConsultaRepositorio(Protocol):
    """Persistência de consultas"""

    def adicionar(self, consulta: Consulta) -> Consulta:
        """Grava a consulta e devolve-a com ``id``."""
        ...

    def listar_consultas_ativas_profissional(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Consulta]:
        """Consultas ``AGENDADA``/``CONFIRMADA`` que intersectam ``[inicio, fim)``."""
        ...

    def listar_consultas_ativas_paciente(self, paciente_id: int) -> list[Consulta]:
        """Todas as consultas ativas do paciente (base para ``AgendaPaciente``, RN03/RN08)."""
        ...
