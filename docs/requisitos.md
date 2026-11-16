# Requisitos e ASRs - Agendamento de Consultas em Clínica Universitária

## 1. Contexto e escopo

O sistema apoia uma clínica universitária na organização das agendas de profissionais de saúde e estagiários, permitindo marcar, cancelar, reagendar e confirmar consultas. Deve considerar períodos de atendimento configurados por profissional, bloqueios datados, limites de reserva e conflitos de horário tanto do profissional quanto do paciente.

O **sistema proposto** contempla as funcionalidades especificadas abaixo. Já o **protótipo** implementará apenas uma fatia vertical, conforme a seção 7.

## 2. Atores

| Ator | Participação no sistema |
|---|---|
| **Paciente** | Consulta disponibilidade, agenda consultas, cancela, reagenda, confirma presença e consulta seu histórico de consultas. |
| **Profissional de saúde / Estagiário** | Mantém sua disponibilidade e bloqueios, consulta sua agenda de consultas, cancela atendimentos em caso de imprevisto e realiza os atendimentos previstos. |

## 3. Requisitos funcionais

| ID | Requisito | Ator(es) | Comportamento esperado |
|---|---|---|---|
| **RF01** | Manter agenda de disponibilidade | Profissional / Estagiário | Registrar ou atualizar os períodos recorrentes de atendimento de um profissional. |
| **RF02** | Consultar horários disponíveis | Paciente, Profissional / Estagiário | Listar slots disponíveis de um profissional específico ou de profissionais de uma especialidade, considerando horários de atendimento, bloqueios e consultas ativas. |
| **RF03** | Agendar consulta | Paciente | Registrar uma consulta para paciente e profissional em um horário válido e disponível, permanecendo inicialmente aguardando confirmação. |
| **RF04** | Cancelar consulta | Paciente, Profissional / Estagiário | Permitir o cancelamento da consulta quando a política de antecedência aplicável for respeitada, liberando o horário ocupado para novos agendamentos. |
| **RF05** | Reagendar consulta | Paciente | Mudar o horário de uma consulta preservando a reserva original caso o novo horário esteja indisponível ou a operação não possa ser concluída. |
| **RF06** | Impedir conflitos de horário | Sistema (acionado em RF03 e RF05) | Rejeitar agendamentos que coincidam com uma consulta ativa do profissional **ou do paciente**, bem como violações de limite de reservas. |
| **RF07** | Confirmar consulta | Paciente | Registrar a confirmação de comparecimento do paciente para uma consulta previamente agendada. |
| **RF08** | Enviar notificações | Sistema (disparado por RF03, RF04, RF05 e lembretes) | Gerar comunicações de agendamento, cancelamento e lembrete para os participantes. |
| **RF09** | Bloquear períodos da agenda | Profissional / Estagiário | Registrar indisponibilidades pontuais em datas específicas (como férias, feriados e reuniões), impedindo novos agendamentos nesses períodos. |
| **RF10** | Consultar agendamentos e histórico | Paciente, Profissional / Estagiário | Listar as consultas do histórico de um paciente ou os agendamentos previstos na agenda de um profissional, incluindo seus estados. |

### 3.1. Requisitos não funcionais (RNFs)

- **RNF01 - Isolamento de notificações (Resiliência):** o envio de notificações não deve bloquear nem desfazer o fluxo gerador da notificação; falhas no canal externo devem ser registradas para tentativa posterior.
- **RNF02 - Consistência e atomicidade:** operações de agendamento e reagendamento devem ocorrer de forma atômica e segura sob concorrência, impedindo reservas conflitantes ou perda da consulta original em caso de falha.
- **RNF03 - Autorização por papéis:** as operações devem respeitar as permissões associadas a cada papel (`Paciente` e `Profissional / Estagiário`), rejeitando solicitações não autorizadas sem alterar dados.

## 4. Regras de negócio

- **RN01 - Horários de atendimento:** cada profissional configura individualmente seus próprios períodos recorrentes de início e fim de atendimento; só podem ser oferecidos horários dentro desses períodos.
- **RN02 - Duração e alinhamento:** as consultas ocupam slots fixos de **30 minutos**, alinhados a uma **grade** que vale para todos os profissionais e pacientes: todo slot começa em `:00` ou `:30` (08:00–08:30, 08:30–09:00 etc.). Por isso, os períodos de atendimento configurados pelo profissional devem começar e terminar em `:00` ou `:30`, e períodos do mesmo profissional no mesmo dia não podem se sobrepor. Dois slots nunca se sobrepõem parcialmente: ou são o mesmo, ou são disjuntos.
- **RN03 - Estados e conflitos:** uma consulta pode assumir os estados `AGENDADA`, `CONFIRMADA`, `CANCELADA`, `REALIZADA` ou `FALTOU`. Consideram-se **ativas** as consultas `AGENDADA` e `CONFIRMADA`, que ocupam o horário; um profissional e um paciente não podem ter mais de uma consulta ativa no mesmo slot. Consultas `CANCELADA` liberam o horário.
- **RN04 - Bloqueios:** períodos bloqueados por exceções datadas tornam os slots correspondentes indisponíveis.
- **RN05 - Cancelamento:** quando solicitado pelo **paciente**, o cancelamento é permitido até **24 horas antes** do início da consulta para atendimentos gerais, ou até **72 horas antes** para atendimentos da especialidade **Odontologia (Dentista)**. Cancelamentos realizados pelo **profissional** não estão sujeitos a essa trava de antecedência.
- **RN06 - Reagendamento:** a alteração de horário deve verificar a disponibilidade do novo horário e garantir que a consulta original seja preservada intacta caso o novo agendamento não possa ser concluído.
- **RN07 - Confirmação:** criar um agendamento e receber a confirmação do paciente são operações distintas. Caso o paciente não confirme antecipadamente, a consulta permanece válida e reservando o horário no estado `AGENDADA` até que seja confirmada, cancelada ou encerrada como realizada/falta.
- **RN08 - Limite de agendamentos do paciente:** para evitar acaparamento da agenda (negação de serviço por reservas excessivas), um paciente pode manter no máximo **2 consultas ativas no mesmo dia** e no máximo **1 consulta ativa futura por especialidade**.

