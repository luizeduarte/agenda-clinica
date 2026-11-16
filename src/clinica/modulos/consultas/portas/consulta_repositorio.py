from datetime import datetime
from typing import Protocol

from clinica.modulos.consultas.dominio.consulta import Consulta


class ConsultaRepositorio(Protocol):
    """Persistência de consultas. Não aplica regras de negócio."""

    def adicionar(self, consulta: Consulta) -> Consulta:
        """Grava a consulta e devolve-a com ``id``.

        Raises:
            ConflitoDePersistenciaError: restrição única de consulta ativa
                violada por profissional ou paciente (ASR-01).
        """
        ...

    def atualizar(self, consulta: Consulta) -> None:
        """Persiste mudança de estado/horário de uma consulta existente."""
        ...

    def obter_por_id(self, consulta_id: int) -> Consulta | None: ...

    def listar_ativas_do_profissional(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Consulta]:
        """Consultas ``AGENDADA``/``CONFIRMADA`` que intersectam ``[inicio, fim)``."""
        ...

    def listar_ativas_do_paciente(self, paciente_id: int) -> list[Consulta]:
        """Todas as consultas ativas do paciente (base para ``AgendaPaciente``, RN03/RN08)."""
        ...

    def listar_por_paciente(self, paciente_id: int) -> list[Consulta]:
        """Histórico completo, em qualquer estado (RF10)."""
        ...

    def listar_por_profissional(
        self, profissional_id: int, inicio: datetime, fim: datetime
    ) -> list[Consulta]:
        """Agenda do profissional no período, em qualquer estado (RF10)."""
        ...
