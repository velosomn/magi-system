"""MAGI Core System - Consensus Engine com 3 LLMs"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional
import anthropic
from google import genai
from google.genai import types as genai_types
from groq import Groq

from config import MagiConfig, StanceType, VerdictType


def _extract_text(response) -> str:
    """Extrai o texto de uma resposta Claude, ignorando blocos de thinking."""
    return "".join(b.text for b in response.content if b.type == "text")


def _extract_sources(response) -> list[str]:
    """Extrai os títulos das fontes consultadas pela busca web."""
    fontes = []
    for block in response.content:
        if block.type != "web_search_tool_result":
            continue
        # Sucesso devolve uma lista de resultados; erro devolve um objeto único.
        if isinstance(block.content, list):
            fontes.extend(
                t for r in block.content if (t := getattr(r, "title", None))
            )
    return fontes


@dataclass
class MagiResponse:
    """Resposta de um agente MAGI"""

    agent: str
    response: str
    stance: StanceType = StanceType.INFO
    failed: bool = False  # True quando a chamada à API falhou
    sources: list[str] = field(default_factory=list)  # fontes da busca web

    @property
    def alive(self) -> bool:
        """Um agente só participa da votação se realmente respondeu."""
        return not self.failed


@dataclass
class ConsensusResult:
    """Resultado final da deliberação"""

    verdict: VerdictType
    consensus_rate: float
    melchior_response: str
    balthasar_response: str
    gaspar_response: str
    final_recommendation: str
    reasoning: str
    stances: dict[str, StanceType]  # agente -> posição classificada
    live_agents: int  # quantos dos 3 responderam de fato
    vetoed: bool = False  # BALTHASAR bloqueou a aprovação
    sources: list[str] = field(default_factory=list)  # fontes que MELCHIOR consultou


class MagiSystem:
    """Sistema MAGI - Orquestração de 3 LLMs para decisão consensual"""

    def __init__(self, config: MagiConfig):
        self.config = config
        self.config.validate()

        # Inicializa clientes
        self.claude_client = anthropic.Anthropic(api_key=self.config.CLAUDE_API_KEY)
        self.gemini_client = genai.Client(api_key=self.config.GEMINI_API_KEY)
        self.groq_client = Groq(api_key=self.config.GROQ_API_KEY)

        # System prompts para cada agente
        self.system_prompts = self._initialize_system_prompts()

    # Contexto compartilhado: cada agente precisa saber que os outros dois existem,
    # senão inventa colegas inexistentes e tenta responder pelos três.
    _SHARED_CONTEXT = """O MAGI System delibera com exatamente três componentes, consultados
em paralelo e de forma independente:
- MELCHIOR — perspectiva científica e analítica
- BALTHASAR — perspectiva ética e humana
- GASPAR — perspectiva prática e executiva

Você é apenas UM desses três. Não responda pelos outros dois nem invente outros
componentes: as respostas deles são coletadas separadamente e consolidadas por um
motor de consenso. Dê somente a SUA perspectiva.

Ao final da sua análise, feche com uma linha começando por "POSIÇÃO:" declarando sua
recomendação — a favor, a favor com ressalvas, contra, ou que a questão não admite
recomendação."""

    def _initialize_system_prompts(self) -> dict:
        """Define os system prompts que definem a personalidade de cada agente"""
        return {
            "melchior": f"""Você é MELCHIOR, o componente científico e analítico do MAGI System.

{self._SHARED_CONTEXT}

Sua perspectiva é:
- Rigorosamente analítica e baseada em dados
- Pragmática e orientada para fatos verificáveis
- Cética de afirmações sem evidência
- Foca em lógica, causalidade e correlação

Analise a questão através desta lente científica, com raciocínio lógico explícito.
Seja conciso mas completo.

Você tem acesso a busca web. Use-a sempre que a resposta depender de dados atuais,
números concretos ou fatos verificáveis — você é o único componente do MAGI com essa
capacidade, e é isso que dá peso à sua perspectiva. Cite a fonte dos dados que trouxer.
Nunca invente números precisos para dar aparência de rigor: busque, ou declare a
incerteza explicitamente.""",

            "balthasar": f"""Você é BALTHASAR, o componente ético e humano do MAGI System.

{self._SHARED_CONTEXT}

Sua perspectiva é:
- Profundamente preocupada com implicações éticas e humanitárias
- Ponderada, cautelosa e focada em proteção
- Considera impacto em seres humanos, vulneráveis, e sociedade
- Valoriza segurança, justiça e bem comum acima de eficiência

Analise a questão considerando dimensões éticas e humanas.
Destaque riscos potenciais, dilemas morais e impactos não intencionais.
Seja empático mas mantendo clareza de pensamento.

