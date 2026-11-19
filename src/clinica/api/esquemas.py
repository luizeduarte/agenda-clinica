"""Formatos JSON da API (entrada e saída)"""
from datetime import datetime

from pydantic import BaseModel, Field, NaiveDatetime

from clinica.modulos.agenda.dominio.slot import Slot
from clinica.modulos.consultas.aplicacao.consultar_disponibilidade import (
    DisponibilidadeDoProfissional,
)
from clinica.modulos.consultas.dominio.consulta import Consulta


class ErroResposta(BaseModel):
    erro: str


class AgendarConsultaPedido(BaseModel):
    profissional_id: int
    inicio: NaiveDatetime = Field(
        description="Data futura e hora local de início em :00 ou :30, no formato AAAA-MM-DDTHH:MM:SS."
    )


class ConsultaResposta(BaseModel):
    id: int
    paciente_id: int
    profissional_id: int
    inicio: datetime
    fim: datetime
    status: str

    @classmethod
    def de(cls, consulta: Consulta) -> "ConsultaResposta":
        return cls(
            id=consulta.id,
            paciente_id=consulta.paciente_id,
            profissional_id=consulta.profissional_id,
            inicio=consulta.slot.inicio,
            fim=consulta.slot.fim,
            status=consulta.status.value,
        )


class SlotResposta(BaseModel):
    inicio: datetime
    fim: datetime

    @classmethod
    def de(cls, slot: Slot) -> "SlotResposta":
        return cls(inicio=slot.inicio, fim=slot.fim)


class ProfissionalResposta(BaseModel):
    id: int
    nome: str
    especialidade: str


class DisponibilidadeResposta(BaseModel):
    profissional: ProfissionalResposta
    slots: list[SlotResposta]

    @classmethod
    def de(cls, disponibilidade: DisponibilidadeDoProfissional) -> "DisponibilidadeResposta":
        p = disponibilidade.profissional
        return cls(
            profissional=ProfissionalResposta(
                id=p.id, nome=p.nome, especialidade=p.especialidade.nome
            ),
            slots=[SlotResposta.de(s) for s in disponibilidade.slots],
        )
