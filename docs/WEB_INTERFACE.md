# 🌐 Interface Web

Interface de deliberação com a geometria e a paleta do display do MAGI: três nós em
torno de um núcleo, laranja-sinal sobre preto, arestas duras. Todo o texto em português.

![Deliberação com veto](img/deliberacao-veto.png)

O display não mostra conteúdo — mostra **estado por componente**, que é exatamente o
que o motor de consenso produz. As análises completas ficam nos painéis abaixo.

## Subir

```bash
pip install -r requirements.txt   # inclui fastapi e uvicorn
python web_server.py              # http://localhost:8000
```

Requer as três chaves no `.env` (veja [QUICKSTART.md](QUICKSTART.md)). O indicador
`ENLACE ATIVO` no canto superior direito confirma que o front conversou com a API;
`SEM CHAVES` significa que o servidor subiu mas o MAGI não inicializou.

## Como ler o display

Cada nó assume a cor da posição que o componente defendeu:

| Cor | Posição | Significado |
|---|---|---|
| 🟢 Verde | `FAVORÁVEL` | Recomenda a favor, sem ressalvas materiais |
| 🟡 Âmbar | `CONDICIONAL` | A favor, condicionado a salvaguardas |
| 🔴 Vermelho | `CONTRÁRIO` | Recomenda contra |
| 🟠 Laranja | `SEM POSIÇÃO` | Tratou a questão como analítica |
| ⬛ Cinza | `OFFLINE` | O componente falhou e saiu da votação |

O núcleo carimba o veredito:

| Núcleo | Quando |
|---|---|
| `APROVADO` | Todos os ativos favoráveis |
| `RESSALVAS` | Maioria favorável (≥ 66%) com condições, ou todos sem posição |
| `REJEITADO` | Alguma posição contrária, **ou** menos de 2 componentes vivos |
| `IMPASSE` | Posições divididas, sem maioria |

Duas faixas aparecem quando pertinente: **veto ético** (BALTHASAR se posicionou contra
e bloqueou a aprovação) e **sistema degradado** (algum componente não respondeu — a
concordância exibida considera só os ativos).

O veredito não vem de faixas de porcentagem. Vem da votação por categorias, avaliada
nesta ordem: quórum → veto → qualquer objeção → concordância. Um `REJEITADO` pode
acontecer com 100% de concordância, se os três concordarem que a resposta é não.

## Link direto

O parâmetro `?q=` preenche e delibera automaticamente:

```
http://localhost:8000/?q=Devemos%20migrar%20para%20microsservi%C3%A7os%3F
```

## API

### `POST /api/deliberate`

```bash
curl -X POST http://localhost:8000/api/deliberate \
  -H "Content-Type: application/json" \
  -d '{"query": "Sua questão aqui"}'
```

```json
{
  "success": true,
  "query": "Sua questão",
  "verdict": "CODE_RED",
  "consensus_rate": 0.33,
  "reasoning": "🔴 VETO ÉTICO — BALTHASAR se posiciona contra…",
  "stances": { "MELCHIOR": "INFO", "BALTHASAR": "NO", "GASPAR": "CONDITIONAL" },
  "live_agents": 3,
  "degraded": false,
  "vetoed": true,
  "perspectives": { "melchior": "…", "balthasar": "…", "gaspar": "…" },
  "sources": ["Título da fonte 1", "…"],
  "synthesis": "Recomendação final…"
}
```

| Campo | Tipo | Significado |
|---|---|---|
| `verdict` | string | `DELIBERATION_PASS` · `CONDITIONAL_PASS` · `CODE_RED` · `DIVERGENCE` |
| `stances` | objeto | Posição por componente: `YES` · `CONDITIONAL` · `NO` · `INFO` · `ERROR` |
| `consensus_rate` | float | Fração dos componentes **ativos** com a posição majoritária |
| `live_agents` | int | Quantos dos 3 responderam. Abaixo de 2 não há veredito válido |
| `degraded` | bool | `true` quando algum componente falhou |
| `vetoed` | bool | `true` quando o BALTHASAR bloqueou a aprovação |
| `sources` | array | Páginas que o MELCHIOR consultou (vazio se a busca não acionou) |

⚠️ `consensus_rate` considera **apenas os ativos**: dois concordando com um terceiro
caído dá 100%, com `degraded: true`. Leia os dois campos juntos.

### Demais rotas

| Rota | Devolve |
|---|---|
| `GET /api/health` | Se o servidor subiu e se o MAGI inicializou |
| `GET /api/config` | Modelo de cada papel, o juiz e os limiares |
| `GET /api/info` | Descrição dos componentes e das rotas |
| `GET /docs` | Swagger gerado pelo FastAPI |
| `WS /ws/deliberate` | Mesmo payload do REST, com `"status": "complete"` |

## Arquivos

```
static/
├── index.html    SVG do display + painéis
├── style.css     paleta, geometria e estados por posição
└── app.js        consulta, render e progressão
```

O `app.js` converte apenas quatro padrões de markdown (`**negrito**`, `` `código` ``,
títulos e parágrafos) e **escapa o HTML antes** — as respostas vêm de modelos e não
são inseridas como markup bruto.

## Personalizar

Cores e geometria ficam em `style.css`:

```css
--orange:   #FF6A00;   /* estrutura e estado ativo */
--favor:    #35BF63;
--ressalva: #E9A400;
--contra:   #E8402A;
--morto:    #45443F;   /* componente offline */
```

Os polígonos dos nós são coordenadas literais no `index.html` (`viewBox="0 0 960 500"`),
sem rotação — mexer neles é editar os `points` diretamente.

## Limitações

- **A progressão é simulada.** O texto de etapa avança por temporizador, não por evento
  real. Como a API só responde no fim, os três nós acendem juntos. Migrar o `app.js`
  para o WebSocket daria progresso real por componente.
- **Sem histórico.** Cada deliberação é independente.
- **Sem autenticação.** Serve para uso local; não exponha a porta 8000 na internet sem
  colocar autenticação na frente — quem alcançar a rota gasta os seus créditos de API.
