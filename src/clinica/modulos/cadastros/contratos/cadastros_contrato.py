"""Contrato público do módulo ``cadastros`` para comunicação entre módulos."""
from clinica.compartilhado.erros import EntidadeNaoEncontradaError
from clinica.modulos.cadastros.dominio.cadastros import Paciente, Profissional
from clinica.modulos.cadastros.portas.repositorios import (
    PacienteRepositorio,
    ProfissionalRepositorio,
)


class Cadastros:
    """Fachada contratual do módulo ``cadastros`` com ``@classmethod``s."""

    _pacientes: PacienteRepositorio | None = None
    _profissionais: ProfissionalRepositorio | None = None

    @classmethod
    def configurar(
        cls,
        pacientes: PacienteRepositorio,
        profissionais: ProfissionalRepositorio,
    ) -> None:
        cls._pacientes = pacientes
        cls._profissionais = profissionais

    @classmethod
    def _repo_pacientes(cls) -> PacienteRepositorio:
        if cls._pacientes is None:
            raise RuntimeError("Cadastros não configurado com PacienteRepositorio.")
        return cls._pacientes

    @classmethod
    def _repo_profissionais(cls) -> ProfissionalRepositorio:
        if cls._profissionais is None:
            raise RuntimeError("Cadastros não configurado com ProfissionalRepositorio.")
        return cls._profissionais

    @classmethod
    def obter_paciente(cls, paciente_id: int) -> Paciente:
        """Retorna o paciente ou levanta ``EntidadeNaoEncontradaError``."""
        paciente = cls._repo_pacientes().obter_por_id(paciente_id)
        if paciente is None:
            raise EntidadeNaoEncontradaError("Paciente não encontrado.")
        return paciente

    @classmethod
    def obter_profissional(cls, profissional_id: int) -> Profissional:
        """Retorna o profissional ou levanta ``EntidadeNaoEncontradaError``."""
        profissional = cls._repo_profissionais().obter_por_id(profissional_id)
        if profissional is None:
            raise EntidadeNaoEncontradaError("Profissional não encontrado.")
        return profissional

    @classmethod
    def listar_profissionais_por_especialidade(
        cls, nome_especialidade: str
    ) -> list[Profissional]:
        """Lista os profissionais cadastrados na especialidade informada."""
        return cls._repo_profissionais().listar_por_especialidade(nome_especialidade)
