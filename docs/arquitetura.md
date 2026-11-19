# Proposta Arquitetural - Agendamento de Consultas

## 1. Visão geral

O sistema adota uma arquitetura cliente-servidor, com backend desenvolvido como um monólito modular, organizado em camadas e utilizando princípios da arquitetura hexagonal.

Essa organização combina três decisões:

- **Monólito modular:** os módulos funcionam em uma única aplicação, com responsabilidades e dependências bem definidas.
- **Organização em camadas:** separa apresentação, aplicação, domínio e infraestrutura.
- **Portas e adaptadores:** isolam as regras de negócio das tecnologias externas, como banco de dados, notificações e autenticação.

A escolha busca equilibrar simplicidade de desenvolvimento, facilidade de manutenção, testabilidade e modificabilidade, sem introduzir a complexidade operacional de microsserviços.

## 2. Organização em módulos

O sistema divide-se em três camadas principais: **apresentação** (`api/`, responsável pela API REST/HTTP e comunicação com o cliente), **núcleo** (`modulos/`) e **infraestrutura** (`infraestrutura/`). O núcleo é particionado em módulos conforme suas responsabilidades de negócio, e cada módulo organiza-se internamente em `dominio/`, `aplicacao/` (quando concentra casos de uso), `portas/` (interfaces implementadas pela camada de infraestrutura) e `contratos/` (fachadas públicas que expõem suas operações para comunicação entre módulos).

| Módulo | Responsabilidades |
|---|---|
| `Agenda` | Gerenciar períodos de atendimento, bloqueios, disponibilidade dos profissionais e consulta de horários disponíveis (`ConsultarDisponibilidade`). |
| `Consultas` | Realizar agendamentos, cancelamentos, reagendamentos e confirmações, controlando conflitos de horário. |
| `Cadastros` | Manter as informações essenciais de pacientes, profissionais e especialidades. |
| `Notificacoes` | Registrar notificações pendentes, processar envios e controlar tentativas de reenvio. |
| `Autenticacao` | Integrar a identificação de profissionais, estagiários e pacientes ao serviço de autenticação da universidade. |

Os módulos pertencem à mesma aplicação e se comunicam por chamadas internas às fachadas de `contratos/`, sem a necessidade de requisições HTTP entre eles.

A comunicação entre módulos ocorre exclusivamente pelas fachadas em `<modulo>/contratos/` (`Agenda`, `Consultas`, `Cadastros`, `Notificacoes` e `Autenticacao`). No domínio, `AgendaProfissional` não depende de `Consulta` — recebe apenas os `Slot`s ocupados, evitando acoplamento cíclico entre as entidades de domínio. Na camada de aplicação e contratos, `Consultas` (`AgendarConsulta`) consome os contratos `Cadastros`, `Agenda` e `Notificacoes`, enquanto `Agenda` (`ConsultarDisponibilidade` e o contrato `Agenda`) consome `Cadastros` e `Consultas.listar_slots_ocupados_profissional`.

Cada módulo concentra responsabilidades relacionadas. As dependências entre os módulos do núcleo ocorrem por meio de seus contratos públicos (`contratos/`), mantendo os detalhes tecnológicos isolados na infraestrutura por trás das interfaces em `portas/`.

## 3. Organização em camadas

### 3.1. Apresentação

Responsável pela comunicação entre os clientes e o sistema.

A aplicação disponibilizará uma API REST, utilizando HTTP e JSON. Os controllers recebem as requisições, validam sua estrutura e encaminham as operações aos casos de uso.

Também convertem os resultados e erros em respostas HTTP adequadas.

As regras de negócio não são implementadas nos controllers.

### 3.2. Aplicação

Contém os casos de uso responsáveis por coordenar as operações do sistema:

- `ConfigurarHorarioAtendimento`
- `ConsultarDisponibilidade`
- `AgendarConsulta`
- `CancelarConsulta`
- `ReagendarConsulta`
- `ConfirmarConsulta`
- `RegistrarBloqueio`
- `ListarConsultas`

