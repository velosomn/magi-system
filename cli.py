"""MAGI System CLI - Interface de Linha de Comando com estilo NERV/Evangelion"""

import asyncio
import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from config import MagiConfig
from magi_core import MagiSystem

# Cores do tema NERV/Evangelion
NERV_PURPLE = "#A020F0"
NERV_GREEN = "#00FF00"
NERV_RED = "#FF0000"
NERV_CYAN = "#00FFFF"
NERV_YELLOW = "#FFFF00"

console = Console()


def print_banner():
    """Banner ASCII no estilo Evangelion/NERV"""
    banner = """
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║         ███╗   ███╗ █████╗  ██████╗ ██╗                   ║
    ║         ████╗ ████║██╔══██╗██╔════╝ ██║                   ║
    ║         ██╔████╔██║███████║██║  ███╗██║                   ║
    ║         ██║╚██╔╝██║██╔══██║██║   ██║██║                   ║
    ║         ██║ ╚═╝ ██║██║  ██║╚██████╔╝██║                   ║
    ║         ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝                   ║
    ║                                                            ║
    ║           MULTI-AGENT AI GOVERNANCE INTERFACE              ║
    ║                                                            ║
    ║    Integrated Consensus Engine v2.1                       ║
    ║    Three-Agent Deliberation System                        ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style=NERV_PURPLE)


def print_section_header(title: str, icon: str = "🔷"):
    """Imprime header de seção com estilo"""
    console.print(f"\n{icon} {title}", style=f"bold {NERV_CYAN}")
    console.print("─" * 70, style=NERV_CYAN)


def print_agent_response(agent_name: str, response: str, icon: str = ""):
    """Imprime resposta de um agente com formatação"""
    panel_style = {
        "MELCHIOR": f"bold {NERV_YELLOW}",
        "BALTHASAR": f"bold {NERV_GREEN}",
        "GASPAR": f"bold {NERV_CYAN}",
    }

    icons = {
        "MELCHIOR": "🔬",
        "BALTHASAR": "⚖️",
        "GASPAR": "⚡",
    }

    panel = Panel(
        response,
        title=f"{icons.get(agent_name, icon)} {agent_name}",
        style=panel_style.get(agent_name, ""),
        expand=False,
    )
    console.print(panel)


def print_consensus_table(result) -> Table:
    """Cria tabela de resultados de consenso"""
    table = Table(title="📊 ANÁLISE DE CONSENSO", style=NERV_GREEN)

    table.add_column("Métrica", style=NERV_CYAN, width=25)
    table.add_column("Valor", style=NERV_YELLOW)

    for agente in ("MELCHIOR", "BALTHASAR", "GASPAR"):
        stance = result.stances.get(agente)
        table.add_row(f"Posição {agente}", stance.label if stance else "—")

    table.add_row("Componentes ativos", f"{result.live_agents} de 3")
    table.add_row("Concordância", f"{result.consensus_rate:.0%}")
    if result.vetoed:
        table.add_row("Veto ético", "🔴 BALTHASAR bloqueou")
    table.add_row("Veredito", result.verdict.value)
    table.add_row("Status", _get_verdict_emoji(result.verdict))

    return table


def _get_verdict_emoji(verdict) -> str:
    """Retorna emoji baseado no tipo de veredito"""
    emoji_map = {
        "DELIBERATION_PASS": "✅ Aprovado",
        "CONDITIONAL_PASS": "⚠️ Aprovado Condicionalmente",
        "CODE_RED": "🔴 Alerta Crítico",
        "DIVERGENCE": "💥 Forte Divergência",
    }
    return emoji_map.get(verdict.value, "❓ Indeterminado")


async def get_user_query() -> str:
    """Obtém query do usuário com validação"""
    console.print("\n", end="")
    query = console.input("[bold cyan]❓ Digite sua questão[/] [dim](ou 'sair' para exitir):[/] ")
    return query.strip()


async def run_magi_deliberation(magi: MagiSystem, query: str):
    """Executa deliberação completa com UI"""
    print_section_header("DELIBERAÇÃO MAGI INICIADA", "🎯")

    # Spinner enquanto aguarda respostas
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Consultando 3 perspectivas..."),
        transient=True,
    ) as progress:
        progress.add_task("deliberating", total=None)
        result = await magi.deliberate(query)

    console.print()

    # Imprime respostas individuais
    print_section_header("PERSPECTIVAS INDIVIDUAIS", "👁️")

    print_agent_response("MELCHIOR", result.melchior_response)
    if result.sources:
        console.print(f"[dim]   🔎 {len(result.sources)} fontes consultadas:[/]")
        for fonte in result.sources[:5]:
            console.print(f"[dim]      · {fonte}[/]")
        if len(result.sources) > 5:
            console.print(f"[dim]      · (+{len(result.sources) - 5} outras)[/]")
    print_agent_response("BALTHASAR", result.balthasar_response)
    print_agent_response("GASPAR", result.gaspar_response)

    # Imprime análise de consenso
    print_section_header("RESULTADO DA DELIBERAÇÃO", "🎯")
    console.print(print_consensus_table(result))

    # Imprime raciocínio
    print_section_header("ANÁLISE DO VEREDITO", "🧠")
    console.print(f"[bold {NERV_YELLOW}]{result.reasoning}[/]")

    # Imprime recomendação final
    print_section_header("RECOMENDAÇÃO FINAL DO MAGI", "💡")
    recommendation_panel = Panel(
        result.final_recommendation,
        style=f"bold {NERV_GREEN}",
        expand=False,
    )
    console.print(recommendation_panel)

    # Status final
    verdict_color = {
        "DELIBERATION_PASS": NERV_GREEN,
        "CONDITIONAL_PASS": NERV_YELLOW,
        "CODE_RED": NERV_RED,
        "DIVERGENCE": NERV_RED,
    }.get(result.verdict.value, "white")

    console.print(
        f"\n[bold {verdict_color}]━━ VEREDITO FINAL: {result.verdict.value} ━━[/]\n",
        justify="center",
    )


async def interactive_mode(magi: MagiSystem):
    """Modo interativo de conversação"""
    print_banner()
    console.print(
        Panel(
            "[bold cyan]MAGI System Deliberation Engine[/]\n"
            "[dim]Formule questões complexas para análise por 3 perspectivas IA[/]",
            style="bold green",
        )
    )

    while True:
        query = await get_user_query()

        if query.lower() in ["sair", "exit", "quit", "q"]:
            console.print("\n[bold yellow]🌙 MAGI System desligando...[/]\n")
            break

        if not query:
            console.print("[dim]Por favor, digite uma questão válida.[/]")
            continue

        try:
            await run_magi_deliberation(magi, query)
        except KeyboardInterrupt:
            console.print("\n[bold red]⚠️ Operação cancelada pelo usuário[/]\n")
        except Exception as e:
            console.print(f"[bold red]❌ Erro: {str(e)}[/]\n")


async def single_query_mode(magi: MagiSystem, query: str):
    """Modo de query única (linha de comando)"""
    print_banner()
    console.print(f"[bold cyan]📋 Processando:[/] {query}\n")
    await run_magi_deliberation(magi, query)


def validate_config():
    """Valida configuração antes de rodar"""
    try:
        config = MagiConfig()
        config.validate()
        return config
    except ValueError as e:
        console.print(f"[bold red]❌ Erro de Configuração[/]\n{str(e)}", style="red")
        sys.exit(1)


async def main():
    """Ponto de entrada da CLI"""
    config = validate_config()
    magi = MagiSystem(config)

    # Modo interativo ou query única
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        await single_query_mode(magi, query)
    else:
        await interactive_mode(magi)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Programa interrompido pelo usuário[/]\n")
