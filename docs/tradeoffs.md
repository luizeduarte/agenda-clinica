# Trade-offs arquiteturais

A arquitetura escolhida combina duas decisões que não estão no mesmo nível, por
isso as alternativas são analisadas em dois eixos:

- **Eixo 1 — Implantação:** monólito simples, monólito
  modular ou microsserviços (ADR-001).
- **Eixo 2 — Organização interna:** camadas tradicionais ou
  camadas com portas e adaptadores (ADR-004).

Cada item indica, entre parênteses, o atributo de qualidade afetado e a parte
do problema nos requisitos a que se relaciona.

## 1. Eixo 1 — Implantação

### 1.1. Monólito simples

Uma aplicação sem fronteiras internas, ou seja, qualquer parte chama qualquer parte 
e acessa o banco diretamente.

**Pode favorecer**

- transação local no mesmo banco, impedindo conflitos do profissional e do 
  paciente (Atributo de Consistência; ASR-01, RN03, RN08);
- consulta e pendência de notificação gravadas na mesma transação, sem broker
  (Disponibilidade; ASR-03);
- um único artefato, sem fronteiras a manter (Custo de desenvolvimento);
- para rodar o sistema, basta iniciar um programa. Um artefato e um banco
  (Implantação, Custo de operação);
- chamadas diretas nas consultas de disponibilidade, por exemplo, que cruza diversos 
  dados (Desempenho; RF02).

**Pode custar**

- envio de notificação espalhado pelos fluxos que o disparam. Assim, trocar o canal
  altera as ações de agendar, cancelar e reagendar (Modificabilidade; ASR-02, RF08);
- regras de agenda e de paciente duplicadas entre agendar e reagendar
  (Modificabilidade; RN01, RN03, RN04, RN08);
- regras misturadas aos fluxos, o código fica testável só com banco e serviços reais
  (Testabilidade; RN05, RN08);
- tudo no mesmo processo, então uma falha pode derrubar o sistema inteiro
  (Disponibilidade);
- só é possível escalar o sistema inteiro (Escalabilidade; RF02).

### 1.2. Monólito modular (escolhida)

Uma aplicação e um banco, com diferentes módulos (`Agenda`, `Consultas`, `Cadastros`,
`Notificacoes` e `Autenticacao`, por exemplo) separados por interfaces internas.

**Pode favorecer**

- transação local e restrições de unicidade no banco, mesmo entre agendas 
  de profissionais diferentes (Consistência; ASR-01, RN03, RN08);
- consulta e pendência de notificação gravadas na mesma transação, sem broker
  (Disponibilidade; ASR-03);
- envio centralizado em um módulo dedicado às notificações (Modificabilidade; 
  ASR-02, RF08);
- para rodar o sistema, basta iniciar um programa. Um artefato e um banco
  (Implantação, Custo de operação);
- chamadas entre módulos dentro do mesmo processo, sem rede (Desempenho; RF02).

**Pode custar**

- módulos de negócio no mesmo processo, então uma falha pode derrubar os 
  módulos juntos (Disponibilidade);
- só é possível escalar o sistema inteiro (Escalabilidade; RF02);
- banco compartilhado: um módulo pode acessar tabelas de outro, e as
  fronteiras dependem de disciplina (Modificabilidade).

### 1.3. Microsserviços

Os módulos do monólito modular se tornam serviços implantados de forma independente, cada um com seu próprio banco e comunicando-se pela rede.

**Pode favorecer**

- escala separada do envio de notificações (Escalabilidade; RF08);
- falha em um serviço não derruba o resto do sistema (Disponibilidade; ASR-03).

**Pode custar**

- a verificação de horário de atendimento e bloqueio (em `Agenda`) e a gravação
  da consulta (em `Consultas`) ficam em bancos diferentes e não cabem em
  uma transação, exigindo coordenação distribuída (Consistência; ASR-01,
  RN01, RN04);
- broker e registro de pendências em cada serviço (Complexidade, Custo de
  operação; ASR-03);
- disponibilidade por especialidade consultando diferentes dados pela rede (Desempenho; RF02);
- dados do paciente replicados entre serviços (Segurança; restrição 5.1, LGPD);
- vários artefatos, pipelines e testes de integração entre serviços
  (Implantação, Testabilidade).

### 1.4. Decisão

