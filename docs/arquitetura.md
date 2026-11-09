# Proposta Arquitetural - Agendamento de Consultas

## 1. Visão geral

O sistema adota uma arquitetura cliente-servidor, com backend desenvolvido como um monólito modular, organizado em camadas e utilizando princípios da arquitetura hexagonal.

Essa organização combina três decisões:

- **Monólito modular:** os módulos funcionam em uma única aplicação, com responsabilidades e dependências bem definidas.
- **Organização em camadas:** separa apresentação, aplicação, domínio e infraestrutura.
- **Portas e adaptadores:** isolam as regras de negócio das tecnologias externas, como banco de dados, notificações e autenticação.

A escolha busca equilibrar simplicidade de desenvolvimento, facilidade de manutenção, testabilidade e modificabilidade, sem introduzir a complexidade operacional de microsserviços.

## 2. Organização em módulos

O sistema será dividido em módulos conforme suas responsabilidades de negócio.

| Módulo | Responsabilidades |
|---|---|
| `Agenda` | Gerenciar períodos de atendimento, bloqueios e disponibilidade dos profissionais. |
| `Consultas` | Realizar agendamentos, cancelamentos, reagendamentos e confirmações, controlando conflitos de horário. |
| `Cadastros` | Manter as informações essenciais de pacientes, profissionais e especialidades. |
| `Notificacoes` | Registrar notificações pendentes, processar envios e controlar tentativas de reenvio. |
| `Autenticacao` | Integrar a identificação de profissionais e estagiários ao serviço de autenticação da universidade. |

Os módulos pertencem à mesma aplicação e se comunicam por chamadas internas, sem a necessidade de requisições HTTP entre eles.

Cada módulo concentra responsabilidades relacionadas. As dependências entre módulos são estabelecidas por contratos e componentes de aplicação, evitando acesso direto aos detalhes internos de outros módulos.

## 3. Organização em camadas

### 3.1. Apresentação

Responsável pela comunicação entre os clientes e o sistema.

A aplicação disponibilizará uma API REST, utilizando HTTP e JSON. Os controllers recebem as requisições, validam sua estrutura e encaminham as operações aos casos de uso.

Também convertem os resultados e erros em respostas HTTP adequadas.

As regras de negócio não são implementadas nos controllers.

### 3.2. Aplicação

Contém os casos de uso responsáveis por coordenar as operações do sistema.

Entre os principais estão:

- `AgendarConsulta`
- `ConsultarDisponibilidade`
- `CancelarConsulta`
- `ReagendarConsulta`
- `ConfirmarConsulta`

Os casos de uso coordenam as entidades do domínio e utilizam interfaces para acessar recursos externos.

Por exemplo, `AgendarConsulta` coordena a verificação da disponibilidade do profissional e do paciente, a criação da consulta e sua persistência.

Os casos de uso não executam diretamente comandos SQL nem realizam chamadas específicas a serviços externos.

### 3.3. Domínio

Contém as entidades e regras essenciais do sistema, descritas em `modelo_dominio.md`.

Entre os principais conceitos estão `Paciente`, `Profissional`, `Agenda`, `Consulta`, `HorarioAtendimento`, `Bloqueio` e `Especialidade`.

A `Agenda` concentra a avaliação da disponibilidade do profissional. A `Consulta` representa o agendamento e controla as transições válidas de seu estado.

As regras de domínio são independentes de HTTP, banco de dados e serviços de notificação.

### 3.4. Infraestrutura

Contém as implementações concretas necessárias para persistência e integração com serviços externos.

Inclui:

- Repositórios que utilizam SQLite.
- Adaptadores de notificação.
- Adaptador de autenticação universitária.
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
| `ConsultaRepositorio` | Consultar, registrar e atualizar consultas, incluindo a verificação dos horários ocupados pelo paciente. |
| `AgendaRepositorio` | Recuperar agendas, períodos de atendimento e bloqueios. |
| `NotificacaoPendenteRepositorio` | Registrar e recuperar notificações que precisam ser enviadas. |
| `UnidadeDeTrabalho` | Coordenar as operações de persistência que devem ocorrer na mesma transação. |
| `Notificador` | Estabelecer o contrato para envio de mensagens, independentemente do canal. |
| `ServicoAutenticacao` | Estabelecer o contrato de identificação de usuários pelo serviço de autenticação universitário. |

Essas interfaces permitem substituir implementações concretas sem alterar os casos de uso e as regras centrais do sistema.

## 5. Comunicação

### 5.1. Comunicação com os clientes

O sistema utilizará uma API REST sobre HTTP/JSON, permitindo a comunicação com interfaces web e outros clientes.

Entre os endpoints previstos estão:

| Método | Endpoint | Operação |
|---|---|---|
| `GET` | `/profissionais/{id}/disponibilidade` | Consultar horários disponíveis. |
| `POST` | `/consultas` | Agendar consulta. |
| `GET` | `/consultas/{id}` | Consultar uma consulta. |
| `PATCH` | `/consultas/{id}` | Reagendar uma consulta. |
| `POST` | `/consultas/{id}/cancelamento` | Cancelar uma consulta. |
| `POST` | `/consultas/{id}/confirmacao` | Confirmar uma consulta. |

A consulta de disponibilidade receberá a data desejada como parâmetro.

As respostas utilizarão códigos HTTP adequados, incluindo `201 Created` para agendamentos realizados, `400 Bad Request` para entradas inválidas, `403 Forbidden` para operações não autorizadas, `404 Not Found` para recursos inexistentes e `409 Conflict` para conflitos de agendamento.

