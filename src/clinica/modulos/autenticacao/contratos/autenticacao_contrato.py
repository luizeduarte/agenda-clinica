"""Contrato público do módulo ``autenticacao`` para comunicação externa/entre módulos."""
from clinica.compartilhado.erros import NaoAutenticadoError
from clinica.modulos.autenticacao.dominio.usuario import Usuario
from clinica.modulos.autenticacao.portas.servico_autenticacao import ServicoAutenticacao


class Autenticacao:
    """Fachada contratual do módulo ``autenticacao`` com ``@classmethod``s."""

    _servico: ServicoAutenticacao | None = None

    @classmethod
    def configurar(cls, servico: ServicoAutenticacao) -> None:
        cls._servico = servico

    @classmethod
    def _porta(cls) -> ServicoAutenticacao:
        if cls._servico is None:
            raise RuntimeError("Autenticacao não configurada com ServicoAutenticacao.")
        return cls._servico

    @classmethod
    def identificar(cls, credencial: str) -> Usuario:
        """Identifica o usuário a partir da credencial (token)."""
        if not credencial.strip():
            raise NaoAutenticadoError("Credencial ausente.")
        return cls._porta().identificar(credencial.strip())

    @classmethod
    def identificar_por_cabecalho(cls, authorization: str | None) -> Usuario:
        """Extrai o token ``Bearer <token>`` do cabeçalho e identifica o usuário."""
        esquema, _, token = (authorization or "").partition(" ")
        if esquema.lower() != "bearer" or not token.strip():
            raise NaoAutenticadoError("Informe o cabeçalho 'Authorization: Bearer <token>'.")
        return cls.identificar(token.strip())
