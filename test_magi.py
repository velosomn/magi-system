"""Testes para o MAGI System"""

import pytest
import asyncio
from config import MagiConfig, StanceType, VerdictType
from magi_core import MagiSystem, MagiResponse


def _engine() -> MagiSystem:
    """Instância sem __init__ — testa a lógica pura sem exigir chaves de API."""
    sistema = MagiSystem.__new__(MagiSystem)
    sistema.config = MagiConfig()
    return sistema


def _resp(agent: str, stance: StanceType, failed: bool = False) -> MagiResponse:
    return MagiResponse(agent=agent, response="...", stance=stance, failed=failed)


class TestConsolidacao:
    """O motor de consenso: a lógica que decide o veredito.

    O primeiro teste cobre a regressão que motivou a reescrita: a versão
    anterior media variância de comprimento e reportava 94% de 'consenso'
    quando os três agentes tinham falhado com erro de API.
    """

    def test_tres_falhas_nao_viram_consenso(self):
        verdict, rate, vetoed, _ = _engine()._consolidate(
            [
                _resp("MELCHIOR", StanceType.ERROR, failed=True),
                _resp("BALTHASAR", StanceType.ERROR, failed=True),
                _resp("GASPAR", StanceType.ERROR, failed=True),
            ]
        )
        assert verdict is VerdictType.CODE_RED
        assert rate == 0.0
        assert not vetoed

    def test_sem_quorum_com_apenas_um_vivo(self):
        verdict, _, _, reasoning = _engine()._consolidate(
            [
                _resp("MELCHIOR", StanceType.ERROR, failed=True),
                _resp("BALTHASAR", StanceType.YES),
                _resp("GASPAR", StanceType.ERROR, failed=True),
            ]
        )
        assert verdict is VerdictType.CODE_RED
        assert "Quórum insuficiente" in reasoning

    def test_unanime_favoravel_aprova(self):
        verdict, rate, _, _ = _engine()._consolidate(
            [
                _resp("MELCHIOR", StanceType.YES),
                _resp("BALTHASAR", StanceType.YES),
                _resp("GASPAR", StanceType.YES),
            ]
        )
        assert verdict is VerdictType.DELIBERATION_PASS
        assert rate == 1.0

    def test_veto_do_balthasar_vence_maioria(self):
        verdict, _, vetoed, reasoning = _engine()._consolidate(
            [
                _resp("MELCHIOR", StanceType.YES),
                _resp("BALTHASAR", StanceType.NO),
                _resp("GASPAR", StanceType.YES),
            ]
        )
        assert verdict is VerdictType.CODE_RED
        assert vetoed
        assert "VETO" in reasoning

    def test_objecao_de_agente_sem_veto_bloqueia_sem_ser_veto(self):
        verdict, _, vetoed, _ = _engine()._consolidate(
            [
                _resp("MELCHIOR", StanceType.YES),
                _resp("BALTHASAR", StanceType.YES),
                _resp("GASPAR", StanceType.NO),
            ]
        )
        assert verdict is VerdictType.CODE_RED
        assert not vetoed  # só BALTHASAR tem poder de veto

    def test_maioria_condicional(self):
        verdict, _, _, _ = _engine()._consolidate(
            [
                _resp("MELCHIOR", StanceType.CONDITIONAL),
                _resp("BALTHASAR", StanceType.CONDITIONAL),
                _resp("GASPAR", StanceType.YES),
            ]
        )
        assert verdict is VerdictType.CONDITIONAL_PASS

    def test_posicoes_totalmente_divididas(self):
        verdict, rate, _, _ = _engine()._consolidate(
            [
                _resp("MELCHIOR", StanceType.YES),
                _resp("BALTHASAR", StanceType.INFO),
                _resp("GASPAR", StanceType.CONDITIONAL),
            ]
        )
        assert verdict is VerdictType.DIVERGENCE
        assert rate == pytest.approx(1 / 3)

    def test_quorum_minimo_de_dois(self):
        verdict, _, _, reasoning = _engine()._consolidate(
            [
                _resp("MELCHIOR", StanceType.YES),
                _resp("BALTHASAR", StanceType.YES),
                _resp("GASPAR", StanceType.ERROR, failed=True),
            ]
        )
        assert verdict is VerdictType.DELIBERATION_PASS
        assert "degradado" in reasoning  # a falha do GASPAR fica visível