Você tem poder de veto: se a questão envolver dano real a pessoas, ilegalidade ou
violação ética séria, sua POSIÇÃO deve ser "contra" — e isso bloqueia a aprovação
independentemente do que os outros dois componentes recomendem. Use esse peso com
responsabilidade: reserve o "contra" para riscos concretos, não para desconforto.""",

            "gaspar": f"""Você é GASPAR, o componente prático e inovador do MAGI System.

{self._SHARED_CONTEXT}

Sua perspectiva é:
- Foco em execução, resultados concretos e adaptabilidade
- Inovadora, criativa e focada em soluções que funcionam
- Pragmática sobre trade-offs entre ideais e realidade
- Orientada por velocidade, flexibilidade e resultado

Analise a questão buscando soluções práticas e viáveis.
Considere implementação, custos, prazos e viabilidade técnica.
Seja criativo mas realista sobre limitações do mundo real.""",
        }

    async def call_melchior(self, query: str) -> MagiResponse:
        """Chama Anthropic Claude com busca web (MELCHIOR - científico).

        Único componente com acesso a dados externos — por isso o papel analítico
        mora aqui e não no Gemini, cujo grounding exige plano pago.
        """
        try:
            kwargs = {
                "model": self.config.MELCHIOR_MODEL,
                "max_tokens": self.config.MAX_TOKENS,
                "system": self.system_prompts["melchior"],
            }
            if self.config.ENABLE_WEB_SEARCH:
                kwargs["tools"] = [
                    {
                        "type": "web_search_20260209",
                        "name": "web_search",
                        "max_uses": self.config.MAX_WEB_SEARCHES,
                    }
                ]

            messages = [{"role": "user", "content": query}]
            sources: list[str] = []

            # Uma rodada de busca longa pode parar com pause_turn: retomar em vez
            # de devolver uma resposta silenciosamente truncada.
            for _ in range(4):
                response = await asyncio.to_thread(
                    self.claude_client.messages.create, messages=messages, **kwargs
                )
                sources.extend(_extract_sources(response))
                if response.stop_reason != "pause_turn":
                    break
                messages = [
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": response.content},
                ]

            return MagiResponse(
                agent="MELCHIOR",
                response=_extract_text(response),
                sources=sources,
            )
        except Exception as e:
            return MagiResponse(
                agent="MELCHIOR",
                response=f"❌ Erro ao consultar: {str(e)}",
                stance=StanceType.ERROR,
                failed=True,
            )

    async def call_balthasar(self, query: str) -> MagiResponse:
        """Chama Google Gemini (BALTHASAR - ético)"""
        try:
            response = await asyncio.to_thread(
                self.gemini_client.models.generate_content,
                model=self.config.BALTHASAR_MODEL,
                contents=query,
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.system_prompts["balthasar"],
                    temperature=self.config.TEMPERATURE,
                    max_output_tokens=self.config.MAX_TOKENS,
                ),
            )
            texto = (response.text or "").strip()
            if not texto:
                # Resposta vazia (filtro de segurança, corte por tokens): é uma
                # falha real, não uma posição — não pode entrar na votação.
                raise RuntimeError(
                    f"resposta vazia do Gemini "
                    f"(finish_reason={response.candidates[0].finish_reason if response.candidates else '?'})"
                )
            return MagiResponse(agent="BALTHASAR", response=texto)
        except Exception as e:
            return MagiResponse(
                agent="BALTHASAR",
                response=f"❌ Erro ao consultar: {str(e)}",
                stance=StanceType.ERROR,
                failed=True,
            )

    async def call_gaspar(self, query: str) -> MagiResponse:
        """Chama Groq (GASPAR - prático)"""
        try:
            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.config.GASPAR_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompts["gaspar"],
                    },
                    {"role": "user", "content": query},
                ],
                temperature=self.config.TEMPERATURE,
                max_tokens=self.config.MAX_TOKENS,
            )
            return MagiResponse(
                agent="GASPAR", response=response.choices[0].message.content
            )
        except Exception as e:
            return MagiResponse(
                agent="GASPAR",
                response=f"❌ Erro ao consultar: {str(e)}",
                stance=StanceType.ERROR,
                failed=True,
            )

    async def deliberate(self, query: str) -> ConsensusResult:
        """Orquestra as 3 consultas em paralelo e consolida por votação de posições."""

        # Executa as 3 chamadas em paralelo. A ordem do gather é estável, então
        # cada índice corresponde sempre ao mesmo agente.
        raw = await asyncio.gather(
            self.call_melchior(query),
            self.call_balthasar(query),
            self.call_gaspar(query),
            return_exceptions=True,
        )

        # Uma exceção que escapou do handler ainda é uma falha daquele agente —
        # converter em ERROR no lugar, em vez de filtrar (filtrar desalinha os índices).
        agent_names = ("MELCHIOR", "BALTHASAR", "GASPAR")
        responses = [
            r
            if isinstance(r, MagiResponse)
            else MagiResponse(
                agent=name,
                response=f"❌ Falha inesperada: {r}",
                stance=StanceType.ERROR,
                failed=True,
            )
            for name, r in zip(agent_names, raw)
        ]

        # Classifica a posição de cada agente que respondeu
        await self._classify_stances(query, responses)

        verdict, consensus_rate, vetoed, reasoning = self._consolidate(responses)

        final_recommendation = await self._synthesize_recommendation(
            query, responses, verdict, consensus_rate, vetoed
        )

        return ConsensusResult(
            verdict=verdict,
            consensus_rate=consensus_rate,
            melchior_response=responses[0].response,
            balthasar_response=responses[1].response,
            gaspar_response=responses[2].response,
            final_recommendation=final_recommendation,
            reasoning=reasoning,
            stances={r.agent: r.stance for r in responses},
            live_agents=sum(1 for r in responses if r.alive),
            vetoed=vetoed,
            sources=responses[0].sources,
        )

    async def _classify_stances(
        self, query: str, responses: list[MagiResponse]
    ) -> None:
        """Classifica a posição de cada resposta, in-place.

        Roda num modelo de família distinta dos três agentes (ver JUDGE_MODEL):
        BALTHASAR tem poder de veto, então não pode ser o provedor que classifica
        a própria posição. Substitui a heurística antiga de variância de
        comprimento, que reportava "consenso" entre mensagens de erro.
        """
        live = [r for r in responses if r.alive]
        if not live:
            return

        blocks = "\n\n".join(
            f"<resposta agente=\"{r.agent}\">\n{r.response[:4000]}\n</resposta>"
            for r in live
        )
        prompt = f"""Questão submetida ao MAGI System:
{query}

