from typing import Protocol, Self

from clinica.modulos.agenda.portas.agenda_repositorio import AgendaRepositorio
from clinica.modulos.cadastros.portas.repositorios import (
    PacienteRepositorio,
    ProfissionalRepositorio,
)
from clinica.modulos.consultas.portas.consulta_repositorio import ConsultaRepositorio
from clinica.modulos.notificacoes.portas.notificacao_pendente_repositorio import (
    NotificacaoPendenteRepositorio,
)


class UnidadeDeTrabalho(Protocol):
    """Agrupa gravações para que valham todas juntas ou nenhuma (ADR-002, ADR-003).

    Ao agendar, o sistema grava duas coisas.
        with uow:                                    # começa o bloco
            uow.consultas.adicionar(consulta)        # 1. rascunho
            uow.notificacoes_pendentes.adicionar(aviso)   # 2. se falhar aqui,
            uow.commit()                             # 3. o 1 nunca chega a valer

    Sair do ``with`` sem ``commit()``, ou por exceção, desfaz tudo (rollback).
    """

    consultas: ConsultaRepositorio
    agendas: AgendaRepositorio
    pacientes: PacienteRepositorio
    profissionais: ProfissionalRepositorio
    notificacoes_pendentes: NotificacaoPendenteRepositorio

    def __enter__(self) -> Self: ...

    def __exit__(self, tipo_exc, exc, tb) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