## 5. Restrições

### 5.1. Restrição legal - LGPD

O tratamento dos dados pessoais dos pacientes deve observar a Lei Geral de Proteção de Dados (LGPD). Isso motiva a **minimização dos dados armazenados** e o **controle de acesso** às informações pessoais e clínicas.

A definição de papéis e permissões descrita no **RNF03** é uma decisão de segurança adotada pelo sistema para atender a essa restrição legal, sem estar entre os três ASRs escolhidos para aprofundamento nesta entrega.

### 5.2. Integração com o sistema de autenticação universitário

O sistema deverá utilizar o serviço de autenticação da universidade para identificar profissionais e estagiários, evitando manter credenciais próprias para esses usuários.

A integração será realizada por meio da interface `ServicoAutenticacao`, isolando as regras de negócio da implementação concreta do serviço externo e favorecendo a modificabilidade.

No protótipo, a autenticação será simulada pelo adaptador `ServicoAutenticacaoFake`, preservando o contrato definido sem depender do acesso ao sistema real da universidade.

## 6. Requisitos arquiteturalmente significativos (ASRs)

### ASR-01 - Consistência dos agendamentos

- **Cenário:** duas solicitações concorrentes tentam ocupar o mesmo slot de um profissional, ou o mesmo paciente tenta reservar simultaneamente slots coincidentes com profissionais diferentes (ou violar seu limite de reservas ativas).
- **Resposta esperada:** no máximo uma reserva conflitante é efetivada; a outra solicitação recebe uma resposta de conflito, sem criar consulta ou notificação indevida.
- **Critério verificável:** testes com requisições concorrentes não devem produzir duas consultas `AGENDADA` ou `CONFIRMADA` para o mesmo `(profissional, início)` nem para o mesmo `(paciente, início)`.
- **Impacto arquitetural:** a `AgendaProfissional` avalia a disponibilidade do profissional e a `AgendaPaciente` avalia conflitos e limites do paciente no domínio, enquanto a persistência garante atomicidade e restrições únicas no banco. Como as consultas são discretizadas em slots fixos e alinhados (RN02), não há sobreposição parcial entre horários, tornando os pares `(profissional, início)` e `(paciente, início)` suficientes para detectar conflitos e impor restrições únicas parciais sob transações de escrita.

### ASR-02 - Modificabilidade das notificações

- **Cenário:** substituir o envio por e-mail por outro canal (por exemplo, SMS ou WhatsApp).
- **Resposta esperada:** as regras de domínio e o fluxo de agendamento permanecem inalterados; muda-se apenas o adaptador do canal e, quando necessário, a configuração de sua seleção.
- **Critério verificável:** substituir `NotificadorFake` por outro adaptador que implemente `Notificador` sem modificar `AgendaProfissional`, `AgendaPaciente`, `Consulta`, `AgendarConsulta` ou a lógica de processamento das notificações.
- **Impacto arquitetural:** contrato `Notificador`, inversão de dependência e composição dos adaptadores na infraestrutura.

### ASR-03 - Resiliência a falhas no envio de notificações

- **Cenário:** o serviço de notificação está indisponível no momento do agendamento.
- **Resposta esperada:** uma consulta validada é persistida e informada ao usuário independentemente da falha externa; a notificação permanece pendente para tentativa posterior.
- **Critério verificável:** ao simular falha no `Notificador`, a consulta já registrada permanece persistida e a notificação mantém estado rastreável para reenvio.
- **Impacto arquitetural:** registrar **consulta e notificação pendente na mesma transação** e enviar posteriormente por processamento separado. A proposta utiliza tabela de pendências no mesmo banco transacional, sem exigir um broker de mensagens externo.

> **Terminologia:** o estado `CONFIRMADA` significa confirmação do **paciente** (RF07). A resposta bem-sucedida de RF03 informa apenas que o **agendamento foi registrado** (`AGENDADA`). Ambos `AGENDADA` e `CONFIRMADA` ocupam o slot.

## 7. Recorte do protótipo

Para atender à fatia vertical solicitada no enunciado, a primeira implementação deve demonstrar:

1. **Consulta:** `ConsultarDisponibilidade` para um profissional (com suporte a especialidade).
2. **Mudança de estado:** `AgendarConsulta`, registrando a consulta como `AGENDADA`.
3. **Erro relevante:** tentativa de agendar slot já ocupado, bloqueado ou que viole conflito/limite do paciente, incluindo testes de concorrência.
4. **Persistência:** transação que salva a consulta e a notificação pendente, preservando as restrições de conflito.
5. **Dependência externa substituível:** `NotificadorFake` (com simulação de falha e reenvio) e `ServicoAutenticacaoFake` para simulação do contrato de autenticação.

Configuração de agenda, bloqueios, cancelamento, reagendamento, confirmação pelo paciente e listagem de histórico permanecem especificados para evolução incremental.

No recorte de RF08, o protótipo gera a notificação de agendamento. A notificação de cancelamento segue o mesmo mecanismo e será gerada quando `CancelarConsulta` for implementado. O lembrete (que exigiria um agendador de tempo) fica para a evolução incremental.
