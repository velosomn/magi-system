# 📁 MAGI System — Estrutura do Projeto

```
magi_system/
│
├── config.py                    ⭐ Comece aqui — papéis, modelos, limiares
├── magi_core.py                 ⭐⭐⭐ Agentes + juiz + motor de consenso
├── cli.py                       ⭐⭐ Interface de terminal
├── web_server.py                API FastAPI + WebSocket
├── static/                      Interface web (index.html, style.css, app.js)
│
├── test_magi.py                 29 testes (23 unitários + 6 de integração)
├── pytest.ini                   Registra o marcador `integration`
├── example_advanced_usage.py    8 padrões de uso programático
├── example_output.txt           Saída real do CLI, para referência
│
├── requirements.txt             Dependências
├── setup.py                     Instalação assistida
├── .env.example                 Template das três chaves
├── .env                         ⚠️ Suas chaves — nunca comitar
├── .gitignore
│
├── README.md                    Documentação principal
└── docs/
    ├── QUICKSTART.md            5 minutos até a primeira deliberação
    ├── WEB_INTERFACE.md         Interface web e API REST
    ├── DEVELOPMENT.md           Arquitetura e extensão
    ├── RESEARCH_INSIGHTS.md     Comparação com outras implementações do MAGI
    └── PROJECT_STRUCTURE.md     Este arquivo
```

---

## `config.py` — configuração e tipos

Dois enums e uma dataclass. É o arquivo a editar quando um modelo é aposentado.

```python
VerdictType     # DELIBERATION_PASS | CONDITIONAL_PASS | CODE_RED | DIVERGENCE
StanceType      # ERROR | NO | CONDITIONAL | YES | INFO  (nesta ordem de prioridade)
MagiConfig      # chaves, modelos por papel, limiares, validate()
```

O mapeamento papel → modelo mora aqui:

| Campo | Default | Papel |
|---|---|---|
| `MELCHIOR_MODEL` | `claude-opus-5` | Científico, com busca web |
| `BALTHASAR_MODEL` | `gemini-3.5-flash` | Ético, com poder de veto |
| `GASPAR_MODEL` | `llama-3.3-70b-versatile` | Prático |
| `JUDGE_MODEL` | `openai/gpt-oss-120b` | Classifica as posições |
| `SYNTHESIS_MODEL` | `claude-opus-5` | Escreve a recomendação final |

`ENABLE_WEB_SEARCH` liga/desliga a busca do MELCHIOR (é cobrada por uso).

**`StanceType` é ordenado de propósito.** A ordem de declaração é a ordem de prioridade
na consolidação: um `ERROR` ou um `NO` pesam mais do que dois `YES`.

---

## `magi_core.py` — o núcleo

### Estruturas

```python
MagiResponse       # agent, response, stance, failed, sources
                   #   .alive  → False se a chamada de API falhou
ConsensusResult    # verdict, consensus_rate, as 3 respostas,
                   #   final_recommendation, reasoning,
                   #   stances, live_agents, vetoed, sources
```

O campo `failed` é explícito em vez de inferido do texto. Antes, o sistema tentava
adivinhar falhas olhando a string da resposta — e mensagens de erro entravam na votação.

### Fluxo de `deliberate()`

```
1. asyncio.gather   → chama os 3 componentes em paralelo
                      exceções soltas viram MagiResponse(failed=True) na posição
                      correta (filtrar desalinharia os índices e trocaria os rótulos)

2. _classify_stances → juiz independente lê as 3 respostas e devolve JSON com a
                       posição de cada uma; falha do juiz mantém INFO em vez de
                       fabricar consenso

3. _consolidate      → aplica quórum, veto e prioridade; devolve
                       (verdict, consensus_rate, vetoed, reasoning)

4. _synthesize_recommendation → escreve a síntese, com instrução condicionada
                                ao veredito já apurado
```

### Métodos

| Método | O que faz |
|---|---|
| `call_melchior` | Claude + `web_search`; retoma em `pause_turn` para não truncar |
| `call_balthasar` | Gemini; resposta vazia conta como falha, não como posição vazia |
| `call_gaspar` | Groq Llama |
| `_classify_stances` | Juiz independente → `StanceType` de cada resposta (in-place) |
| `_consolidate` | Quórum → veto → objeção → concordância. **Toda a lógica de veredito** |
| `_synthesize_recommendation` | Síntese vinculada ao veredito |
| `_extract_text` | Texto de uma resposta Claude, ignorando blocos de thinking |
| `_extract_sources` | Títulos das fontes da busca web |

`_consolidate` é uma função pura — é por isso que 8 dos testes cobrem o motor de
consenso sem tocar em nenhuma API.

---

## `cli.py` — interface de terminal

```python
print_banner()              # ASCII art NERV
print_agent_response()      # painel colorido por componente
print_consensus_table()     # posições, quórum, veto, veredito
interactive_mode()          # loop REPL
single_query_mode()         # pergunta única via argv
```

Cores por componente: MELCHIOR azul, BALTHASAR verde, GASPAR amarelo.

---

## `test_magi.py` — 29 testes

| Classe | Cobre |
|---|---|
| `TestConsolidacao` | 8 cenários do motor: quórum, veto, objeção, divergência |
| `TestMagiResponse` | `.alive` distingue resposta de falha |
| `TestMagiConfig` | Limiares; **juiz é de família distinta dos agentes** |
| `TestVerdictType` | Os 4 vereditos existem |
| `TestSystemPrompts` | Cada agente conhece os colegas, declara `POSIÇÃO:`, só BALTHASAR tem veto |
| `TestIntegration` | 6 testes contra APIs reais (`-m integration`) |

Dois testes existem por causa de bugs reais observados:

- **`test_tres_falhas_nao_viram_consenso`** — a versão anterior reportava 94% de consenso
  quando os três agentes falharam com 404, porque media variância de comprimento e
  mensagens de erro têm tamanho parecido.
- **`test_todo_agente_conhece_os_colegas`** — o GASPAR anunciou "as 3 perspectivas:
  GASPAR, LUNA e SOL", inventando dois colegas, porque o prompt não nomeava os outros.

---

## Pontos de entrada por objetivo

**Usar:** [QUICKSTART.md](QUICKSTART.md) → `python cli.py`

**Entender a decisão:** `_consolidate` em `magi_core.py` — é onde o veredito nasce

**Trocar um modelo:** `config.py`, o campo do papel correspondente

**Adicionar um componente:** [DEVELOPMENT.md](DEVELOPMENT.md) → seção de extensão

**Integrar:** [WEB_INTERFACE.md](WEB_INTERFACE.md) (REST) ou `deliberate()` direto
