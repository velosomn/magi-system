# 🛠️ MAGI System - Development Guide

## Arquitetura Detalhada

### Componentes Principais

```
┌─────────────────────────────────────────────────────────────┐
│         cli.py (rich)          web_server.py (FastAPI)      │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  magi_core.py — deliberate()                │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  MELCHIOR    │  │  BALTHASAR   │  │   GASPAR     │      │
│  │   Claude     │  │   Gemini     │  │ Groq Llama   │      │
│  │ + busca web  │  │ + veto       │  │              │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         └─── asyncio.gather (paralelo) ──────┘              │
│                         ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  _classify_stances — JUIZ (Groq gpt-oss-120b)       │   │
│  │  Lê as 3 respostas → StanceType de cada uma.        │   │
│  │  Família distinta dos agentes: quem tem veto não    │   │
│  │  pode classificar o próprio voto.                   │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            ↓                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  _consolidate — função pura, sem I/O                │   │
│  │  quórum → veto → objeção → concordância             │   │
│  │  → (verdict, rate, vetoed, reasoning)               │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            ↓                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  _synthesize_recommendation (Claude)                │   │
│  │  Instrução condicionada ao veredito já apurado      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         ↑
              config.py — papéis, modelos, limiares
```

## Fluxo de Execução

1. **Input** — CLI ou HTTP recebe a questão
2. **Dispatch** — `deliberate()` chama os 3 componentes em paralelo.
   Exceções soltas viram `MagiResponse(failed=True)` **na posição correta** — filtrar
   desalinharia os índices e trocaria os rótulos dos painéis
3. **Classificação** — o juiz independente devolve a posição de cada resposta.
   Só respostas com `.alive == True` entram
4. **Consolidação** — `_consolidate` aplica, nesta ordem:
   quórum (≥2 vivos) → veto do BALTHASAR → qualquer objeção → concordância
5. **Síntese** — a instrução muda conforme o veredito: sob veto ela não pode
   recomendar prosseguir; sob divergência não pode forçar meio-termo
6. **Output** — veredito, placar de posições, fontes consultadas

### Por que a classificação é um passo separado

O motor precisa saber **o que cada componente defende**, não quão parecidas as
respostas são. A versão anterior media variância de comprimento e reportava 94% de
consenso quando os três agentes falharam com 404 — mensagens de erro têm tamanho
parecido. Ver `test_tres_falhas_nao_viram_consenso`.

Cada agente encerra com uma linha `POSIÇÃO:`, então o trabalho do juiz é mais
extração do que julgamento — daí um modelo pequeno e barato dar conta.

## Estendendo o Sistema

### Adicionar Novo Agente

1. **Defina o agent em `config.py`:**

```python
@dataclass
class MagiConfig:
    SOPHIAS_MODEL: str = "novo-modelo"
    SOPHIAS_API_KEY: str = os.getenv("SOPHIAS_API_KEY", "")
```

2. **Crie method em `magi_core.py`:**

```python
async def call_sophias(self, query: str) -> MagiResponse:
    """Novo agente SOPHIAS"""
    try:
        response = await asyncio.to_thread(
            seu_client.create,
            model=self.config.SOPHIAS_MODEL,
            # ...
        )
        return MagiResponse(agent="SOPHIAS", response=response)
    except Exception as e:
        return MagiResponse(agent="SOPHIAS", response=f"Erro: {e}")
```

3. **Atualize `deliberate()` para incluir novo agente:**

```python
agent_names = ("MELCHIOR", "BALTHASAR", "GASPAR", "SOPHIAS")  # manter em sincronia
raw = await asyncio.gather(
    self.call_melchior(query),
    self.call_balthasar(query),
    self.call_gaspar(query),
    self.call_sophias(query),  # novo
    return_exceptions=True,
)
```

⚠️ **Quatro pontos que quebram silenciosamente se você esquecer:**

- `agent_names` no `deliberate()` precisa da nova entrada, **na mesma ordem** do
  `gather` — é o que mapeia índice → nome quando uma exceção escapa
- O `enum` do juiz em `_classify_stances` lista os agentes válidos; um nome ausente
  faz o juiz devolver o agente sem classificação, e ele fica em `INFO`
- `ConsensusResult` expõe as respostas por campo nomeado
  (`melchior_response`, …) — adicione o novo campo e ajuste a CLI e o `web_server`
- O quórum em `_consolidate` é `< 2` fixo. Com 4+ componentes, considere se o mínimo
  deveria ser proporcional

### Customizar System Prompts

Edite `_initialize_system_prompts()`. Todo prompt precisa manter dois elementos, ou
o motor de consenso degrada:

```python
_SHARED_CONTEXT   # nomeia os três componentes e proíbe responder pelos outros
                  # sem isso um agente inventa colegas — o GASPAR já anunciou
                  # "as 3 perspectivas: GASPAR, LUNA e SOL"
"POSIÇÃO:"        # a linha final que o juiz usa como sinal principal
```

`test_todo_agente_conhece_os_colegas` e `test_todo_agente_declara_posicao` protegem
os dois.

### Ajustar a lógica de veredito

Toda a decisão vive em `_consolidate` — função pura, sem I/O, testável sem API.
Os limiares estão em `config.py` (`CONSENSUS_THRESHOLD`, `DIVERGENCE_THRESHOLD`).