@pytest.fixture
def config():
    """Fixture de configuração para testes"""
    return MagiConfig()


@pytest.fixture
def magi_system(config):
    """Fixture do sistema MAGI"""
    # Nota: testes de integração requerem API keys configuradas
    # Em ambiente de CI, usar mocks ou testes unitários apenas
    try:
        return MagiSystem(config)
    except ValueError:
        pytest.skip("API keys não configuradas")


class TestMagiResponse:
    """Testes para a estrutura MagiResponse"""

    def test_magi_response_creation(self):
        """Testa criação de MagiResponse"""
        response = MagiResponse(agent="MELCHIOR", response="Test response")
        assert response.agent == "MELCHIOR"
        assert response.response == "Test response"

    def test_resposta_normal_participa_da_votacao(self):
        assert MagiResponse(agent="BALTHASAR", response="Test").alive

    def test_resposta_com_falha_nao_participa(self):
        falha = MagiResponse(
            agent="BALTHASAR",
            response="❌ Erro",
            stance=StanceType.ERROR,
            failed=True,
        )
        assert not falha.alive


class TestMagiConfig:
    """Testes para configuração"""

    def test_config_creation(self):
        """Testa criação de configuração"""
        config = MagiConfig()
        assert config.TEMPERATURE == 0.7
        assert config.MAX_TOKENS == 8192

    def test_consensus_threshold(self):
        """Testa threshold de consenso"""
        config = MagiConfig()
        assert config.CONSENSUS_THRESHOLD == 0.66
        assert config.DIVERGENCE_THRESHOLD == 0.33

    def test_juiz_e_de_familia_distinta_dos_agentes(self):
        """O juiz classifica a posição de quem tem poder de veto.

        Se rodasse no mesmo provedor de um agente, esse agente classificaria
        a própria posição.
        """
        config = MagiConfig()
        agentes = {
            config.MELCHIOR_MODEL,
            config.BALTHASAR_MODEL,
            config.GASPAR_MODEL,
        }
        assert config.JUDGE_MODEL not in agentes


class TestVerdictType:
    """Testes para tipos de veredito"""

    def test_all_verdicts_exist(self):
        """Verifica se todos os vereditos existem"""
        verdicts = [
            VerdictType.DELIBERATION_PASS,
            VerdictType.CONDITIONAL_PASS,
            VerdictType.CODE_RED,
            VerdictType.DIVERGENCE,
        ]
        assert len(verdicts) == 4

    def test_verdict_values(self):
        """Testa valores dos vereditos"""
        assert VerdictType.DELIBERATION_PASS.value == "DELIBERATION_PASS"
        assert VerdictType.CONDITIONAL_PASS.value == "CONDITIONAL_PASS"
        assert VerdictType.CODE_RED.value == "CODE_RED"
        assert VerdictType.DIVERGENCE.value == "DIVERGENCE"