A documentação detalhada das operações e de seus formatos de entrada e saída será mantida junto à implementação da API.

### 5.2. Comunicação interna

Os módulos se comunicam por chamadas de métodos e interfaces dentro da aplicação.

Não será utilizada comunicação HTTP entre os módulos, já que todos pertencem ao mesmo monólito.

Essa escolha evita latência de rede e infraestrutura adicional para operações internas.

### 5.3. Comunicação assíncrona

O envio de notificações será separado do processamento dos agendamentos.

O caso de uso registra a consulta e uma notificação pendente na mesma transação. O envio é executado posteriormente por um componente de processamento de notificações.

Esse mecanismo utiliza uma tabela de pendências no banco de dados, sem necessidade de um broker de mensagens externo.

## 6. Persistência e consistência

### 6.1. Banco de dados

O protótipo utilizará SQLite para armazenar pacientes, profissionais, agendas, consultas, bloqueios e notificações pendentes.

O acesso aos dados ocorrerá por repositórios, evitando dependências diretas entre os casos de uso e a tecnologia de persistência.

### 6.2. Controle de conflitos

As consultas possuem duração fixa de 30 minutos e utilizam horários alinhados à grade de atendimento.

Antes de realizar o agendamento, serão verificadas:

1. A existência de um período de atendimento válido.
2. A ausência de bloqueios na agenda do profissional.
3. A disponibilidade do profissional.
4. A ausência de outra consulta ativa do paciente no mesmo horário.

Consideram-se ativas as consultas com estado `AGENDADA` ou `CONFIRMADA`.

Para impedir reservas conflitantes, o banco utilizará restrições de unicidade condicionadas às consultas ativas, considerando os pares:

- `(profissional_id, inicio)`
- `(paciente_id, inicio)`

A verificação prévia de disponibilidade não é suficiente para garantir a consistência sob concorrência.

No SQLite, as operações de reserva utilizarão transações de escrita iniciadas antes das verificações de disponibilidade, com bloqueio de escrita antecipado (`BEGIN IMMEDIATE`). A validação dos bloqueios e a gravação da consulta ocorrerão dentro da mesma transação.

As operações que alteram a disponibilidade, como criação de bloqueios, seguirão o mesmo controle transacional.

Caso a reserva não possa ser concluída, a transação será revertida e a operação retornará um erro, sem produzir agendamento parcial.

### 6.3. Reagendamento

O reagendamento será tratado como uma operação transacional.

A disponibilidade do novo horário será verificada antes da confirmação da mudança. A liberação do horário anterior e a ocupação do novo serão realizadas na mesma transação.

Se ocorrer conflito ou falha, a transação será revertida, preservando a consulta original.

### 6.4. Unidade de trabalho

A interface `UnidadeDeTrabalho` coordenará as operações que precisam ser persistidas atomicamente.

No agendamento, isso inclui o registro da consulta e da notificação pendente.

Todas as operações da unidade de trabalho utilizarão a mesma transação de banco de dados, permitindo confirmar ou reverter as alterações em conjunto.

## 7. Notificações

### 7.1. Registro das pendências

Após validar um agendamento, a aplicação registra uma notificação pendente juntamente com a consulta.

Esse registro ocorrerá na mesma transação, garantindo que um agendamento persistido tenha sua notificação correspondente registrada.

A operação de agendamento não dependerá do sucesso do envio externo.

### 7.2. Processamento

Um componente separado será responsável por:

1. Consultar notificações pendentes.
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

A integração será isolada pela interface `ServicoAutenticacao`, implementada no protótipo por `AutenticacaoFake`.

As permissões serão verificadas conforme o papel do usuário, separando autenticação de autorização.

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
      consultas/
        dominio/
        aplicacao/
        portas/
      cadastros/
        dominio/
      notificacoes/
        aplicacao/
        portas/
      autenticacao/
        portas/
    infraestrutura/
      persistencia/
      notificacoes/
      autenticacao/

tests/
  dominio/
  aplicacao/
  integracao/
```

As interfaces ficarão próximas dos componentes que as utilizam. As implementações concretas serão mantidas na infraestrutura.

A composição das dependências será realizada na inicialização da aplicação.

Essa estrutura preserva a separação de responsabilidades e permite evoluir os módulos sem exigir sua implantação independente.

## 10. Relação com os ASRs

| ASR | Decisões arquiteturais relacionadas |
|---|---|
| **ASR-01 - Consistência** | Slots padronizados, validação de disponibilidade, restrições de unicidade e transações. |
| **ASR-02 - Modificabilidade** | Interface `Notificador`, portas e adaptadores, separação entre regras de negócio e infraestrutura. |
| **ASR-03 - Resiliência** | Registro transacional de notificações pendentes, envio desacoplado e mecanismo de reenvio. |

A arquitetura introduz algumas abstrações adicionais, mas mantém a aplicação em um único processo principal, reduzindo os custos de desenvolvimento e operação.

As alternativas arquiteturais e os custos das decisões serão detalhados nos documentos de trade-offs e ADRs.

## 11. Evolução da arquitetura

A separação entre domínio e infraestrutura permite substituir tecnologias sem alterar as regras centrais do sistema.

Na substituição do SQLite por PostgreSQL, serão modificados os adaptadores de persistência, a configuração de conexão e os mecanismos específicos de controle transacional.

Na substituição do canal de notificações, será necessário implementar outro adaptador e atualizar sua configuração.

A API REST também permite adicionar novos clientes sem modificar diretamente os casos de uso.

Essas possibilidades de evolução decorrem da organização modular e dos contratos estabelecidos entre os componentes.