Para mudar quem tem poder de veto, altere a checagem em `_consolidate`:

```python
balthasar = next((r for r in live if r.agent == "BALTHASAR"), None)
vetoed = balthasar is not None and balthasar.stance is StanceType.NO
```

Se der veto a mais de um componente, atualize também
`test_apenas_balthasar_tem_veto` e o prompt de quem ganhar o poder — o agente
precisa **saber** que tem veto para usá-lo com parcimônia.

### Melhorias possíveis no motor

O classificador atual é um LLM lendo a linha `POSIÇÃO:`. Alternativas, em ordem de
custo-benefício:

1. **Extrair a linha `POSIÇÃO:` por regex** e usar o LLM só como fallback — elimina
   uma chamada de API na maioria dos casos
2. **Rodadas de deliberação** — cada agente vê as respostas dos outros e pode revisar
   a posição (padrão debate). Custa latência: acabaria com o paralelismo puro
3. **Similaridade semântica por embeddings** como métrica secundária ao lado da
   votação — mede se dois "sim" concordam pelos *mesmos motivos*

## Testing

### Executar Testes Unitários

```bash
pytest test_magi.py -v
```

### Executar Apenas Testes de Configuração

```bash
pytest test_magi.py::TestMagiConfig -v
```

### Executar Testes de Integração

Requer API keys configuradas:

```bash
pytest test_magi.py -v -m integration
```

### Coverage

```bash
pytest test_magi.py --cov=magi_core --cov=config --cov-report=html
```

## Performance Optimization

### Caching de Respostas

Adicionar ao `magi_core.py`:

```python
from functools import lru_cache
import hashlib

class MagiSystem:
    def __init__(self, config):
        self._cache = {}
    
    def _hash_query(self, query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()
    
    async def deliberate(self, query: str):
        query_hash = self._hash_query(query)
        if query_hash in self._cache:
            return self._cache[query_hash]
        
        result = await self._deliberate_impl(query)
        self._cache[query_hash] = result
        return result
```

### Parallel Timeout Optimization

```python
async def deliberate(self, query: str):
    try:
        responses = await asyncio.wait_for(
            asyncio.gather(
                self.call_melchior(query),
                self.call_balthasar(query),
                self.call_gaspar(query),
            ),
            timeout=self.config.TOTAL_TIMEOUT
        )
    except asyncio.TimeoutError:
        # Fallback to partial results
        pass
```

## Debugging

### Enable Verbose Logging

Adicione ao `cli.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect API Responses

Modifique `magi_core.py`:

```python
async def call_melchior(self, query: str) -> MagiResponse:
    print(f"[DEBUG] Query to Gemini: {query}")
    response = await asyncio.to_thread(...)
    print(f"[DEBUG] Gemini response: {response.text[:200]}")
    return MagiResponse(...)
```

### Check Consensus Calculation

```python
result = await magi.deliberate("test query")
print(f"Consensus: {result.consensus_rate}")
print(f"Verdict: {result.verdict}")
```

## Limitações conhecidas

1. **A progressão da interface web é simulada.** O `app.js` avança o texto de etapa por
   temporizador, não por evento real — a API só responde no fim, então os três nós
   acendem juntos. O WebSocket já devolve o payload correto; migrar o `app.js` do REST
   para ele daria progresso real por componente.

2. **Só MELCHIOR tem busca.** BALTHASAR e GASPAR respondem do conhecimento de treino.
   Ligar busca no BALTHASAR exigiria plano pago no Gemini; no GASPAR, trocar para
   `groq/compound`.

3. **Sem persistência.** Nenhum histórico de deliberações.

4. **Timeout fixo.** `API_TIMEOUT`/`TOTAL_TIMEOUT` não escalam com a complexidade da
   questão. Uma deliberação com várias buscas web pode passar de 60s.

5. **O juiz é um ponto único de falha.** Se ele cair, todas as posições ficam `INFO` e
   o veredito vira `CONDITIONAL_PASS`. É conservador de propósito — melhor do que
   fabricar consenso — mas é uma degradação silenciosa: nada avisa que a classificação
   não aconteceu.

6. **Claude ainda acumula dois papéis.** É MELCHIOR e também escreve a síntese. Menos
   grave do que era (o juiz saiu do Claude), porque a síntese acontece **depois** do
   veredito estar fechado e é vinculada a ele — mas não é independência total.

## Contribuindo

1. Fork o repo
2. Crie uma feature branch: `git checkout -b feature/X`
3. Commit mudanças: `git commit -am 'Add X'`
4. Push branch: `git push origin feature/X`
5. Abra Pull Request

## Troubleshooting Desenvolvimento

### "ModuleNotFoundError: No module named 'config'"

```bash
# Certifique-se de estar no diretório correto
cd magi_system
python cli.py
```

### Async RuntimeError

```python
# Windows PowerShell pode precisar:
$env:PYTHONIOENCODING = "utf-8"
python cli.py
```

### API Rate Limits

Use backoff exponencial:

```python
import asyncio
import tenacity

@tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
    stop=tenacity.stop_after_attempt(3)
)
async def call_with_retry(self, api_call):
    return await api_call()
```

---

Desenvolvido com ❤️ e café ☕
