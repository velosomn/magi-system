"""Verifica a geometria do display do MAGI em static/index.html.

As coordenadas dos polígonos e conectores são escritas à mão e erram em silêncio:
um conector cujo extremo não toca o polígono aparece na tela como um risco solto,
sem nenhum erro de execução. Foi exatamente o que aconteceu com BALTHASAR e
GASPAR — a origem caía fora do trapézio porque a aresta inclinada já havia
recuado naquela altura.

Roda sem servidor e sem navegador: lê o SVG e faz as contas.
"""

import re
from pathlib import Path

import pytest

SVG = Path(__file__).parent / "static" / "index.html"
AGENTES = ("MELCHIOR", "BALTHASAR", "GASPAR")

Ponto = tuple[float, float]
Aresta = tuple[Ponto, Ponto]


def _pontos(texto: str) -> list[Ponto]:
    return [tuple(map(float, p.split(","))) for p in texto.split()]


@pytest.fixture(scope="module")
def svg() -> str:
    return SVG.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def nucleo(svg) -> list[Ponto]:
    m = re.search(r'class="core-shape"\s*\n?\s*points="([^"]+)"', svg)
    assert m, "polígono do núcleo não encontrado"
    return _pontos(m.group(1))


@pytest.fixture(scope="module")
def nos(svg) -> dict[str, list[Ponto]]:
    achados = {}
    for agente in AGENTES:
        m = re.search(
            rf'id="node-{agente}"[^>]*>\s*<polygon class="node-shape" points="([^"]+)"',
            svg,
        )
        assert m, f"polígono de {agente} não encontrado"
        achados[agente] = _pontos(m.group(1))
    return achados


@pytest.fixture(scope="module")
def conectores(svg) -> dict[str, tuple[Ponto, Ponto]]:
    achados = {}
    for m in re.finditer(
        r'data-link="(\w+)"\s+x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)"',
        svg,
    ):
        nome, x1, y1, x2, y2 = m.groups()
        achados[nome] = ((float(x1), float(y1)), (float(x2), float(y2)))
    return achados


def _arestas(poly: list[Ponto]) -> list[Aresta]:
    return [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]


def _toca(p: Ponto, poly: list[Ponto], tol: float = 0.6) -> bool:
    """O ponto está sobre alguma aresta (ou vértice) do polígono?"""
    px, py = p
    for (ax, ay), (bx, by) in _arestas(poly):
        dx, dy = bx - ax, by - ay
        comp2 = dx * dx + dy * dy
        t = 0.0 if comp2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / comp2))
        if ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5 <= tol:
            return True
    return False


def _cruzam(s1: Aresta, s2: Aresta) -> bool:
    """Os segmentos se cruzam propriamente? Toque em extremidade não conta."""
    (x1, y1), (x2, y2) = s1
    (x3, y3), (x4, y4) = s2
    d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(d) < 1e-9:
        return False
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
    u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
    return 1e-6 < t < 1 - 1e-6 and 1e-6 < u < 1 - 1e-6


class TestConectores:
    """Cada linha precisa ligar de fato o núcleo a um nó."""

    @pytest.mark.parametrize("agente", AGENTES)
    def test_liga_nucleo_ao_no(self, agente, conectores, nucleo, nos):
        assert agente in conectores, f"conector de {agente} ausente"
        a, b = conectores[agente]
        # direção-agnóstico: um extremo no núcleo, o outro no nó
        ligado = (_toca(a, nucleo) and _toca(b, nos[agente])) or (
            _toca(b, nucleo) and _toca(a, nos[agente])
        )
        assert ligado, (
            f"conector de {agente} {a}->{b} não toca núcleo e nó — "
            "na tela vira um risco solto"
        )

    @pytest.mark.parametrize("agente", AGENTES)
    def test_visivel(self, agente, conectores):
        (x1, y1), (x2, y2) = conectores[agente]
        comp = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        assert comp >= 25, f"conector de {agente} tem {comp:.0f}px — curto demais"


