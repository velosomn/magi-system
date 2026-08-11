# 🔬 Comparação com outras implementações do MAGI

Três implementações públicas inspiradas no MAGI de *Evangelion*, o que cada uma resolve,
e o que este projeto tomou emprestado.

---

## 1. [TomaszRewak/MAGI](https://github.com/TomaszRewak/MAGI)

**Stack:** ChatGPT-3.5 · Dash/Plotly · MIT
**Agentes:** MELCHIOR (científico) · BALTHASAR (maternal) · CASPER (pessoal)

### O que faz de diferente

O fluxo não é "três respostas e uma média". É uma **votação com categorias**:

1. Classifica se a questão admite resposta sim/não
2. Cada agente responde
3. **Classifica cada resposta numa categoria**
4. Consolida por ordem de prioridade: `erro > info > não > condicional > sim`

Note a ordem: um "não" vence dois "sim". O sistema tem viés de segurança embutido.

### O que copiamos daqui

**Praticamente todo o nosso motor de consenso.** Esta foi a contribuição mais valiosa
das três referências, e resolveu o bug mais grave que tínhamos.

Nossa primeira versão calculava consenso por **variância de comprimento das respostas**.
O resultado: três agentes falhando com erro 404 produziam "94% de consenso, aprovado" —
porque mensagens de erro têm tamanho parecido. O sistema aprovava com convicção enquanto
nenhum componente havia respondido.

Adotamos a ideia do Rewak com três adaptações:

| Rewak | Aqui |
|---|---|
| Classifica com o mesmo modelo dos agentes | **Juiz de família distinta** — quem tem veto não classifica o próprio voto |
| `erro > info > não > condicional > sim` | `ERROR > NO > CONDITIONAL > YES > INFO` — INFO no fim, por ser neutro |
| Prioridade uniforme entre agentes | **Veto nomeado**: uma objeção do BALTHASAR é registrada como veto ético explícito |

Também adotamos a **checagem de quórum**: abaixo de dois componentes vivos não há
veredito, apenas `CODE_RED` por sistema degradado.

### O que não copiamos

A classificação prévia da questão em "admite sim/não" ou não. Nosso juiz classifica as
**respostas**, não a pergunta — se os três tratam a questão como analítica, a categoria
`INFO` emerge naturalmente da votação sem precisar de um passo extra.

---

## 2. [lordpba/AI_Magi](https://github.com/lordpba/AI_Magi)

**Stack:** CrewAI · Gradio · LiteLLM · Groq/OpenAI/Ollama · Hugging Face Spaces
**Agentes:** Melchior (lógica) · Balthasar (ética/emoção) · Casper (prático/social)

### O que faz de diferente

- **LiteLLM** como camada de abstração — trocar de provedor é trocar uma string
- **Ollama** para modelos locais, gratuitos e offline
- Deploy real no Hugging Face Spaces
- Estrutura organizada em `config/`, `src/`, `scripts/`, `docs/`

### O que copiamos daqui

**A organização em `docs/`** — a raiz do repositório fica só com código e README.

**A lição sobre abstração de provedor, aprendida do jeito difícil.** Nós grudamos três
SDKs direto no código, e pagamos o preço: seis rodadas de erro porque os IDs de modelo
que usávamos havia sido aposentados. Com uma camada como LiteLLM — ou apenas com os IDs
no `.env` em vez de no código — teria sido uma edição de uma linha.

Mitigação parcial adotada: os modelos agora ficam em campos nomeados **por papel**
(`MELCHIOR_MODEL`, `BALTHASAR_MODEL`, `GASPAR_MODEL`, `JUDGE_MODEL`) em vez de por
provedor. Trocar o provedor de um papel é uma mudança localizada.

### O que não copiamos

**CrewAI.** É um framework de orquestração sequencial com delegação entre agentes. Nosso
caso de uso é mais simples — três chamadas paralelas independentes — e o `asyncio.gather`
resolve sem a dependência. O ganho é latência: paralelo puro contra sequencial.

**Ollama.** Vale a pena e está na lista: um fallback local significa que o sistema degrada
em vez de morrer quando uma chave falha ou o crédito acaba. Não implementado.

---