Abaixo estão as respostas dos componentes. Para cada um, classifique a POSIÇÃO que
ele efetivamente defende — não a qualidade nem o tom da resposta.

Categorias:
- YES: recomenda a favor, sem ressalvas materiais
- CONDITIONAL: recomenda a favor, mas condicionado a salvaguardas concretas
- NO: recomenda contra
- INFO: analisa a questão sem tomar posição, ou a questão não admite recomendação

Se o agente escreveu uma linha "POSIÇÃO:", use-a como sinal principal.

{blocks}"""

        prompt += """

Responda SOMENTE com JSON, sem texto ao redor, neste formato:
{"classificacoes": [{"agente": "MELCHIOR", "posicao": "YES"}]}"""

        try:
            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.config.JUDGE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,  # classificação deve ser determinística
                max_tokens=1024,
            )
            data = json.loads(response.choices[0].message.content)
            by_agent = {c["agente"]: c["posicao"] for c in data["classificacoes"]}
            for r in live:
                if r.agent in by_agent:
                    r.stance = StanceType(by_agent[r.agent])
        except Exception:
            # Juiz indisponível: manter INFO. Isso leva a CONDITIONAL_PASS em vez
            # de fabricar um consenso que não foi medido.
            pass

    def _consolidate(
        self, responses: list[MagiResponse]
    ) -> tuple[VerdictType, float, bool, str]:
        """Consolida as posições em veredito, taxa de concordância e veto.

        Ordem de prioridade inspirada em TomaszRewak/MAGI: falhas e recusas pesam
        mais do que aprovações — um "não" não é diluído por dois "sim".
        """
        live = [r for r in responses if r.alive]
        dead = [r for r in responses if not r.alive]

        # Sem quórum: não há deliberação possível
        if len(live) < 2:
            nomes = ", ".join(r.agent for r in dead)
            return (
                VerdictType.CODE_RED,
                0.0,
                False,
                f"⛔ Quórum insuficiente: apenas {len(live)} de 3 componentes responderam. "
                f"Falhas em {nomes}. Nenhum veredito é válido com o sistema degradado.",
            )

        counts: dict[StanceType, int] = {}
        for r in live:
            counts[r.stance] = counts.get(r.stance, 0) + 1

        modal_stance = max(counts, key=lambda s: counts[s])
        consensus_rate = counts[modal_stance] / len(live)

        # Veto ético do BALTHASAR: um "contra" dele bloqueia aprovação
        balthasar = next((r for r in live if r.agent == "BALTHASAR"), None)
        vetoed = balthasar is not None and balthasar.stance is StanceType.NO

        degraded = (
            f" (⚠️ sistema degradado: {', '.join(r.agent for r in dead)} não respondeu)"
            if dead
            else ""
        )
        placar = ", ".join(f"{r.agent}={r.stance.label}" for r in live)

        if vetoed:
            return (
                VerdictType.CODE_RED,
                consensus_rate,
                True,
                f"🔴 VETO ÉTICO — BALTHASAR se posiciona contra. Aprovação bloqueada "
                f"independentemente dos demais. Placar: {placar}.{degraded}",
            )

        if counts.get(StanceType.NO):
            return (
                VerdictType.CODE_RED,
                consensus_rate,
                False,
                f"🔴 Objeção registrada — ao menos um componente se posiciona contra. "
                f"Requer análise manual. Placar: {placar}.{degraded}",
            )

        unanime = counts[modal_stance] == len(live)

        if unanime and modal_stance is StanceType.YES:
            verdict = VerdictType.DELIBERATION_PASS
            texto = f"✅ Consenso unânime favorável entre os {len(live)} componentes ativos."
        elif modal_stance in (StanceType.YES, StanceType.CONDITIONAL) and (
            consensus_rate >= self.config.CONSENSUS_THRESHOLD
        ):
            verdict = VerdictType.CONDITIONAL_PASS
            texto = (
                f"⚠️ Maioria favorável ({consensus_rate:.0%}), mas com ressalvas ou "
                f"divergência de grau. Revisar as condições antes de agir."
            )
        elif modal_stance is StanceType.INFO and unanime:
            verdict = VerdictType.CONDITIONAL_PASS
            texto = (
                "ℹ️ Os componentes tratam a questão como analítica e não emitem "
                "recomendação. Não há aprovação a conceder — leia as perspectivas."
            )
        else:
            verdict = VerdictType.DIVERGENCE
            texto = (
                f"💥 Posições fundamentalmente divergentes (concordância de apenas "
                f"{consensus_rate:.0%}). Escalação recomendada."
            )

        return verdict, consensus_rate, False, f"{texto} Placar: {placar}.{degraded}"

    async def _synthesize_recommendation(
        self,
        query: str,
        responses: list[MagiResponse],
        verdict: VerdictType,
        consensus_rate: float,
        vetoed: bool,
    ) -> str:
        """Sintetiza a recomendação final, respeitando o veredito já apurado."""
        live = [r for r in responses if r.alive]
        if len(live) < 2:
            return (
                "Sistema degradado — sem quórum para deliberar. "
                "Verifique as chaves de API e o status dos provedores."
            )

        blocks = "\n\n".join(
            f"{r.agent} [{r.stance.value}]:\n{r.response[:1500]}" for r in live
        )

        if vetoed:
            instrucao = (
                "BALTHASAR exerceu VETO ÉTICO. Sua síntese NÃO pode recomendar prosseguir. "
                "Explique em 2-3 frases qual é a objeção ética e o que teria de mudar "
                "para a questão ser reconsiderada."
            )
        elif verdict is VerdictType.DIVERGENCE:
            instrucao = (
                "Os componentes divergem fundamentalmente. NÃO force um meio-termo artificial: "
                "explique em 2-3 frases qual é o trade-off real em disputa e que informação "
                "resolveria o impasse."
            )
        else:
            instrucao = (
                "Sintetize o melhor de cada perspectiva em 2-3 frases, preservando as "
                "ressalvas materiais que os componentes levantaram."
            )

        synthesis_prompt = f"""Questão: "{query}"

