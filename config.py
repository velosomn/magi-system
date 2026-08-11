"""MAGI System Configuration"""

from dataclasses import dataclass
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()


class VerdictType(Enum):
    """Decisão final do MAGI System"""
    DELIBERATION_PASS = "DELIBERATION_PASS"
    CONDITIONAL_PASS = "CONDITIONAL_PASS"
    CODE_RED = "CODE_RED"
    DIVERGENCE = "DIVERGENCE"


class StanceType(Enum):
    """Posição extraída da resposta de um agente.

    Ordenados por prioridade de consolidação (inspirado em TomaszRewak/MAGI):
    um ERROR ou um NO pesam mais do que dois YES.
    """
    ERROR = "ERROR"              # O agente não respondeu (falha de API)
    NO = "NO"                    # Recomenda contra
    CONDITIONAL = "CONDITIONAL"  # Recomenda a favor, com ressalvas
    YES = "YES"                  # Recomenda a favor
    INFO = "INFO"                # Análise informativa, sem recomendação

    @property
    def label(self) -> str:
        return {
            "ERROR": "⛔ falha",
            "NO": "🔴 contra",
            "CONDITIONAL": "⚠️ condicional",
            "YES": "✅ favorável",
            "INFO": "ℹ️ informativo",
        }[self.value]


@dataclass
class MagiConfig:
    """Configuração centralizada do MAGI System"""

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Mapeamento papel -> modelo (verificado via API em 2026-08-11).
    #
    # MELCHIOR usa Claude porque é o único provedor cuja busca web funciona nesta
    # conta: o grounding do Gemini exige plano pago (retorna 429 no free tier).
    # O papel "orientado a dados" precisa de acesso a dados.
    MELCHIOR_MODEL: str = "claude-opus-5"          # Anthropic — com busca web
    BALTHASAR_MODEL: str = "gemini-3.5-flash"      # Google
    GASPAR_MODEL: str = "llama-3.3-70b-versatile"  # Groq

    # O juiz classifica as posições dos três. Fica num modelo de família distinta
    # dos agentes (nem Claude, nem Gemini, nem Llama) para que nenhum componente
    # classifique a própria posição — BALTHASAR tem poder de veto.
    JUDGE_MODEL: str = "openai/gpt-oss-120b"       # Groq

    # A síntese final roda no Claude, mas depois do veredito já apurado
    SYNTHESIS_MODEL: str = "claude-opus-5"

    # Busca web do MELCHIOR (server-side tool da Anthropic — cobrada por uso)
    ENABLE_WEB_SEARCH: bool = True
    # 4 era baixo: o MELCHIOR esgotava o limite e narrava "a busca falhou"
    # mesmo tendo consultado dezenas de fontes antes do corte.
    MAX_WEB_SEARCHES: int = 10

    # Temperature & Parâmetros
    TEMPERATURE: float = 0.7  # Gemini e Groq apenas — claude-opus-5 rejeita este parâmetro
    MAX_TOKENS: int = 8192

    # Limites de Consenso
    CONSENSUS_THRESHOLD: float = 0.66  # 2 de 3 = consenso
    DIVERGENCE_THRESHOLD: float = 0.33  # 1 de 3 = divergência alta

    # Timeouts
    API_TIMEOUT: int = 30
    TOTAL_TIMEOUT: int = 60

    def validate(self) -> bool:
        """Valida se todas as API keys estão configuradas"""
        required_keys = [self.GEMINI_API_KEY, self.CLAUDE_API_KEY, self.GROQ_API_KEY]
        missing = [key for key in required_keys if not key]

        if missing:
            raise ValueError(
                f"❌ API Keys faltando. Configure todas as keys no arquivo .env\n"
                f"   Variáveis requeridas: GEMINI_API_KEY, CLAUDE_API_KEY, GROQ_API_KEY"
            )
        return True
