# Requisitos e ASRs - Agendamento de Consultas em Clínica Universitária

## 1. Contexto e escopo

O sistema apoia uma clínica universitária na organização das agendas de profissionais de saúde e estagiários, permitindo marcar, cancelar, reagendar e confirmar consultas. Deve considerar períodos de atendimento, bloqueios e conflitos de horário tanto do profissional quanto do paciente.

O **sistema proposto** contempla as funcionalidades especificadas abaixo. Já o **protótipo** implementará apenas uma fatia vertical, conforme a seção 7.

## 2. Atores

| Ator | Participação no sistema |
|---|---|
| **Paciente** | Consulta disponibilidade, solicita agendamentos, cancela, reagenda, confirma e consulta seu histórico. |
| **Profissional de saúde / Estagiário** | Mantém sua disponibilidade e realiza atendimentos previstos na agenda. |
| **Recepcionista / Secretária** | Apoia o gerenciamento de agendas e o agendamento de consultas, conforme as permissões definidas para seu papel. |

## 3. Requisitos funcionais

| ID | Requisito | Comportamento esperado |
|---|---|---|
| **RF01** | Manter agenda de disponibilidade | Registrar ou atualizar os períodos de atendimento de um profissional. |
| **RF02** | Consultar horários disponíveis | Listar slots disponíveis de um profissional ou de profissionais de uma especialidade, considerando horários de atendimento, bloqueios e consultas ativas. |
| **RF03** | Agendar consulta | Registrar uma consulta para paciente e profissional em um slot válido e disponível. A consulta inicia como `AGENDADA`. |
| **RF04** | Cancelar consulta | Permitir cancelamento quando a política de antecedência for respeitada; liberar o slot ao passar a `CANCELADA`. |
| **RF05** | Reagendar consulta | Mudar o horário de uma consulta sem perder a reserva original caso o novo horário esteja indisponível ou a operação falhe. |
| **RF06** | Impedir conflitos de horário | Rejeitar agendamentos que coincidam com uma consulta ativa do profissional **ou do paciente**. |
| **RF07** | Confirmar consulta | Registrar a confirmação do paciente, alterando uma consulta `AGENDADA` para `CONFIRMADA`. |
| **RF08** | Enviar notificações | Gerar comunicações de agendamento, cancelamento e lembrete, sem tornar o agendamento dependente da disponibilidade do canal externo. |
| **RF09** | Bloquear períodos da agenda | Registrar indisponibilidades como férias, feriados e reuniões, impedindo novos agendamentos nesses períodos. |
| **RF10** | Consultar histórico do paciente | Listar as consultas de um paciente, incluindo seus estados. |

## 4. Regras de negócio

- **RN01 - Horários de atendimento:** só podem ser oferecidos slots dentro dos períodos de atendimento do profissional.
- **RN02 - Duração e alinhamento:** as consultas ocupam slots fixos de **30 minutos**, alinhados à grade da agenda (por exemplo, 10h00-10h30 e 10h30-11h00).
- **RN03 - Conflitos:** um profissional e um paciente não podem ter mais de uma consulta **ativa** no mesmo slot. Para a reserva, consideram-se ativas as consultas `AGENDADA` e `CONFIRMADA`; `CANCELADA` não ocupa o horário.
- **RN04 - Bloqueios:** períodos bloqueados tornam os slots correspondentes indisponíveis.
- **RN05 - Cancelamento:** o cancelamento é permitido até **24 horas antes** do início da consulta.
- **RN06 - Reagendamento:** a operação deve verificar o novo slot e realizar a mudança de forma transacional; se houver conflito ou falha, a consulta original permanece válida.
- **RN07 - Confirmação:** criar um agendamento e receber a confirmação do paciente são operações distintas; uma consulta pode ocupar o horário mesmo estando apenas `AGENDADA`.

## 5. Restrições e requisitos associados

### 5.1. Restrição legal - LGPD

O tratamento dos dados pessoais dos pacientes deve observar a Lei Geral de Proteção de Dados (LGPD). Isso motiva **minimização dos dados armazenados** e **controle de acesso** às informações pessoais.

A definição de papéis e permissões é uma necessidade de segurança associada a essa restrição.