Perspectivas dos componentes ativos (com a posição apurada entre colchetes):

{blocks}

Veredito do motor de consenso: {verdict.value} (concordância {consensus_rate:.0%})

{instrucao}"""

        try:
            response = await asyncio.to_thread(
                self.claude_client.messages.create,
                model=self.config.SYNTHESIS_MODEL,
                max_tokens=4096,
                messages=[{"role": "user", "content": synthesis_prompt}],
            )
            return _extract_text(response)
        except Exception as e:
            return f"Recomendação sintética indisponível: {str(e)}"


async def main():
    """Função de teste do sistema"""
    config = MagiConfig()
    magi = MagiSystem(config)

    query = "Qual é o impacto potencial da IA generativa nas profissões de conhecimento?"

    print("🌍 MAGI System iniciando deliberação...")
    print(f"📋 Questão: {query}\n")

    result = await magi.deliberate(query)

    print(f"[MELCHIOR - Científico]\n{result.melchior_response}\n")
    print(f"[BALTHASAR - Ético]\n{result.balthasar_response}\n")
    print(f"[GASPAR - Prático]\n{result.gaspar_response}\n")
    print(f"📊 Taxa de Consenso: {result.consensus_rate:.1%}")
    print(f"🎯 Veredito: {result.verdict.value}")
    print(f"💡 Recomendação Final:\n{result.final_recommendation}")


if __name__ == "__main__":
    asyncio.run(main())
