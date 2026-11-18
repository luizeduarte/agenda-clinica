# Agenda Clínica

Projeto desenvolvido como trabalho final para a disciplina CI1163 - Design de
Software, com o tema 02: Agendamento de consultas em clínica universitária —
Sistema para organizar agendas de profissionais, permitir marcação, cancelamento
e reagendamento de consultas, além de controlar conflitos de horários e
confirmações.

Integrantes:
Arthur dos Santos Lima Gropp - GRR20211769
Gabriel Lisboa Conegero      - GRR20221255
Luize Cunha Duarte           - GRR20221232
Vinicius Evair da Silva      - GRR20221251

## Escopo

Os [requisitos](docs/requisitos.md) contemplam:

- Configuração de horários de atendimento e bloqueios nas agendas.
- Consulta de disponibilidade por profissional ou especialidade.
- Agendamento, cancelamento, reagendamento e confirmação de consultas.
- Controle de conflitos e limites de reservas por paciente.
- Notificações e consulta de agendamentos e histórico.

A fatia vertical escolhida para a implementação foi a consulta de disponibilidade
e o agendamento, incluindo a rejeição de reservas conflitantes, a persistência
da consulta e o registro da notificação para envio posterior.

## Arquitetura

A arquitetura proposta é cliente-servidor, com uma API REST sobre HTTP/JSON e um
backend organizado como monólito modular.

A persistência utiliza SQLite. A consulta e sua notificação pendente são gravadas
na mesma transação; o envio ocorre depois, sem condicionar o agendamento à
disponibilidade do canal externo.

Os três ASRs aprofundados são a consistência dos agendamentos, a modificabilidade
das notificações e a resiliência a falhas no envio. As justificativas e os custos
dessas escolhas estão na [proposta arquitetural](docs/arquitetura.md), nos
[trade-offs](docs/tradeoffs.md) e nos [ADRs](docs/adr/).

## Protótipo
TBD

## Diagramas
TBD

## Documentação

- [Enunciado do trabalho](trabalho-design.pdf)
- [Requisitos, regras de negócio, restrições e ASRs](docs/requisitos.md)
- [Modelo de domínio e responsabilidades](docs/responsabilidades.md)
- [Proposta arquitetural e análise de evolução](docs/arquitetura.md)
- [Alternativas e trade-offs](docs/tradeoffs.md)
- Registros de decisões arquiteturais:
  - [ADR-001: monólito modular em vez de microsserviços](docs/adr/ADR-001.md)
  - [ADR-002: isolamento do notificador e estratégia de falha](docs/adr/ADR-002.md)
  - [ADR-003: persistência e garantia de conflito de horário](docs/adr/ADR-003.md)
  - [ADR-004: domínio isolado de infraestrutura](docs/adr/ADR-004.md)
- [Diagramas UML](docs/diagramas/)