### 5.2. Integração com o sistema de autenticação universitário

O sistema deverá utilizar o serviço de autenticação da universidade para identificar profissionais e estagiários, evitando a necessidade de manter credenciais próprias para esses usuários.

A integração será realizada por meio da interface `ServicoAutenticacao`, isolando as regras de negócio da implementação concreta do serviço externo e favorecendo a modificabilidade.

No protótipo, a autenticação será simulada por um adaptador `AutenticacaoFake`, preservando o contrato definido sem depender do acesso ao sistema real da universidade.

### 5.3. Requisito de segurança

As operações devem respeitar as permissões de cada papel. Solicitações não autorizadas devem ser rejeitadas sem alterar dados. Esse requisito é importante, mas **não está entre os três ASRs escolhidos para aprofundamento** nesta entrega.

## 6. Requisitos arquiteturalmente significativos (ASRs)

### ASR-01 - Consistência dos agendamentos

- **Cenário:** duas solicitações concorrentes tentam ocupar o mesmo slot de um profissional, ou o mesmo paciente tenta reservar simultaneamente slots coincidentes com profissionais diferentes.
- **Resposta esperada:** no máximo uma reserva conflitante é efetivada; a outra solicitação recebe uma resposta de conflito, sem criar consulta ou notificação indevida.
- **Critério verificável:** testes com requisições concorrentes não devem produzir duas consultas `AGENDADA` ou `CONFIRMADA` para o mesmo `(profissional, início)` nem para o mesmo `(paciente, início)`.
- **Impacto arquitetural:** a `Agenda` avalia a disponibilidade do profissional; `AgendarConsulta` coordena também a checagem das consultas do paciente; a persistência precisa garantir atomicidade e restrições para ambos os casos. Com slots fixos e alinhados, podem ser usadas restrições únicas condicionadas às consultas ativas, junto a transações e validação dos bloqueios.

### ASR-02 - Modificabilidade das notificações

- **Cenário:** substituir o envio por e-mail por outro canal (por exemplo, SMS ou WhatsApp).
- **Resposta esperada:** as regras de domínio e o fluxo de agendamento permanecem inalterados; muda-se o adaptador do canal e, quando necessário, a configuração de sua seleção.
- **Critério verificável:** substituir NotificadorFake por outro adaptador que implemente Notificador, sem modificar Agenda, Consulta, AgendarConsulta ou a lógica de processamento das notificações.
- **Impacto arquitetural:** contrato `Notificador`, inversão de dependência e composição dos adaptadores na infraestrutura.

### ASR-03 - Resiliência a falhas no envio de notificações

- **Cenário:** o serviço de notificação está indisponível no momento do agendamento.
- **Resposta esperada:** uma consulta validada pode ser persistida e informada ao usuário independentemente da falha externa; a notificação permanece pendente para tentativa posterior.
- **Critério verificável:** ao simular falha no `Notificador`, a consulta já registrada permanece persistida e a notificação mantém estado rastreável para reenvio.
- **Impacto arquitetural:** registrar **consulta e notificação pendente na mesma transação** e enviar posteriormente por processamento separado. A proposta utiliza tabela de pendências, sem exigir um broker de mensagens.

> **Terminologia:** o estado `CONFIRMADA` significa confirmação do **paciente** (RF07). A resposta bem-sucedida de RF03 confirma apenas que o **agendamento foi registrado**. Ambos `AGENDADA` e `CONFIRMADA` ocupam o slot.

## 7. Recorte do protótipo

Para atender à fatia vertical solicitada no enunciado, a primeira implementação deve demonstrar:

1. **Consulta:** `ConsultarDisponibilidade` para um profissional.
2. **Mudança de estado:** `AgendarConsulta`, registrando a consulta como `AGENDADA`.
3. **Erro relevante:** tentativa de agendar slot já ocupado ou bloqueado; incluir conflito de paciente e concorrência nos testes.
4. **Persistência:** transação que salva a consulta e a notificação pendente, preservando as restrições de conflito.
5. **Dependência externa substituível:** `NotificadorFake`, com possibilidade de simular falha e reenvio.

Cancelamento, reagendamento, confirmação pelo paciente, histórico e autenticação universitária podem permanecer especificados para evolução futura.