Os casos de uso coordenam as entidades e objetos do domínio e utilizam interfaces para acessar recursos externos.

Por exemplo, `AgendarConsulta` coordena a obtenção de dados e a verificação de disponibilidade pelos contratos `Cadastros` e `Agenda`, delega a validação temporal e de conflitos/limites do paciente a `Slot` e `AgendaPaciente`, instancia a `Consulta` e persiste a consulta e a notificação pendente (via contrato `Notificacoes`) atomicamente na transação aberta por `ConsultaRepositorio.transacao()`.

Os casos de uso não executam diretamente comandos SQL nem realizam chamadas específicas a serviços externos.

### 3.3. Domínio

Contém as entidades, objetos de valor e regras essenciais do sistema, detalhados em [`responsabilidades.md`](responsabilidades.md).

Entre os principais conceitos estão `Paciente`, `Profissional`, `Especialidade`, `Slot`, `AgendaProfissional`, `AgendaPaciente`, `Consulta`, `HorarioAtendimento`, `Bloqueio` e `PoliticaDeCancelamento`.

A `AgendaProfissional` concentra a avaliação da disponibilidade do profissional, enquanto `AgendaPaciente` concentra as regras de conflito e limite de reservas do paciente. `Slot` encapsula a validação de grade e sobreposição temporal, `PoliticaDeCancelamento` isola prazos por ator e especialidade e `Consulta` controla as transições válidas de seu estado.

As regras de domínio são independentes de HTTP, banco de dados e serviços de notificação.

### 3.4. Infraestrutura

Contém as implementações concretas necessárias para persistência e integração com serviços externos.

Inclui:

- Repositórios SQLite e o gerenciador de conexões e transações `ConexaoSQLite`.
- Adaptadores de notificação (`NotificadorFake`).
- Adaptador de autenticação universitária (`ServicoAutenticacaoFake`).
- Processamento das notificações pendentes.

Esses componentes implementam os contratos utilizados pela aplicação, mantendo os detalhes tecnológicos fora das regras de negócio.

## 4. Dependências e interfaces

### 4.1. Direção das dependências

As dependências do código devem preservar a independência do domínio.

A apresentação utiliza os casos de uso. Os casos de uso utilizam as entidades de domínio e dependem de interfaces para acessar recursos externos.

Os adaptadores da infraestrutura implementam essas interfaces.

Assim, a dependência do caso de uso em relação à persistência não é estabelecida com a implementação concreta do SQLite, mas com o contrato de repositório.

A configuração da aplicação é responsável por criar os componentes e associar cada interface à implementação correspondente.

### 4.2. Interfaces principais

| Interface | Responsabilidade |
|---|---|
| `ConsultaRepositorio` | Persistir e recuperar consultas por ID, por profissional ou por paciente (incluindo listagens de histórico e consultas ativas), além de expor o contexto transacional (`transacao()`) para operações atômicas, sem realizar validações de regra de negócio. |
| `AgendaRepositorio` | Persistir e recuperar períodos de atendimento e bloqueios das agendas. |
| `PacienteRepositorio` | Recuperar os dados essenciais de pacientes. |
| `ProfissionalRepositorio` | Recuperar os dados essenciais de profissionais e suas especialidades (incluindo filtro por especialidade). |
| `NotificacaoPendenteRepositorio` | Registrar, consultar e atualizar notificações pendentes de envio, além de expor o contexto transacional (`transacao()`) para gravações e atualizações atômicas. |
| `Notificador` | Estabelecer o contrato para envio de mensagens, independentemente do canal. |
| `ServicoAutenticacao` | Estabelecer o contrato de identificação de usuários e seus papéis pelo serviço de autenticação universitário. |

Essas interfaces permitem substituir implementações concretas sem alterar os casos de uso e as regras centrais do sistema.

## 5. Comunicação

### 5.1. Comunicação com os clientes