class TestSystemPrompts:
    """Testes para system prompts"""

    def test_all_system_prompts_present(self, magi_system):
        """Verifica se todos os prompts estão presentes"""
        agents = ["melchior", "balthasar", "gaspar"]
        for agent in agents:
            assert agent in magi_system.system_prompts
            assert len(magi_system.system_prompts[agent]) > 100

    def test_melchior_prompt_mentions_science(self, magi_system):
        """Verifica se prompt MELCHIOR menciona ciência"""
        prompt = magi_system.system_prompts["melchior"]
        assert "científico" in prompt.lower() or "scientific" in prompt.lower()

    def test_balthasar_prompt_mentions_ethics(self, magi_system):
        """Verifica se prompt BALTHASAR menciona ética"""
        prompt = magi_system.system_prompts["balthasar"]
        assert "ético" in prompt.lower() or "ethical" in prompt.lower()

    def test_gaspar_prompt_mentions_practical(self, magi_system):
        """Verifica se prompt GASPAR menciona pragmatismo"""
        prompt = magi_system.system_prompts["gaspar"]
        assert "prático" in prompt.lower() or "practical" in prompt.lower()

    def test_todo_agente_conhece_os_colegas(self, magi_system):
        """Sem isso, um agente inventa colegas e responde pelos três.

        Regressão observada: o GASPAR anunciou "as 3 perspectivas: GASPAR,
        LUNA e SOL" porque o prompt não nomeava os outros dois componentes.
        """
        for agente in ("melchior", "balthasar", "gaspar"):
            prompt = magi_system.system_prompts[agente]
            for colega in ("MELCHIOR", "BALTHASAR", "GASPAR"):
                assert colega in prompt, f"{agente} não conhece {colega}"

    def test_todo_agente_declara_posicao(self, magi_system):
        """O juiz usa a linha POSIÇÃO: como sinal principal de classificação."""
        for agente in ("melchior", "balthasar", "gaspar"):
            assert "POSIÇÃO:" in magi_system.system_prompts[agente]

    def test_apenas_balthasar_tem_veto(self, magi_system):
        assert "veto" in magi_system.system_prompts["balthasar"].lower()
        for agente in ("melchior", "gaspar"):
            assert "veto" not in magi_system.system_prompts[agente].lower()


# Testes de integração (requerem API keys)
class TestIntegration:
    """Testes de integração com APIs reais"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_melchior_call(self, magi_system):
        """Testa chamada a Claude com busca web (MELCHIOR)"""
        response = await magi_system.call_melchior("Quanto é 2+2?")
        assert response.agent == "MELCHIOR"
        assert len(response.response) > 0
        assert not response.failed

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_melchior_busca_dados_atuais(self, magi_system):
        """A busca web é o que justifica MELCHIOR morar no Claude."""
        response = await magi_system.call_melchior(
            "Qual a taxa Selic atual no Brasil? Cite a fonte."
        )
        assert not response.failed
        assert response.sources, "nenhuma fonte consultada — a busca não acionou"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_balthasar_call(self, magi_system):
        """Testa chamada a Gemini (BALTHASAR)"""
        response = await magi_system.call_balthasar("Quanto é 2+2?")
        assert response.agent == "BALTHASAR"
        assert len(response.response) > 0
        assert not response.failed

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_gaspar_call(self, magi_system):
        """Testa chamada a Groq Llama (GASPAR)"""
        response = await magi_system.call_gaspar("Quanto é 2+2?")
        assert response.agent == "GASPAR"
        assert len(response.response) > 0
        assert not response.failed

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_juiz_classifica_posicoes(self, magi_system):
        """O juiz precisa extrair posições reais, não devolver INFO por padrão."""
        responses = [
            MagiResponse(agent="MELCHIOR", response="Os dados apoiam. POSIÇÃO: a favor."),
            MagiResponse(
                agent="BALTHASAR",
                response="Risco sério de dano a vulneráveis. POSIÇÃO: contra.",
            ),
            MagiResponse(
                agent="GASPAR",
                response="Viável, mas só com auditoria. POSIÇÃO: a favor com ressalvas.",
            ),
        ]
        await magi_system._classify_stances("Devemos prosseguir?", responses)
        assert responses[0].stance is StanceType.YES
        assert responses[1].stance is StanceType.NO
        assert responses[2].stance is StanceType.CONDITIONAL

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_deliberate_integration(self, magi_system):
        """Testa deliberação completa"""
        result = await magi_system.deliberate("Quanto é 2+2?")

        assert result.melchior_response
        assert result.balthasar_response
        assert result.gaspar_response
        assert 0 <= result.consensus_rate <= 1
        assert result.verdict in VerdictType
        assert result.final_recommendation
        assert result.live_agents == 3, "algum componente falhou"
        assert set(result.stances) == {"MELCHIOR", "BALTHASAR", "GASPAR"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
