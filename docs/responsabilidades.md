# Modelo de Responsabilidades e Princípios de Design

## 1. Visão geral

O sistema de agendamento de consultas será organizado de modo a separar as regras de negócio da coordenação dos casos de uso e das tecnologias de infraestrutura.

A distribuição de responsabilidades busca garantir:

- **Alta coesão:** cada classe ou módulo concentra responsabilidades relacionadas.
- **Baixo acoplamento:** os componentes dependem o mínimo possível de detalhes de outros componentes.
- **Modificabilidade:** alterações em tecnologias externas não devem exigir mudanças nas regras de negócio.
- **Testabilidade:** regras e casos de uso podem ser testados independentemente do banco de dados ou de serviços externos.

Para isso, a arquitetura adotada consiste em um monólito modular, com separação entre domínio, aplicação, apresentação e infraestrutura, utilizando portas e adaptadores nas integrações.

## 2. Distribuição de responsabilidades

### 2.1. Camada de domínio

Contém os conceitos e as regras essenciais do sistema, independentemente das tecnologias utilizadas.

| Classe | Responsabilidade |
|---|---|
| `Paciente` | Representar o paciente e suas informações essenciais. |
| `Profissional` | Representar o profissional responsável pelos atendimentos e sua especialidade. |
| `Agenda` | Avaliar a disponibilidade de horários **do profissional**, considerando suas consultas, períodos de atendimento e bloqueios. |
| `Consulta` | Representar o agendamento, seus participantes, período e estado, controlando suas transições válidas. |
| `HorarioAtendimento` | Representar os períodos regulares de atendimento do profissional. |
| `Bloqueio` | Representar indisponibilidades da agenda, como férias e reuniões. |
| `Especialidade` | Representar a área de atendimento do profissional. |

A classe `Agenda` concentra as regras de disponibilidade **do profissional**, enquanto `Consulta` concentra as informações e comportamentos próprios de um agendamento. A disponibilidade do **paciente** é verificada pelo caso de uso `AgendarConsulta` por meio das consultas ativas recuperadas do repositório.

A verificação realizada por `Agenda` considera os dados disponibilizados a ela, sem consultar diretamente o banco de dados.

### 2.2. Camada de aplicação

Coordena os casos de uso e a interação entre o domínio e as interfaces necessárias.

| Caso de uso | Responsabilidade |
|---|---|
| `AgendarConsulta` | Coordenar a verificação da disponibilidade do profissional **e do paciente**, a criação da consulta, a persistência e o registro da notificação pendente. |
| `ConsultarDisponibilidade` | Obter as informações necessárias e apresentar os horários disponíveis de um profissional. |
| `CancelarConsulta` | Verificar a política de cancelamento e coordenar a alteração do estado da consulta. |
| `ReagendarConsulta` | Coordenar a alteração de horário, garantindo que a operação preserve a consulta original em caso de falha. |
| `ConfirmarConsulta` | Coordenar a confirmação de uma consulta previamente agendada. |

O protótipo priorizará `AgendarConsulta` e `ConsultarDisponibilidade`. Os demais casos de uso poderão ser documentados e implementados posteriormente.

Os casos de uso não devem conter SQL, detalhes de HTTP ou lógica específica de envio de e-mails.

### 2.3. Apresentação e infraestrutura

**Apresentação**

O `AgendamentoController` recebe requisições da API, valida os dados de entrada e encaminha as operações aos casos de uso correspondentes.

Também é responsável por transformar os resultados e erros da aplicação em respostas HTTP adequadas.

Não deve implementar regras de disponibilidade nem acessar diretamente o banco de dados.

**Portas e adaptadores**

| Componente | Responsabilidade |
|---|---|
| `ConsultaRepositorio` | Definir operações de acesso e persistência de consultas, incluindo a consulta de agendamentos ativos de um paciente em determinado horário. |
| `AgendaRepositorio` | Definir operações para obter agendas e seus dados de disponibilidade. |
| `NotificacaoPendenteRepositorio` | Definir operações para registrar e recuperar notificações pendentes. |
| `UnidadeDeTrabalho` | Coordenar a transação envolvendo as alterações de persistência que devem ocorrer atomicamente. |
| `Notificador` | Definir o contrato para envio de notificações, independentemente do canal utilizado. |
| `SQLiteConsultaRepositorio` | Implementar a persistência de consultas utilizando SQLite. |
| `NotificadorFake` | Simular o envio de notificações durante o desenvolvimento e os testes. |

