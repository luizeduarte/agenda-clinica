from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
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

    # Repositórios que participam da transação. São abstratos para que uma
    # implementação que esqueça algum falhe já ao ser criada.
    @property
    @abstractmethod
    def consultas(self) -> ConsultaRepositorio: ...

    @property
    @abstractmethod
    def agendas(self) -> AgendaRepositorio: ...

    @property
    @abstractmethod
    def pacientes(self) -> PacienteRepositorio: ...

    @property
    @abstractmethod
    def profissionais(self) -> ProfissionalRepositorio: ...

    @property
    @abstractmethod
    def notificacoes_pendentes(self) -> NotificacaoPendenteRepositorio: ...

    def __enter__(self) -> Self:
        self.iniciar()
        return self

    def __exit__(self, tipo_exc, exc, tb) -> None:
        self._encerrar()

    @contextmanager
    def somente_leitura(self) -> Iterator[Self]:
        """Bloco só de leitura: ``with uow.somente_leitura() as uow:``.

        Não toma o bloqueio de escrita, então não atrasa as reservas (ADR-003),
        e recusa gravações. Usado por consultas como ``ConsultarDisponibilidade``.
        """
        self.iniciar(somente_leitura=True)
        try:
            yield self
        finally:
            self._encerrar()

    def _encerrar(self) -> None:
        # Desfaz o que não teve commit e libera a conexão, em qualquer saída do bloco.
        try:
            self.rollback()
        finally:
            self._fechar()

    @abstractmethod
    def iniciar(self, somente_leitura: bool = False) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    def _fechar(self) -> None:
        pass
