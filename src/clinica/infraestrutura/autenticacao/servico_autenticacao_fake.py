"""Simulação do serviço de autenticação da universidade (restrição 5.2).

Implementa a porta ``ServicoAutenticacao`` com um dicionário de tokens. Trocar
por um cliente real do serviço da universidade só exige outra implementação da
porta e a mudança na composição (``main.py``).
"""
from clinica.compartilhado.erros import NaoAutenticadoError
from clinica.modulos.autenticacao.portas.servico_autenticacao import Papel, Usuario

# Combina com os dados de exemplo da persistência (pacientes 7 e 8; profissionais 10 e 11).
TOKENS_DE_EXEMPLO: dict[str, Usuario] = {
    "token-ana": Usuario(7, Papel.PACIENTE),
    "token-bia": Usuario(8, Papel.PACIENTE),
    "token-dr-joao": Usuario(10, Papel.PROFISSIONAL),
    "token-dra-marta": Usuario(11, Papel.PROFISSIONAL),
}


class ServicoAutenticacaoFake:
    def __init__(self, usuarios: dict[str, Usuario] | None = None) -> None:
        self._usuarios = dict(TOKENS_DE_EXEMPLO if usuarios is None else usuarios)

    def identificar(self, credencial: str) -> Usuario:
        try:
            return self._usuarios[credencial]
        except KeyError:
            raise NaoAutenticadoError("Credencial inválida.") from None
