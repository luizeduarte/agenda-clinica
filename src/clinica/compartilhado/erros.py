"""Exceções do sistema.

Ficam fora de qualquer módulo porque são levantadas pelo domínio, pela
aplicação e pelas portas, e traduzidas para HTTP apenas na apresentação
(ver ``docs/arquitetura.md`` seção 5.1).
"""


class ErroDeDominio(Exception):
    """Base de todos os erros de regra de negócio."""


# --- Agendamento (RF03, RF06, RN02, RN03, RN04, RN08) -----------------------

class SlotInvalidoError(ErroDeDominio):
    """Slot sem 30 minutos ou fora do alinhamento do período (RN02)."""


class HorarioIndisponivelError(ErroDeDominio):
    """Fora do atendimento, bloqueado ou já ocupado pelo profissional (RN01, RN03, RN04)."""


class ConflitoDoPacienteError(ErroDeDominio):
    """O paciente já tem consulta ativa sobreposta ao horário (RN03)."""


class LimiteDoPacienteExcedidoError(ErroDeDominio):
    """Excede 2 consultas ativas no dia ou 1 futura por especialidade (RN08)."""


# --- Ciclo de vida da consulta (RF04, RF07) ---------------------------------

class TransicaoInvalidaError(ErroDeDominio):
    """Mudança de estado não permitida para a consulta."""


class CancelamentoForaDoPrazoError(ErroDeDominio):
    """Antecedência mínima de cancelamento não respeitada (RN05)."""


# --- Cadastros e acesso ------------------------------------------------------

class EntidadeNaoEncontradaError(ErroDeDominio):
    """Paciente, profissional ou consulta inexistente."""


class NaoAutenticadoError(ErroDeDominio):
    """Credencial não identificada pelo serviço de autenticação."""


class NaoAutorizadoError(ErroDeDominio):
    """O papel do usuário não permite a operação (RNF03)."""


# --- Infraestrutura vista pela aplicação ------------------------------------

class ConflitoDePersistenciaError(Exception):
    """Restrição única do banco violada na gravação (ASR-01).

    Levantada pelos repositórios quando duas reservas concorrentes disputam o
    mesmo ``(participante, inicio)``. O caso de uso a converte em
    ``HorarioIndisponivelError`` ou ``ConflitoDoPacienteError``.
    """


class FalhaNoEnvioError(Exception):
    """Falha do canal ao enviar uma notificação (ASR-03).

    Levantada por qualquer implementação de ``Notificador``; o processador de
    pendências registra a falha e mantém a notificação para reenvio.
    """
