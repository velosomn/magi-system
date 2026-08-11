# 🚀 MAGI System — Quick Start

Da instalação à primeira deliberação em ~5 minutos.

## 1. Obtenha as três chaves de API (2 min)

Duas das três são gratuitas. Você precisa das três — o sistema recusa iniciar com
qualquer uma faltando.

### Anthropic Claude — MELCHIOR + síntese final
1. Abra <https://console.anthropic.com/>
2. Menu lateral → **API keys** → **Create key**
3. Copie (começa com `sk-ant-`)

**Precisa de crédito na conta.** É o único provedor pago aqui: o Claude roda o
componente científico (com busca web) e escreve a síntese final.

### Google Gemini — BALTHASAR
1. Abra <https://makersuite.google.com/app/apikey>
2. **Create API Key**
3. Copie (começa com `AIza`)

Gratuito.

### Groq — GASPAR + o juiz
1. Abra <https://console.groq.com/>
2. Crie a conta → **API Keys** → **Create API Key**
3. Copie (começa com `gsk_`)

Gratuito e **não pede cartão de crédito**.

## 2. Instale (2 min)

```bash
cd magi_system

python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate

pip install -r requirements.txt
```

## 3. Configure as chaves (1 min)

```bash
cp .env.example .env
```

Abra o `.env` e preencha:

```env
CLAUDE_API_KEY=sk-ant-sua-chave-aqui
GEMINI_API_KEY=AIza-sua-chave-aqui
GROQ_API_KEY=gsk_sua-chave-aqui
```

> ⚠️ Nunca comite o `.env` nem cole uma chave em chat, issue ou print. Se expor uma,
> revogue no console do provedor **antes** de qualquer outra coisa — uma chave exposta
> continua válida até ser revogada. O `.gitignore` já protege o `.env`.

## 4. Rode

```bash
python cli.py "Vale a pena migrar nosso monolito para microsserviços?"
```

Leva 20–40 segundos: os três componentes rodam em paralelo, mas o MELCHIOR pode fazer
várias buscas web e o Claude raciocina antes de responder.

Modo interativo (várias perguntas na mesma sessão):

```bash
python cli.py
```

Interface web:

```bash
python web_server.py
# abra http://localhost:8000
```

## Como ler o resultado

```
📊 ANÁLISE DE CONSENSO
│ Posição MELCHIOR     │ ✅ favorável      │   ← posição de cada componente
│ Posição BALTHASAR    │ ⚠️ condicional    │
│ Posição GASPAR       │ ✅ favorável      │
│ Componentes ativos   │ 3 de 3            │   ← se for 2, houve falha
│ Concordância         │ 67%               │   ← quantos compartilham a posição majoritária
│ Veredito             │ CONDITIONAL_PASS  │
```

Os quatro vereditos:

| Veredito | Significado |
|---|---|
| ✅ `DELIBERATION_PASS` | Os três (ou os dois ativos) concordam, sem ressalvas |
| ⚠️ `CONDITIONAL_PASS` | Maioria favorável, mas há ressalvas materiais — leia as condições |
| 🔴 `CODE_RED` | Algum componente se posicionou **contra**, ou faltou quórum |
| 💥 `DIVERGENCE` | As posições se dividiram; não há maioria |

**`CODE_RED` com "veto ético"** significa que o BALTHASAR se posicionou contra. Isso
bloqueia a aprovação mesmo que os outros dois sejam favoráveis — é intencional.

Se o MELCHIOR fez buscas, as fontes aparecem logo abaixo do painel dele.

## Se der erro

### `❌ API Keys faltando`
O `.env` não existe, está em outra pasta, ou falta uma das três chaves. Confirme que ele
está na raiz do projeto (mesma pasta do `cli.py`) e que as três linhas estão preenchidas.

### `404 model ... not found` ou `model_decommissioned`
O ID do modelo foi aposentado — acontece com frequência. **Não tente adivinhar outro
ID**: liste os que a sua chave acessa e escolha um da lista.

```python
# Anthropic
import anthropic
for m in anthropic.Anthropic().models.list():
    print(m.id)

# Groq
from groq import Groq
for m in Groq().models.list().data:
    print(m.id)

# Gemini
from google import genai
for m in genai.Client().models.list():
    print(m.name)
```

Depois atualize o modelo do papel correspondente em `config.py`
(`MELCHIOR_MODEL`, `BALTHASAR_MODEL`, `GASPAR_MODEL`, `JUDGE_MODEL`).

### `429 RESOURCE_EXHAUSTED` (Gemini)
Cota do free tier estourada. Aguarde alguns minutos. Se acontecer só quando a busca é
acionada, é esperado: o grounding do Gemini exige plano pago — mas o BALTHASAR não usa
busca, então não deveria afetar o funcionamento normal.

### `429 insufficient_quota` / `credit_balance_exhausted` (Anthropic)
Sem crédito na conta. Adicione em
<https://console.anthropic.com/settings/billing>. Como paliativo, desligue a busca web
(`ENABLE_WEB_SEARCH = False` em `config.py`) — reduz o custo, mas o MELCHIOR perde
acesso a dados atuais.

### Veredito sai sempre `CONDITIONAL_PASS` com todas as posições `ℹ️ informativo`
O juiz não conseguiu classificar. Costuma ser a chave do Groq ou o `JUDGE_MODEL`
aposentado. O sistema é conservador aqui de propósito: sem classificação válida, ele
não inventa consenso.

## Próximos passos

- [WEB_INTERFACE.md](WEB_INTERFACE.md) — interface web e a API REST
- [DEVELOPMENT.md](DEVELOPMENT.md) — arquitetura e como adicionar um quarto componente
- [../example_advanced_usage.py](../example_advanced_usage.py) — 8 padrões de uso programático

```bash
pytest -m "not integration"    # 23 testes, sem custo de API
```