**Monólito modular.** O monólito simples atende ao ASR-01 tão bem quanto ele,
porque também usa transação local, o que o descarta é a falta de fronteiras
para isolar os módulos, como as notificações (ASR-02, RF08). Microsserviços oferecem escala e isolamento que nenhum requisito da clínica exige, ao custo de separar
em bancos diferentes a verificação da agenda e a gravação da consulta (RN01,
RN04), o que exige coordenação distribuída.

Com isso, a decisão prioriza consistência (ASR-01) e modificabilidade (ASR-02),
com implantação e operação simples. Em troca, aceita que uma falha no processo
afete todos os módulos, que o sistema só escale por inteiro e que as fronteiras
entre módulos dependam de disciplina, já que o banco é compartilhado.

## 2. Eixo 2 — Organização interna

A partir da decisão por um monólito modular, é preciso decidir a organização interna do sistema.

### 2.1. Camadas tradicionais

Apresentação → aplicação → domínio → infraestrutura. Os casos de uso chamam
diretamente as classes concretas (repositório de banco de dados, cliente de e-mail,
cliente de autenticação).

**Pode favorecer**

- menos interfaces e indireção (Complexidade estrutural, Custo de
  desenvolvimento).

**Pode custar**

- o caso de uso de agendamento depende do cliente de e-mail concreto: trocar o canal
  altera o caso de uso (Modificabilidade; ASR-02);
- simulação do serviço universitário embutida na classe concreta
  (Testabilidade; restrição 5.2);
- RN05 e RN08 testáveis só com banco (Testabilidade).

### 2.2. Camadas com portas e adaptadores (escolhida)

Os casos de uso são portas de entrada, acionadas pelos controllers REST;
`Notificador`, `ServicoAutenticacao`, repositórios, entre outros, são
portas de saída, implementadas por adaptadores na infraestrutura. O núcleo não
depende dos adaptadores.

**Pode favorecer**

- troca de canal por um novo adaptador de `Notificador`, sem modificar
  outros módulos (Modificabilidade; ASR-02);
- implementações simuladas do notificador e da autenticação para simular falha
  no envio e o serviço universitário (Testabilidade; ASR-03, restrição 5.2);
- núcleo sem SQL nem HTTP, com RN02, RN05 e RN08 testáveis sem banco
  (Testabilidade);

**Pode custar**

- mais interfaces, adaptadores e indireção (Complexidade estrutural, Custo de
  desenvolvimento);

### 2.3. Decisão

**Camadas com portas e adaptadores.** O custo extra em interfaces é compensado
pelas portas que respondem diretamente a requisitos, como por exemplo `Notificador` (ASR-02, ASR-03) e `ServicoAutenticacao` (restrição 5.2).

Com isso, a decisão prioriza modificabilidade e testabilidade. Em troca, exige mais
interfaces e adaptadores e aumenta a indireção no código. Para conter esse custo,
só criamos portas onde há uma variação prevista nos requisitos (canal de
notificação, serviço de autenticação, mecanismo de persistência), e não uma
porta para cada classe.

---

## 3. ASRs, decisões e trade-offs

| ASR | Decisão favorecida | Prioriza | Pode prejudicar ou exigir |
|---|---|---|---|
| **ASR-01 — Consistência** | Monólito modular com transação local e restrições de unicidade no mesmo banco; verificação de disponibilidade e gravação da reserva em uma única transação (ADR-001, ADR-003). | Consistência dos agendamentos sob concorrência. | Desempenho sob carga, pois as escritas são serializadas no banco; escalabilidade, pois o sistema escala por inteiro; disponibilidade, pois uma falha no processo afeta todos os módulos. |
| **ASR-02 — Modificabilidade** | Módulo `Notificacoes` e porta `Notificador`; troca de canal por adaptador (ADR-002, ADR-004). | Modificabilidade do canal e testabilidade, com notificador simulado. | Mais interfaces e indireção, o que aumenta a complexidade estrutural e o custo de desenvolvimento. |
| **ASR-03 — Resiliência** | Fila de notificações implementada como tabela no mesmo banco: a pendência é gravada junto da consulta e enviada depois, sem acoplamento temporal com o canal (ADR-002). | Disponibilidade do agendamento e confiabilidade da entrega (falhas registradas e reenvio). | Notificação não imediata; possível mensagem duplicada, pois a entrega é *at-least-once* (risco aceito); monitoramento da fila; consultas e fila presas ao mesmo banco, disputando sua capacidade. |
