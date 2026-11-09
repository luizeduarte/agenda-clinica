# Trade-offs arquiteturais

## 1. Alternativas consideradas

Foram consideradas três alternativas para o sistema:

- Alternativa A — monólito simples: aplicação única com pouca separação
  entre domínio, casos de uso e infraestrutura.
- Alternativa B — monólito modular com camadas e inspiração hexagonal:
  apresentação, aplicação, domínio e infraestrutura separadas por contratos.
- Alternativa C — microsserviços: serviços independentes para partes como
  agenda, consultas e notificações.

A Alternativa B foi escolhida.

## 2. Comparação

| Critério | Monólito simples | Monólito modular + camadas/hexagonal | Microsserviços |
|---|---|---|---|
| Modificabilidade | Baixa: regras e infraestrutura tendem a se misturar | Alta: portas e adaptadores isolam integrações | Alta entre serviços, mas com contratos distribuídos |
| Desempenho | Bom em chamadas internas, com pouca indireção | Bom, pois a comunicação principal permanece em processo | Pode sofrer latência e custo de rede |
| Disponibilidade | Operação simples, mas falhas ficam concentradas | Operação simples e bom isolamento lógico | Pode isolar falhas, mas exige infraestrutura distribuída |
| Testabilidade | Menor quando há dependência direta de banco e serviços | Alta: domínio e aplicação usam contratos substituíveis | Alta por serviço, mas exige testes de integração e contrato |
| Complexidade | Baixa inicialmente, com risco de crescimento desorganizado | Moderada e explícita | Alta, especialmente para transações e diagnóstico |
| Implantação | Simples | Simples, com módulos no mesmo artefato | Complexa, com vários artefatos e pipelines |
| Escalabilidade | Escala o sistema inteiro | Escala o sistema inteiro inicialmente | Permite escalar serviços separadamente |
| Custo de desenvolvimento/operação | Baixo no início, maior custo de manutenção futura | Moderado e proporcional ao protótipo | Alto para o escopo e a equipe atuais |

## 3. Alternativa A — monólito simples

### Vantagens

- menor custo inicial;
- implantação e operação simples;
- comunicação interna direta;

### Desvantagens

- pode misturar regras de negócio e integrações externas;
- dificulta testar o domínio sem banco ou serviços reais;
- torna a troca do canal de notificação mais invasiva;
- aumenta o risco de uma falha no notificador bloquear o agendamento;
- logica muito concetrada, dificultando a modificabilidade;

Foi rejeitada porque não atende tão bem à modificabilidade do ASR-02 nem
ao isolamento de falhas do ASR-03. A menor complexidade inicial não
compensa o acoplamento nas partes que o projeto exige que sejam substituíveis.

## 4. Alternativa B — monólito modular com camadas e inspiração hexagonal

### Vantagens

- separa regras de domínio, coordenação de casos de uso, apresentação e
  infraestrutura;
- permite que `Notificador`, repositórios e autenticação sejam contratos com
  adaptadores substituíveis;
- mantém a comunicação principal em processo, sem custo de rede entre
  módulos;
- permite registrar consulta e notificação pendente na mesma transação;
- facilita testes unitários e de integração;
- preserva fronteiras que podem apoiar uma futura extração de serviços.

### Desvantagens

- adiciona interfaces, classes e indireções (complexidade de implantação);
- exige disciplina para preservar a regra de dependência entre camadas;
- não permite escalar cada módulo de forma independente;

Esta alternativa oferece o melhor equilíbrio para o escopo atual. Ela atende
ao ASR-01 com uma transação e persistência compartilhada, ao ASR-02
com a interface `Notificador`, e ao ASR-03 com o registro transacional de
pendências e o processamento posterior.

## 5. Alternativa C — microsserviços

### Vantagens

- permite implantar e escalar notificações ou consultas separadamente;
- pode isolar falhas entre serviços;
- favorece evolução independente quando há equipes, cargas ou ciclos de
  implantação diferentes;

### Desvantagens

- exige comunicação de rede, observabilidade e operação distribuída;
- aumenta o custo de desenvolvimento e implantação;
- dificulta garantir atomicamente a reserva e o registro da notificação;
- exige coordenação distribuída, eventos ou outra estratégia para manter
  consistência;

Foi rejeitada porque o protótipo não precisa de implantação independente nem
de escalabilidade por serviço. Para o ASR-01, transformar uma transação
local em uma operação distribuída aumentaria o risco e a complexidade. O
monólito modular mantém fronteiras explícitas sem antecipar esse custo.