O sistema utilizará uma API REST sobre HTTP/JSON, permitindo a comunicação com interfaces web e outros clientes.

Entre os endpoints previstos estão:

| Método | Endpoint | Operação |
|---|---|---|
| `GET` | `/disponibilidade` | Consultar horários disponíveis (filtrando por profissional ou especialidade e data). |
| `PUT` | `/profissionais/{id}/horarios-atendimento` | Configurar ou atualizar períodos de atendimento do profissional. |
| `POST` | `/profissionais/{id}/bloqueios` | Registrar bloqueio datado na agenda. |
| `POST` | `/consultas` | Agendar consulta. |
| `GET` | `/consultas` | Listar consultas de um paciente ou da agenda de um profissional. |
| `GET` | `/consultas/{id}` | Consultar detalhes de uma consulta. |
| `PATCH` | `/consultas/{id}` | Reagendar uma consulta. |
| `DELETE` | `/consultas/{id}` | Cancelar uma consulta (alterando seu estado para `CANCELADA` e liberando o slot). |
| `POST` | `/consultas/{id}/confirmacao` | Confirmar uma consulta. |

A consulta de disponibilidade receberá a data desejada e o filtro (`profissional_id` ou `especialidade`) como parâmetros de consulta.

As respostas utilizarão códigos HTTP adequados, incluindo `201 Created` para agendamentos realizados, `200 OK` / `204 No Content` para cancelamentos e consultas, `400 Bad Request` para entradas inválidas, `403 Forbidden` para operações não autorizadas, `404 Not Found` para recursos inexistentes e `409 Conflict` para conflitos de agendamento.

A documentação detalhada das operações e de seus formatos de entrada e saída será mantida junto à implementação da API.

### 5.2. Comunicação interna

Os módulos expõem fachadas contratuais no pacote `<modulo>/contratos/` (`Agenda`, `Cadastros`, `Consultas`, `Notificacoes` e `Autenticacao`), configuradas na inicialização da aplicação com as implementações concretas de suas portas. Um módulo só importa de outro o que está definido em `contratos/`, garantindo fronteiras explícitas por chamadas em memória dentro da aplicação.

Não será utilizada comunicação HTTP entre os módulos, já que todos pertencem ao mesmo monólito.

Essa escolha evita latência de rede e infraestrutura adicional para operações internas.

### 5.3. Comunicação assíncrona

O envio de notificações será separado do processamento dos agendamentos.

O caso de uso registra a consulta e uma notificação pendente na mesma transação. O envio é executado posteriormente por um componente de processamento de notificações.

Esse mecanismo funciona como uma **fila de notificações**, implementada como uma tabela de pendências no próprio banco de dados (padrão *Transactional Outbox*), sem necessidade de um broker de mensagens externo. Cada pendência é uma mensagem na fila, com registro de envio, tentativas e possibilidade de reenvio. Por exigir atomicidade local, as implementações de `ConsultaRepositorio` e `NotificacaoPendenteRepositorio` precisam operar sobre o mesmo banco transacional. Em vez de fundir essas duas interfaces em um único repositório — o que violaria o SRP e acoplaria o módulo de consultas ao ciclo de vida das notificações —, as portas permanecem separadas e o compartilhamento da conexão e da transação é coordenado na infraestrutura por `ConexaoSQLite`, a partir do contexto transacional aberto em `ConsultaRepositorio.transacao()`.

## 6. Persistência e consistência

### 6.1. Banco de dados

O protótipo utilizará SQLite para armazenar pacientes, profissionais, agendas, consultas, bloqueios e notificações pendentes.

O acesso aos dados ocorrerá por repositórios, evitando dependências diretas entre os casos de uso e a tecnologia de persistência.

### 6.2. Controle de conflitos

As consultas possuem duração fixa de 30 minutos e utilizam uma grade alinhada a `:00` e `:30`, comum a todos os profissionais e pacientes (RN02). Os períodos de atendimento também devem respeitar essa grade.

Antes de realizar o agendamento, o domínio verifica:

1. A validade e o alinhamento do `Slot` solicitado.
2. Na `AgendaProfissional`: a existência de um `HorarioAtendimento` válido, a ausência de `Bloqueio` datado e a ausência de outra consulta ativa do profissional no horário.
3. Na `AgendaPaciente`: a ausência de outra consulta ativa do paciente no mesmo horário e o respeito ao limite máximo de consultas ativas permitidas.

Consideram-se ativas as consultas com estado `AGENDADA` ou `CONFIRMADA`.

Como os slots são discretizados e alinhados à grade (RN02), não ocorre sobreposição parcial entre horários, bastando impedir duplicidade de horário inicial entre consultas ativas. Para isso, o banco utilizará restrições de unicidade condicionadas às consultas ativas para os pares:

- `(profissional_id, inicio)`
- `(paciente_id, inicio)`

A verificação prévia de disponibilidade não é suficiente para garantir a consistência sob concorrência.

No SQLite, as operações de reserva utilizarão transações de escrita iniciadas antes das verificações de disponibilidade, com bloqueio de escrita antecipado (`BEGIN IMMEDIATE`). A validação dos bloqueios, dos limites do paciente e a gravação da consulta ocorrerão dentro da mesma transação.

As operações que alteram a disponibilidade, como criação de bloqueios e alteração de horários de atendimento, seguirão o mesmo controle transacional.

Caso a reserva não possa ser concluída, a transação será revertida e a operação retornará um erro, sem produzir agendamento parcial.

### 6.3. Reagendamento

O reagendamento será tratado como uma operação transacional.

A disponibilidade do novo horário será verificada antes da confirmação da mudança. A liberação do horário anterior e a ocupação do novo serão realizadas na mesma transação.

Se ocorrer conflito ou falha, a transação será revertida, preservando a consulta original.

### 6.4. Gerenciamento de conexão e transação (`ConexaoSQLite`)

Na infraestrutura SQLite, o componente `ConexaoSQLite` (`src/clinica/infraestrutura/persistencia/conexao.py`) gerencia o ciclo de vida das conexões e transações sem exigir uma interface separada de unidade de trabalho nos casos de uso:

- **Isolamento por thread:** a conexão ativa é armazenada em `threading.local()`, garantindo que requisições concorrentes no pool de threads da API utilizem conexões e transações independentes.
- **Transação explícita (`transacao()`):** o gerenciador de contexto `transacao()` — exposto pelas portas de escrita `ConsultaRepositorio.transacao()` e `NotificacaoPendenteRepositorio.transacao()` — abre uma conexão SQLite (com `isolation_level=None`, controle manual), inicia a transação com `BEGIN IMMEDIATE` para adquirir o bloqueio de escrita antes das leituras, confirma com `COMMIT` ao final do bloco ou reverte com `ROLLBACK` em caso de exceção, fechando a conexão ao sair.
- **Reaproveitamento transparente (`leitura()` e `escrita()`):** os repositórios SQLite acessam o banco internamente pelos gerenciadores `leitura()` e `escrita()` da instância compartilhada de `ConexaoSQLite`. Se já houver uma transação ativa na thread atual, ambos reutilizam essa mesma conexão e transação. Caso contrário, `leitura()` abre uma conexão temporária de somente leitura (`PRAGMA query_only = ON` com `BEGIN`) e a encerra após a operação, enquanto `escrita()` delega para `transacao()`.

Dessa forma, múltiplos repositórios instanciados com o mesmo `ConexaoSQLite` — como `SQLiteConsultaRepositorio` e `SQLiteNotificacaoPendenteRepositorio`, acionados por `AgendarConsulta` e pelo contrato `Notificacoes` — participam automaticamente da mesma transação física, garantindo commit ou rollback conjunto sem acoplar os módulos.

## 7. Notificações

### 7.1. Registro na fila de notificações

Após validar um agendamento, a aplicação coloca uma notificação pendente na fila de notificações, juntamente com a consulta.