class TestSobreposicao:
    """Nada pode invadir nada."""

    @pytest.mark.parametrize("agente", AGENTES)
    def test_no_nao_invade_nucleo(self, agente, nos, nucleo):
        colisoes = [
            (e1, e2)
            for e1 in _arestas(nos[agente])
            for e2 in _arestas(nucleo)
            if _cruzam(e1, e2)
        ]
        assert not colisoes, f"{agente} cruza o núcleo em {len(colisoes)} ponto(s)"

    @pytest.mark.parametrize(
        "a,b",
        [("MELCHIOR", "BALTHASAR"), ("MELCHIOR", "GASPAR"), ("BALTHASAR", "GASPAR")],
    )
    def test_nos_nao_se_cruzam(self, a, b, nos):
        colisoes = [
            (e1, e2) for e1 in _arestas(nos[a]) for e2 in _arestas(nos[b]) if _cruzam(e1, e2)
        ]
        assert not colisoes, f"{a} cruza {b}"

    def test_nos_da_base_separados(self, nos):
        """BALTHASAR e GASPAR precisam de espaço visível entre si."""
        dir_balthasar = max(x for x, _ in nos["BALTHASAR"])
        esq_gaspar = min(x for x, _ in nos["GASPAR"])
        folga = esq_gaspar - dir_balthasar
        assert folga >= 100, f"apenas {folga:.0f}px entre BALTHASAR e GASPAR"


class TestEnquadramento:
    def test_conteudo_cabe_no_viewbox(self, svg, nos, nucleo):
        m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
        assert m, "viewBox não encontrado"
        largura, altura = int(m.group(1)), int(m.group(2))

        todos = [p for poly in nos.values() for p in poly] + nucleo
        assert max(x for x, _ in todos) <= largura - 15, "conteúdo encosta na borda direita"
        assert max(y for _, y in todos) <= altura - 15, "conteúdo encosta na borda inferior"
        assert min(x for x, _ in todos) >= 15, "conteúdo encosta na borda esquerda"
        assert min(y for _, y in todos) >= 15, "conteúdo encosta na borda superior"

    def test_composicao_simetrica(self, nos, nucleo):
        """O núcleo fica centrado entre os dois nós da base."""
        centro_nucleo = sum(x for x, _ in nucleo) / len(nucleo)
        centro_b = sum(x for x, _ in nos["BALTHASAR"]) / 4
        centro_g = sum(x for x, _ in nos["GASPAR"]) / 4
        meio = (centro_b + centro_g) / 2
        assert abs(centro_nucleo - meio) < 2, (
            f"núcleo em x={centro_nucleo:.0f}, meio da base em x={meio:.0f}"
        )


class TestTextos:
    @pytest.mark.parametrize("agente", AGENTES)
    def test_texto_centrado_no_no(self, agente, svg, nos):
        """O texto precisa acompanhar o polígono quando ele se move."""
        bloco = re.search(
            rf'id="node-{agente}".*?</g>', svg, re.S
        ).group(0)
        xs = {float(x) for x in re.findall(r'<text[^>]*\sx="([\d.]+)"', bloco)}
        assert len(xs) == 1, f"textos de {agente} em x diferentes: {sorted(xs)}"

        centro = sum(x for x, _ in nos[agente]) / 4
        assert abs(xs.pop() - centro) < 2, f"texto de {agente} fora do centro do polígono"

    @pytest.mark.parametrize("agente", AGENTES)
    def test_texto_dentro_do_no(self, agente, svg, nos):
        bloco = re.search(rf'id="node-{agente}".*?</g>', svg, re.S).group(0)
        ys = [float(y) for y in re.findall(r'<text[^>]*\sy="([\d.]+)"', bloco)]
        topo = min(y for _, y in nos[agente])
        base = max(y for _, y in nos[agente])
        for y in ys:
            assert topo < y < base, f"texto de {agente} em y={y} fora do polígono"
