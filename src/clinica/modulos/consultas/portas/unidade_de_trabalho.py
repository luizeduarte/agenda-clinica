from abc import ABC, abstractmethod
from typing import Self

from clinica.modulos.agenda.portas.agenda_repositorio import AgendaRepositorio
from clinica.modulos.cadastros.portas.repositorios import (
    PacienteRepositorio,
    ProfissionalRepositorio,
)
from clinica.modulos.consultas.portas.consulta_repositorio import ConsultaRepositorio
from clinica.modulos.notificacoes.portas.notificacao_pendente_repositorio import (
    NotificacaoPendenteRepositorio,
)


class UnidadeDeTrabalho(ABC):
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

    def __enter__(self) -> Self:
        self.iniciar()
        return self

    def __exit__(self, tipo_exc, exc, tb) -> None:
        try:
            self.rollback()
        finally:
            self._fechar()

    @abstractmethod
    def iniciar(self) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    def _fechar(self) -> None:
        pass