As interfaces representam contratos utilizados pela aplicação. As implementações concretas pertencem à infraestrutura.

Um componente de processamento de notificações poderá consultar as pendências registradas e utilizar a interface `Notificador` para realizar os envios e tratar falhas.

A autenticação de profissionais e estagiários será realizada por meio do serviço da universidade, isolado pela interface ServicoAutenticacao. No protótipo, a integração será representada pelo adaptador AutenticacaoFake.

## 3. Aplicação dos princípios GRASP

### 3.1. Information Expert

**Aplicação: `Agenda`**

A responsabilidade de avaliar a disponibilidade **do profissional** é atribuída à `Agenda`, pois ela possui as informações e regras necessárias para considerar horários de atendimento, bloqueios e consultas desse profissional. Já a verificação de conflito do **paciente** é coordenada por `AgendarConsulta`, com informações obtidas pelo `ConsultaRepositorio`.

Isso evita que a lógica de disponibilidade seja espalhada entre controllers, repositórios e casos de uso.

Entretanto, a verificação de disponibilidade não substitui o controle transacional necessário para impedir reservas concorrentes.

### 3.2. Controller

**Aplicação: `AgendamentoController`**

O controller recebe as solicitações externas e delega sua execução aos casos de uso apropriados.

Por exemplo:

`AgendamentoController -> AgendarConsulta`

Assim, a camada de apresentação não concentra regras de negócio, facilitando a inclusão futura de outras interfaces.

### 3.3. Creator

**Aplicação: criação de `Consulta` no fluxo de agendamento**

O caso de uso `AgendarConsulta` reúne os dados necessários e coordena a criação da consulta, após a verificação das regras de disponibilidade.

A instanciação pode ocorrer por meio de um construtor ou método de fábrica da própria entidade `Consulta`, sem necessidade de criar uma classe adicional apenas para essa operação.

A responsabilidade pela criação é distinta da responsabilidade pela persistência.

### 3.4. Low Coupling e High Cohesion

As responsabilidades são separadas conforme seus objetivos:

- `Agenda` concentra regras de disponibilidade.
- `Consulta` concentra o estado e o comportamento do agendamento.
- Os casos de uso coordenam operações.
- Os repositórios implementam o acesso aos dados.
- Os adaptadores de notificação realizam a comunicação externa.

Essa divisão reduz dependências desnecessárias e facilita a manutenção dos componentes.

### 3.5. Protected Variations e Indirection

**Aplicação: `Notificador` e interfaces de repositório**

O sistema não deve depender diretamente de um serviço específico de e-mail ou de uma implementação concreta de persistência.

Utilizamos interfaces para intermediar essas dependências e proteger as regras de negócio de mudanças tecnológicas.

Por exemplo, substituir `NotificadorFake` por `EmailNotificador` ou `WhatsAppNotificador` não deve exigir alterações nas regras de agendamento, desde que as implementações respeitem o contrato.

### 3.6. Pure Fabrication

**Aplicação: repositórios e serviços de aplicação**

Componentes como repositórios não representam necessariamente entidades naturais do domínio da clínica.

Eles são introduzidos para organizar responsabilidades técnicas, evitar que entidades de domínio acumulem tarefas de infraestrutura e favorecer baixo acoplamento e alta coesão.

## 4. Aplicação dos princípios SOLID

| Princípio | Aplicação proposta |
|---|---|
| **SRP** | Separar regras de disponibilidade, coordenação dos casos de uso, persistência e notificações. |
| **OCP** | Permitir adicionar novos canais de notificação implementando o contrato existente, sem modificar o fluxo de agendamento. |
| **LSP** | Garantir que diferentes implementações de `Notificador` possam substituir umas às outras sem violar o comportamento esperado pelo contrato. |
| **ISP** | Utilizar interfaces com operações pertinentes às necessidades de seus clientes, evitando contratos excessivamente amplos. |
| **DIP** | Fazer com que os casos de uso dependam de abstrações, e não diretamente de implementações de banco de dados ou serviços externos. |

A aplicação desses princípios deverá ser proporcional às necessidades do sistema. Não serão criadas abstrações adicionais quando elas não representarem uma responsabilidade clara ou uma variação relevante.

## 5. Coesão e acoplamento

A organização proposta busca manter responsabilidades relacionadas dentro de um mesmo componente e reduzir dependências entre partes do sistema que possuem motivos diferentes para mudar.