## 3. [Artigo do Mario PBA no Medium](https://medium.com/@mario.pba/building-a-multi-agent-system-inspired-by-evangelions-magi-supercomputer-1d163704dca9)

**Stack:** CrewAI · LangChain · Groq/OpenAI · SerperDevTool
**Agentes:** Melchior-1 (análise técnica) · Balthasar-2 (estratégia de defesa) · Casper-3 (avaliação ética)

### O que faz de diferente

- **Busca web via SerperDevTool** — os agentes têm acesso a dados externos
- **Tarefas sequenciais** com `allow_delegation=True`: cada agente vê o resultado do anterior
- Casper fecha resumindo tudo e emitindo o julgamento ético final

### O que copiamos daqui

**A ideia de grounding.** Foi a leitura deste artigo que expôs uma contradição no coração
do nosso projeto: o prompt do MELCHIOR mandava "citar evidências e dados", e ele obedecia
**inventando números** — porque não tinha acesso a nenhum dado.

Nossa implementação difere na execução. Em vez de uma ferramenta de busca externa, usamos
a busca web nativa da Anthropic no MELCHIOR. Isso determinou o mapeamento de papéis: o
grounding do Gemini exige plano pago, então o papel analítico foi para o Claude, que é
onde a busca funciona. Detalhes no [README](../README.md#os-três-componentes).

### O que não copiamos

**As tarefas sequenciais.** É o padrão debate/reflexão, e tem mérito real: um agente que
vê o argumento do outro pode revisar sua posição. Mas custa o paralelismo — nossa
deliberação inteira leva o tempo do componente mais lento, não a soma dos três.

Está na lista como modo opcional ("rodadas de deliberação"), não como default.

---

## Comparação técnica

| Critério | Este projeto | Rewak | Medium/CrewAI |
|---|---|---|---|
| **Orquestração** | `asyncio` nativo | Sequencial | CrewAI |
| **Paralelismo** | ✅ Real | ❌ | ⚠️ Parcial |
| **Consolidação** | Votação por categorias + veto + quórum | Votação por categorias | Delegação entre tarefas |
| **Independência do juiz** | ✅ Família distinta dos agentes | ❌ Mesmo modelo | — |
| **Grounding** | ✅ MELCHIOR (busca nativa) | ❌ | ✅ SerperDevTool |
| **Provedores distintos** | 3 (Anthropic, Google, Groq) | 1 | 1–2 |
| **Degradação graciosa** | ✅ Quórum explícito, falha visível | ❌ | ❌ |
| **Interface** | CLI + web + API REST/WS | Dash | CLI |
| **Testes** | 29 (23 sem custo de API) | — | — |

O uso de **três provedores diferentes** é uma escolha deliberada: agentes rodando no
mesmo modelo base tendem a concordar por compartilharem os mesmos vieses de treino.
Divergência genuína exige diversidade real de modelos — sem isso, o "consenso" mede
menos do que parece.

---

## O que ainda falta

Ordenado por valor:

1. **Fallback local com Ollama** (do AI_Magi) — o sistema degrada em vez de morrer
   quando uma chave falha. Resolveria o caso concreto de um cartão de crédito recusado.
2. **Interface web à altura do motor** — o `app.js` ignora posições, veto e fontes que
   a API já devolve. Hoje o CLI é estritamente superior.
3. **Rodadas de deliberação** (do artigo) — agentes revisando posições após ver os
   outros. Trade-off explícito de latência.
4. **Persistência** — nenhum histórico de deliberações.
5. **Extrair `POSIÇÃO:` por regex** antes de chamar o juiz — economizaria uma chamada
   de API na maioria dos casos, com o LLM só como fallback.

---

## Nota sobre o cânone

Nos três projetos e neste, o componente ético carrega um peso que o anime não dá. No
MAGI original a decisão é por **maioria simples** entre os três — e a tensão dramática
da série vem justamente de um dos três discordar e ser sobrepujado.

O veto do BALTHASAR aqui é uma escolha de projeto, não fidelidade: para um sistema que
pode recomendar ações no mundo real, um viés de segurança explícito vale mais do que
fidelidade narrativa. Está isolado em `_consolidate` se você preferir maioria simples.
