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
    """Transação única compartilhada pelos repositórios (ADR-002, ADR-003).

    Os repositórios continuam contratos separados (SRP); a implementação
    concreta faz todos usarem a mesma conexão/transação.

    Uso::

        with uow:                      # inicia a transação (BEGIN IMMEDIATE no SQLite)
            uow.consultas.adicionar(c)
            uow.notificacoes_pendentes.adicionar(p)
            uow.commit()

    Sair do ``with`` sem ``commit()`` ou por exceção faz rollback.
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
