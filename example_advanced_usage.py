"""
Exemplos Avançados de Uso do MAGI System
Demonstra como usar o sistema programaticamente em diferentes contextos
"""

import asyncio
import json
from config import MagiConfig, VerdictType
from magi_core import MagiSystem


# ==============================================================================
# EXEMPLO 1: Uso Básico Programático
# ==============================================================================
async def example_basic_usage():
    """Uso básico: deliberar sobre uma questão"""
    print("\n" + "=" * 70)
    print("EXEMPLO 1: Uso Básico Programático")
    print("=" * 70 + "\n")

    config = MagiConfig()
    magi = MagiSystem(config)

    query = "Qual é o futuro do trabalho remoto?"
    result = await magi.deliberate(query)

    print(f"Query: {query}")
    print(f"Consenso: {result.consensus_rate:.1%}")
    print(f"Veredito: {result.verdict.value}")
    print(f"\nRecomendação:\n{result.final_recommendation}")


# ==============================================================================
# EXEMPLO 2: Batch Processing
# ==============================================================================
async def example_batch_processing():
    """Processar múltiplas questões em sequência"""
    print("\n" + "=" * 70)
    print("EXEMPLO 2: Batch Processing de Múltiplas Questões")
    print("=" * 70 + "\n")

    config = MagiConfig()
    magi = MagiSystem(config)

    queries = [
        "A IA substituirá os desenvolvedores de software?",
        "Como as empresas devem se preparar para economia digital?",
        "Qual é o futuro dos bancos tradicionais?",
    ]

    results = []
    for i, query in enumerate(queries, 1):
        print(f"Processando questão {i}/{len(queries)}: {query[:50]}...")
        result = await magi.deliberate(query)
        results.append(
            {
                "query": query,
                "consensus": result.consensus_rate,
                "verdict": result.verdict.value,
            }
        )

    # Análise agregada
    print("\n📊 RESUMO DOS RESULTADOS:")
    print("-" * 70)
    avg_consensus = sum(r["consensus"] for r in results) / len(results)
    print(f"Consenso Médio: {avg_consensus:.1%}")

    verdicts_count = {}
    for r in results:
        verdict = r["verdict"]
        verdicts_count[verdict] = verdicts_count.get(verdict, 0) + 1

    print(f"Distribuição de Vereditos: {verdicts_count}")


# ==============================================================================
# EXEMPLO 3: Análise de Perspectivas Individuais
# ==============================================================================
async def example_individual_perspectives():
    """Analisar perspectivas individuais sem síntese"""
    print("\n" + "=" * 70)
    print("EXEMPLO 3: Análise de Perspectivas Individuais")
    print("=" * 70 + "\n")

    config = MagiConfig()
    magi = MagiSystem(config)

    query = "Qual é o principal desafio da IA generativa?"

    # Chamar agentes individualmente para mais controle
    melchior = await magi.call_melchior(query)
    balthasar = await magi.call_balthasar(query)
    gaspar = await magi.call_gaspar(query)

    print(f"Questão: {query}\n")

    print("🔬 PERSPECTIVA CIENTÍFICA (MELCHIOR):")
    print(melchior.response[:500] + "...\n")

    print("⚖️ PERSPECTIVA ÉTICA (BALTHASAR):")
    print(balthasar.response[:500] + "...\n")

    print("⚡ PERSPECTIVA PRÁTICA (GASPAR):")
    print(gaspar.response[:500] + "...\n")


# ==============================================================================
# EXEMPLO 4: Filtro por Veredito
# ==============================================================================
async def example_filter_by_verdict():
    """Processa queries até encontrar um veredito específico"""
    print("\n" + "=" * 70)
    print("EXEMPLO 4: Filtro por Tipo de Veredito")
    print("=" * 70 + "\n")

    config = MagiConfig()
    magi = MagiSystem(config)

    queries = [
        "Qual é o melhor editor de código para Python?",
        "Como implementar testes em aplicações de ML?",
        "Qual é a linguagem de programação do futuro?",
        "Devo usar TypeScript ou Python para backend?",
    ]

    # Procura por vereditos de forte consenso
    strong_consensus_queries = []

    for query in queries:
        result = await magi.deliberate(query)
        if result.verdict == VerdictType.DELIBERATION_PASS:
            strong_consensus_queries.append(
                {"query": query, "consensus": result.consensus_rate}
            )

    print(f"Questões com FORTE CONSENSO (≥66%):")
    for item in strong_consensus_queries:
        print(f"  • {item['query']} [{item['consensus']:.1%}]")


