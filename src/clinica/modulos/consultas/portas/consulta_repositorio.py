from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from clinica.modulos.consultas.dominio.consulta import Consulta


class ConsultaRepositorio(ABC):
    """Persistência de consultas"""

    @contextmanager
    def transacao(self) -> Iterator[None]:
        """Delimita uma transação atômica de escrita (ASR-01, ASR-03)."""
        yield

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