Esse registro ocorrerá na mesma transação, garantindo que um agendamento persistido tenha sua notificação correspondente registrada.

A operação de agendamento não dependerá do sucesso do envio externo.

### 7.2. Processamento

Um componente separado será responsável por:

1. Consultar as notificações pendentes na fila.
2. Realizar o envio por meio da interface `Notificador`.
3. Registrar o resultado da tentativa.
4. Manter notificações com falha disponíveis para reenvio.

As notificações terão estados como `PENDENTE`, `ENVIADA` e `FALHA`, além de informações sobre tentativas de envio.

O processamento poderá ser executado por um processo separado da API, utilizando a mesma base de dados.

### 7.3. Substituição do canal

O contrato `Notificador` será implementado inicialmente por `NotificadorFake`.

A substituição por um canal real, como e-mail ou WhatsApp, exigirá a implementação de um novo adaptador e sua configuração na aplicação.

As regras de agendamento e o processamento das pendências permanecerão independentes do canal utilizado.

## 8. Autenticação e segurança

O sistema utilizará o serviço de autenticação universitário para identificar profissionais e estagiários.

A integração será isolada pela interface `ServicoAutenticacao` — exposta externamente pelo contrato `Autenticacao` — e implementada no protótipo por `ServicoAutenticacaoFake`.

As permissões serão verificadas conforme o papel do usuário (`Paciente` ou `Profissional / Estagiário`), separando autenticação de autorização.

Os dados pessoais utilizados no agendamento serão limitados às informações necessárias para o funcionamento do sistema, considerando as exigências da LGPD.

O adaptador simulado será utilizado apenas no ambiente de desenvolvimento e demonstração, não sendo um mecanismo de autenticação adequado para produção.

## 9. Organização do código

A implementação seguirá uma estrutura modular, com separação entre apresentação, aplicação, domínio e infraestrutura.

Uma organização de referência é:

```text
src/
  clinica/
    main.py
    api/
      controllers/
    modulos/
      agenda/
        dominio/
        aplicacao/
        portas/
        contratos/
      consultas/
        dominio/
        aplicacao/
        portas/
        contratos/
      cadastros/
        dominio/
        portas/
        contratos/
      notificacoes/
        dominio/
        aplicacao/
        portas/
        contratos/
      autenticacao/
        dominio/
        portas/
        contratos/
    infraestrutura/
      persistencia/
      notificacoes/
      autenticacao/

tests/
  api/
  dominio/
  aplicacao/
  integracao/
```

Os contratos públicos (`contratos/`) e interfaces (`portas/`) ficam próximos dos módulos aos quais pertencem. As implementações concretas serão mantidas na infraestrutura.

A composição das dependências e a configuração dos contratos serão realizadas na inicialização da aplicação.

Essa estrutura preserva a separação de responsabilidades e permite evoluir os módulos sem exigir sua implantação independente.

## 10. Relação com os ASRs

| ASR | Decisões arquiteturais relacionadas |
|---|---|
| **ASR-01 - Consistência** | Slots discretizados (`Slot`), validação de disponibilidade no domínio (`AgendaProfissional` e `AgendaPaciente`), restrições de unicidade e transações via transação do repositório (`ConexaoSQLite`). |
| **ASR-02 - Modificabilidade** | Interfaces `Notificador`, `ServicoAutenticacao` e repositórios, fachadas em `contratos/`, além de `PoliticaDeCancelamento` e `Slot` desacoplados, separando regras de negócio e infraestrutura. |
| **ASR-03 - Resiliência** | Registro transacional de notificações pendentes na mesma transação local (`ConexaoSQLite`) — mantendo repositórios e módulos segregados —, envio desacoplado e mecanismo de reenvio. |

A arquitetura introduz algumas abstrações adicionais, mas mantém a aplicação em um único processo principal, reduzindo os custos de desenvolvimento e operação.

As alternativas arquiteturais e os custos das decisões serão detalhados nos documentos de trade-offs e ADRs.