"""``AgendaPaciente``: conflitos e limites do paciente (RN03, RN08).
"""
from collections.abc import Iterable
from datetime import datetime

from clinica.compartilhado.erros import ConflitoDoPacienteError, LimiteDoPacienteExcedidoError
from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.dominio.consulta import Consulta

MAX_ATIVAS_NO_DIA = 2
MAX_ATIVAS_FUTURAS_POR_ESPECIALIDADE = 1


class AgendaPaciente:
    def __init__(self, paciente_id: int, consultas: Iterable[Consulta]) -> None:
        self.paciente_id = paciente_id
        self.consultas_ativas = [c for c in consultas if c.esta_ativa]

    def verificar_pode_agendar(self, slot: Slot, especialidade_id: int, agora: datetime) -> None:
        """Levanta erro se o paciente não puder reservar ``slot`` com a especialidade dada."""
        if any(c.slot.sobrepoe(slot) for c in self.consultas_ativas):
            raise ConflitoDoPacienteError("O paciente já tem uma consulta ativa nesse horário.")

        no_mesmo_dia = [c for c in self.consultas_ativas if c.slot.inicio.date() == slot.inicio.date()]
        if len(no_mesmo_dia) >= MAX_ATIVAS_NO_DIA:
            raise LimiteDoPacienteExcedidoError(
                f"O paciente já tem {MAX_ATIVAS_NO_DIA} consultas ativas nesse dia."
            )

        futuras_na_especialidade = [
            c
            for c in self.consultas_ativas
            if c.especialidade_id == especialidade_id and c.slot.inicio > agora
        ]
        if len(futuras_na_especialidade) >= MAX_ATIVAS_FUTURAS_POR_ESPECIALIDADE:
            raise LimiteDoPacienteExcedidoError(
                "O paciente já tem uma consulta ativa futura nessa especialidade."
            )
