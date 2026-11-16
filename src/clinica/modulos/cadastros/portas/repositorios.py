from typing import Protocol

from clinica.modulos.cadastros.dominio.cadastros import Paciente, Profissional


class PacienteRepositorio(Protocol):
    def obter_por_id(self, paciente_id: int) -> Paciente | None: ...


class ProfissionalRepositorio(Protocol):
    def obter_por_id(self, profissional_id: int) -> Profissional | None: ...

    def listar_por_especialidade(self, nome_especialidade: str) -> list[Profissional]: ...