### 5.1. Coesão

A separação entre as camadas favorece a coesão ao concentrar responsabilidades específicas:

- **Domínio:** entidades como `Agenda` e `Consulta` concentram regras relacionadas aos conceitos que representam, sem assumir responsabilidades de persistência ou comunicação externa.
- **Aplicação:** os casos de uso coordenam operações específicas, como agendar ou cancelar consultas, delegando as regras de negócio às entidades responsáveis.
- **Apresentação:** os controllers concentram o tratamento das requisições e respostas HTTP, sem implementar diretamente as regras de agendamento.
- **Infraestrutura:** repositórios e adaptadores concentram responsabilidades técnicas, como persistência e envio de notificações.

Assim, alterações em uma responsabilidade tendem a permanecer localizadas no componente correspondente, reduzindo a necessidade de modificar partes não relacionadas.

### 5.2. Acoplamento

O acoplamento é reduzido principalmente pela separação entre as regras de negócio e as implementações tecnológicas.

Por exemplo:

- `AgendarConsulta` depende de contratos de repositório, e não diretamente do SQLite.
- O envio de notificações utiliza a interface `Notificador`, sem depender de um serviço específico de e-mail ou WhatsApp.
- `Agenda` não precisa conhecer controllers, APIs HTTP ou detalhes de persistência.
- A substituição de adaptadores concretos pode ocorrer sem modificar os casos de uso, desde que os contratos sejam preservados.

Dessa forma, as dependências do código permanecem direcionadas às abstrações e às regras centrais do sistema.

### 5.3. Trade-offs

Essa separação introduz interfaces, classes e indireções adicionais, aumentando um pouco a complexidade estrutural.

Entretanto, consideramos esse custo justificável pela necessidade de modificar integrações externas, testar componentes isoladamente e preservar as regras de negócio diante de mudanças tecnológicas.

## 6. Fluxo de responsabilidades - Agendar consulta

O principal caso de uso seguirá, conceitualmente, as seguintes etapas:

1. O `AgendamentoController` recebe a solicitação.
2. O caso de uso `AgendarConsulta` obtém as informações necessárias por meio das interfaces de repositório.
3. A `Agenda` avalia a disponibilidade do profissional, enquanto `AgendarConsulta` verifica, via `ConsultaRepositorio`, se o paciente já possui uma consulta ativa no mesmo slot.
4. O caso de uso coordena a criação da `Consulta`.
5. A persistência garante atomicamente a reserva do horário e o registro de uma notificação pendente.
6. A aplicação retorna o resultado do agendamento.
7. Um processamento separado utiliza o `Notificador` para enviar a confirmação e tratar eventuais falhas.

A validação realizada pelo domínio não é suficiente, isoladamente, para garantir a consistência em situações de concorrência.

A infraestrutura de persistência deverá aplicar transações e mecanismos adequados para impedir consultas conflitantes, tanto para o profissional quanto para o paciente. Com slots fixos de 30 minutos alinhados, serão utilizadas restrições únicas condicionadas às consultas ativas por `(profissional_id, inicio)` e por `(paciente_id, inicio)`, além da validação dos períodos bloqueados durante a operação.

Em caso de conflito, o agendamento deverá falhar sem gerar uma consulta ou notificação pendente indevida.

## 7. Justificativas das decisões

A distribuição proposta busca atender principalmente aos três requisitos arquiteturalmente significativos selecionados:

**ASR-01 - Consistência:** a `Agenda` avalia disponibilidade do profissional; `AgendarConsulta` coordena a verificação de conflitos do paciente; e a persistência garante a atomicidade necessária para impedir agendamentos concorrentes conflitantes de ambos.

**ASR-02 - Modificabilidade:** interfaces de notificação e persistência permitem substituir implementações sem alterar as regras centrais do sistema.

**ASR-03 - Resiliência:** a separação entre o registro do agendamento e o envio posterior da notificação impede que uma falha externa invalide uma consulta já persistida.

## 8. Considerações finais

A distribuição de responsabilidades busca equilibrar separação de interesses, facilidade de evolução e simplicidade de implementação.

A proposta evita que entidades de domínio dependam diretamente de tecnologias externas e reduz o risco de concentração excessiva de responsabilidades em controllers ou serviços.

Este documento orientará a modelagem UML e a implementação do protótipo, devendo ser atualizado caso as decisões arquiteturais ou as regras de negócio sejam modificadas.