# ==============================================================================
# EXEMPLO 5: JSON Export para Análise
# ==============================================================================
async def example_json_export():
    """Exportar resultados em JSON para análise/integração"""
    print("\n" + "=" * 70)
    print("EXEMPLO 5: Export para JSON")
    print("=" * 70 + "\n")

    config = MagiConfig()
    magi = MagiSystem(config)

    query = "Como as startups podem competir com Big Tech?"
    result = await magi.deliberate(query)

    # Estruturar resultado para JSON
    export_data = {
        "query": query,
        "timestamp": "2024-08-10T10:30:00Z",
        "consensus": {
            "rate": round(result.consensus_rate, 3),
            "threshold": config.CONSENSUS_THRESHOLD,
        },
        "verdict": {
            "type": result.verdict.value,
            "reasoning": result.reasoning,
        },
        "perspectives": {
            "melchior_scientific": result.melchior_response[:300],
            "balthasar_ethical": result.balthasar_response[:300],
            "gaspar_practical": result.gaspar_response[:300],
        },
        "synthesis": result.final_recommendation,
    }

    # Pretty print JSON
    print(json.dumps(export_data, indent=2, ensure_ascii=False))

    # Opcional: salvar em arquivo
    with open("magi_result.json", "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    print("\n✅ Resultado exportado para magi_result.json")


# ==============================================================================
# EXEMPLO 6: Convergência de Perspectivas
# ==============================================================================
async def example_convergence_analysis():
    """Analisar como as perspectivas convergem ou divergem"""
    print("\n" + "=" * 70)
    print("EXEMPLO 6: Análise de Convergência de Perspectivas")
    print("=" * 70 + "\n")

    config = MagiConfig()
    magi = MagiSystem(config)

    query = "A criptografia deve ter backdoors para lei e ordem?"

    # Questão que naturalmente divide perspectivas
    result = await magi.deliberate(query)

    print(f"Questão: {query}\n")
    print(f"Taxa de Convergência: {result.consensus_rate:.1%}\n")

    if result.verdict == VerdictType.DIVERGENCE:
        print("💥 PERSPECTIVAS ALTAMENTE DIVERGENTES")
        print("\nEste é um tópico onde os três agentes fundamentalmente discordam.")
        print("Cada perspectiva representa um trade-off válido:\n")

        print("🔬 MELCHIOR: Enfoque em eficiência técnica e dados")
        print(f"   {result.melchior_response[:250]}...\n")

        print("⚖️ BALTHASAR: Enfoque em proteção e direitos humanos")
        print(f"   {result.balthasar_response[:250]}...\n")

        print("⚡ GASPAR: Enfoque em implementação e compromissos práticos")
        print(f"   {result.gaspar_response[:250]}...\n")

    elif result.verdict == VerdictType.DELIBERATION_PASS:
        print("✅ FORTE CONSENSO")
        print("Os três agentes convergem em recomendação similar.")
    else:
        print(f"⚠️ {result.verdict.value}")


# ==============================================================================
# EXEMPLO 7: Monitoramento de Qualidade de Respostas
# ==============================================================================
async def example_quality_monitoring():
    """Monitorar qualidade das respostas"""
    print("\n" + "=" * 70)
    print("EXEMPLO 7: Monitoramento de Qualidade")
    print("=" * 70 + "\n")

    config = MagiConfig()
    magi = MagiSystem(config)

    query = "Qual é a melhor estratégia de marketing digital para 2024?"
    result = await magi.deliberate(query)

    # Análise de qualidade
    metrics = {
        "query_length": len(query),
        "melchior_response_length": len(result.melchior_response),
        "balthasar_response_length": len(result.balthasar_response),
        "gaspar_response_length": len(result.gaspar_response),
        "synthesis_length": len(result.final_recommendation),
        "consensus_rate": result.consensus_rate,
        "has_errors": any(
            "erro" in resp.lower() or "error" in resp.lower()
            for resp in [
                result.melchior_response,
                result.balthasar_response,
                result.gaspar_response,
            ]
        ),
    }

    print("📊 MÉTRICAS DE QUALIDADE:")
    print("-" * 70)
    for metric, value in metrics.items():
        print(f"  {metric}: {value}")

    # Validações
    print("\n✓ VALIDAÇÕES:")
    if metrics["melchior_response_length"] > 100:
        print("  ✓ MELCHIOR forneceu resposta significativa")
    if metrics["balthasar_response_length"] > 100:
        print("  ✓ BALTHASAR forneceu resposta significativa")
    if metrics["gaspar_response_length"] > 100:
        print("  ✓ GASPAR forneceu resposta significativa")
    if not metrics["has_errors"]:
        print("  ✓ Nenhum erro detectado nas respostas")
    if metrics["consensus_rate"] > 0.5:
        print("  ✓ Nível de consenso aceitável")


# ==============================================================================
# EXEMPLO 8: Iteração/Refinamento
# ==============================================================================
async def example_iterative_refinement():
    """Refinar uma questão através de iterações"""
    print("\n" + "=" * 70)
    print("EXEMPLO 8: Refinamento Iterativo")
    print("=" * 70 + "\n")

    config = MagiConfig()
    magi = MagiSystem(config)

    # Começar com questão geral
    query1 = "Como implementar IA na empresa?"
    result1 = await magi.deliberate(query1)
    print(f"Round 1: {query1}")
    print(f"Consenso: {result1.consensus_rate:.1%}\n")

    # Refinar baseado em resultado
    if result1.consensus_rate < 0.7:
        query2 = "Como implementar IA em uma empresa de varejo e-commerce de médio porte?"
        result2 = await magi.deliberate(query2)
        print(f"Round 2 (Refinada): {query2}")
        print(f"Consenso: {result2.consensus_rate:.1%}\n")

        # Refinar ainda mais se necessário
        if result2.consensus_rate < 0.75:
            query3 = (
                "Qual é a primeira aplicação de IA que uma empresa de e-commerce "
                "deve implementar: otimização de recomendações ou automação de suporte?"
            )
            result3 = await magi.deliberate(query3)
            print(f"Round 3 (Muito Refinada): {query3}")
            print(f"Consenso: {result3.consensus_rate:.1%}\n")
            print(f"Recomendação Final:\n{result3.final_recommendation}")


# ==============================================================================
# MAIN: Executar Exemplos
# ==============================================================================
async def main():
    """Executar todos os exemplos"""

    examples = [
        ("1", "Uso Básico", example_basic_usage),
        ("2", "Batch Processing", example_batch_processing),
        ("3", "Perspectivas Individuais", example_individual_perspectives),
        ("4", "Filtro por Veredito", example_filter_by_verdict),
        ("5", "Export JSON", example_json_export),
        ("6", "Análise de Convergência", example_convergence_analysis),
        ("7", "Monitoramento de Qualidade", example_quality_monitoring),
        ("8", "Refinamento Iterativo", example_iterative_refinement),
    ]

    print("\n🎯 EXEMPLOS AVANÇADOS DE USO DO MAGI SYSTEM")
    print("=" * 70)
    print("\nEscolha um exemplo para executar:")
    for num, name, _ in examples:
        print(f"  {num}. {name}")
    print("  0. Executar Todos")
    print("  q. Sair")

    choice = input("\nSua escolha: ").strip().lower()

    if choice == "q":
        print("Saindo...")
        return

    if choice == "0":
        for _, _, example_func in examples:
            try:
                await example_func()
            except Exception as e:
                print(f"❌ Erro ao executar exemplo: {e}")
    else:
        for num, _, example_func in examples:
            if choice == num:
                try:
                    await example_func()
                except Exception as e:
                    print(f"❌ Erro: {e}")
                break


if __name__ == "__main__":
    asyncio.run(main())
