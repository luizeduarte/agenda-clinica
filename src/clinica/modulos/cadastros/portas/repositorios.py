from abc import ABC, abstractmethod

from clinica.modulos.cadastros.dominio.cadastros import Paciente, Profissional


class PacienteRepositorio(ABC):
    @abstractmethod
    def obter_por_id(self, paciente_id: int) -> Paciente | None: ...


class ProfissionalRepositorio(ABC):
    @abstractmethod
    def obter_por_id(self, profissional_id: int) -> Profissional | None: ...

    @abstractmethod
    def listar_por_especialidade(self, nome_especialidade: str) -> list[Profissional]: ...
