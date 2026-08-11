/* ==========================================================================
   MAGI System — lógica da interface de deliberação
   Consome o payload completo do motor de consenso: posições por componente,
   quórum, veto e fontes consultadas.
   ========================================================================== */

'use strict';

const AGENTES = ['MELCHIOR', 'BALTHASAR', 'GASPAR'];

/* Posição da API -> estado visual + rótulo em português */
const POSICAO = {
  YES:         { estado: 'favor',    rotulo: 'FAVORÁVEL',   noDisplay: 'FAVORÁVEL' },
  CONDITIONAL: { estado: 'ressalva', rotulo: 'CONDICIONAL', noDisplay: 'CONDICIONAL' },
  NO:          { estado: 'contra',   rotulo: 'CONTRÁRIO',   noDisplay: 'CONTRÁRIO' },
  INFO:        { estado: 'info',     rotulo: 'INFORMATIVO', noDisplay: 'SEM POSIÇÃO' },
  ERROR:       { estado: 'morto',    rotulo: 'SEM RESPOSTA', noDisplay: 'OFFLINE' },
};

const VEREDITO = {
  DELIBERATION_PASS: { estado: 'aprovado',    titulo: 'APROVADO',  sub: 'consenso entre os componentes' },
  CONDITIONAL_PASS:  { estado: 'ressalvas',   titulo: 'RESSALVAS', sub: 'aprovado sob condições' },
  CODE_RED:          { estado: 'rejeitado',   titulo: 'REJEITADO', sub: 'objeção registrada' },
  DIVERGENCE:        { estado: 'divergencia', titulo: 'IMPASSE',   sub: 'sem maioria formada' },
};

const el = (id) => document.getElementById(id);

const ui = {
  query: el('query'),
  submit: el('submit'),
  progress: el('progress'),
  result: el('result'),
  error: el('error'),
  core: el('core'),
  coreVerdict: el('core-verdict'),
  coreSub: el('core-sub'),
  veto: el('veto-banner'),
  degraded: el('degraded-banner'),
  degradedText: el('degraded-text'),
  consensus: el('t-consensus'),
  live: el('t-live'),
  reason: el('t-reason'),
  synthesis: el('synthesis'),
  sourcesWrap: el('sources-wrap'),
  sourcesCount: el('sources-count'),
  sourcesList: el('sources-list'),
  link: el('link-status'),
  clock: el('clock'),
};

let ocupado = false;

/* ---------------------------------------------------------------- relógio */

function tick() {
  ui.clock.textContent = new Date().toLocaleTimeString('pt-BR', { hour12: false });
}

/* ------------------------------------------------------- estado dos nós */

function definirNo(agente, estado, textoEstado) {
  const no = el(`node-${agente}`);
  if (!no) return;
  no.dataset.state = estado;
  const rotulo = no.querySelector('.node-state');
  if (rotulo) rotulo.textContent = textoEstado;

  const conexao = document.querySelector(`.link[data-link="${agente}"]`);
  if (conexao) conexao.dataset.state = estado;
}

function definirNucleo(estado, titulo, sub) {
  ui.core.dataset.verdict = estado;
  ui.coreVerdict.textContent = titulo;
  ui.coreSub.textContent = sub;
}

function reiniciarDisplay() {
  AGENTES.forEach((a) => definirNo(a, 'ativo', 'CONSULTANDO'));
  definirNucleo('ativo', 'DELIBERANDO', 'consulta em andamento');
  ui.veto.hidden = true;
  ui.degraded.hidden = true;
  ui.error.hidden = true;
  ui.result.hidden = true;
}

/* --------------------------------------------------- texto -> HTML seguro
   As respostas vêm em markdown leve dos modelos. Converto apenas os quatro
   padrões que eles de fato usam, escapando o HTML antes — nada de innerHTML
   com conteúdo bruto de terceiros.                                        */

function escapar(texto) {
  const d = document.createElement('div');
  d.textContent = texto;
  return d.innerHTML;
}

function formatar(texto) {
  if (!texto) return '';
  return escapar(texto)
    .split(/\n{2,}/)
    .map((bloco) => {
      const t = bloco.trim();
      if (!t) return '';
      const cabecalho = t.match(/^#{1,6}\s+(.*)$/s);
      if (cabecalho) return `<h4>${inline(cabecalho[1])}</h4>`;
      return `<p>${inline(t).replace(/\n/g, '<br>')}</p>`;
    })
    .join('');
}

function inline(t) {
  return t
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

/* ------------------------------------------------------------ progressão */

const ETAPAS = [
  'Consultando MELCHIOR — análise científica, com busca web…',
  'Consultando BALTHASAR — avaliação ética…',
  'Consultando GASPAR — viabilidade prática…',
  'Classificando as posições no juiz independente…',
  'Consolidando o veredito e redigindo a síntese…',
];

let timerEtapa = null;

function iniciarProgresso() {
  let i = 0;
  ui.progress.hidden = false;
  ui.progress.textContent = ETAPAS[0];
  timerEtapa = setInterval(() => {
    i = Math.min(i + 1, ETAPAS.length - 1);
    ui.progress.textContent = ETAPAS[i];
  }, 6000);
}

function pararProgresso() {
  clearInterval(timerEtapa);
  timerEtapa = null;
  ui.progress.hidden = true;
}

/* -------------------------------------------------------------- render */

function renderizar(dados) {
  const posicoes = dados.stances || {};

  AGENTES.forEach((agente) => {
    const info = POSICAO[posicoes[agente]] || POSICAO.INFO;
    definirNo(agente, info.estado, info.noDisplay);

    const chip = document.querySelector(`[data-stance-for="${agente}"]`);
    if (chip) {
      chip.dataset.state = info.estado;
      chip.textContent = info.rotulo;
    }

    const corpo = document.querySelector(`[data-body-for="${agente}"]`);
    if (corpo) {
      const chave = agente.toLowerCase();
      corpo.innerHTML = formatar((dados.perspectives || {})[chave] || '');
    }
  });

  const v = VEREDITO[dados.verdict] || VEREDITO.DIVERGENCE;
  definirNucleo(v.estado, v.titulo, dados.vetoed ? 'bloqueado por veto ético' : v.sub);

  ui.veto.hidden = !dados.vetoed;

  if (dados.degraded) {
    const caidos = AGENTES.filter((a) => posicoes[a] === 'ERROR');
    ui.degradedText.textContent =
      `${dados.live_agents} de 3 componentes responderam` +
      (caidos.length ? ` — sem resposta de ${caidos.join(' e ')}.` : '.') +
      ' A concordância abaixo considera apenas os ativos.';
    ui.degraded.hidden = false;
  } else {
    ui.degraded.hidden = true;
  }

  ui.consensus.textContent = `${Math.round((dados.consensus_rate || 0) * 100)}%`;
  ui.live.textContent = `${dados.live_agents} de 3`;
  ui.reason.textContent = dados.reasoning || '—';
  ui.synthesis.innerHTML = formatar(dados.synthesis || '');

  const fontes = dados.sources || [];
  if (fontes.length) {
    ui.sourcesCount.textContent = fontes.length;
    ui.sourcesList.replaceChildren(
      ...fontes.map((f) => {
        const li = document.createElement('li');
        li.textContent = f;
        return li;
      })
    );
    ui.sourcesWrap.hidden = false;
  } else {
    ui.sourcesWrap.hidden = true;
  }

  ui.result.hidden = false;
  ui.result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function falhar(mensagem) {
  AGENTES.forEach((a) => definirNo(a, 'morto', 'OFFLINE'));
  definirNucleo('rejeitado', 'FALHA', 'deliberação não concluída');
  ui.error.textContent = mensagem;
  ui.error.hidden = false;
}

/* -------------------------------------------------------------- consulta */

async function deliberar() {
  if (ocupado) return;

  const consulta = ui.query.value.trim();
  if (consulta.length < 5) {
    falhar('Formule uma questão com pelo menos 5 caracteres.');
    return;
  }
  if (consulta.length > 500) {
    falhar('Questão muito longa — limite de 500 caracteres.');
    return;
  }

  ocupado = true;
  ui.submit.disabled = true;
  ui.query.disabled = true;
  reiniciarDisplay();
  iniciarProgresso();

  try {
    const resposta = await fetch('/api/deliberate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: consulta }),
    });

    if (!resposta.ok) {
      let detalhe = `O servidor respondeu ${resposta.status}.`;
      try {
        const corpo = await resposta.json();
        if (corpo.detail) detalhe = corpo.detail;
      } catch { /* resposta sem JSON — mantém a mensagem padrão */ }
      throw new Error(detalhe);
    }

    renderizar(await resposta.json());
  } catch (erro) {
    falhar(
      erro instanceof TypeError
        ? 'Sem conexão com o servidor MAGI. Confirme que o web_server.py está rodando.'
        : erro.message
    );
  } finally {
    pararProgresso();
    ocupado = false;
    ui.submit.disabled = false;
    ui.query.disabled = false;
    ui.query.focus({ preventScroll: true });
  }
}

/* ------------------------------------------------------------- inicialização */

async function verificarEnlace() {
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    if (d.magi_initialized) {
      ui.link.textContent = 'ENLACE ATIVO';
      ui.link.className = 'readout live';
    } else {
      ui.link.textContent = 'SEM CHAVES';
      ui.link.className = 'readout down';
      falhar('O servidor subiu, mas o MAGI não inicializou — verifique as três chaves de API no .env.');
    }
  } catch {
    ui.link.textContent = 'ENLACE PERDIDO';
    ui.link.className = 'readout down';
  }
}

function iniciar() {
  tick();
  setInterval(tick, 1000);
  ui.submit.addEventListener('click', deliberar);
  ui.query.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') deliberar();
  });
  verificarEnlace();
  // preventScroll: focar o campo rolaria a página para baixo, escondendo o
  // display do MAGI logo no carregamento.
  ui.query.focus({ preventScroll: true });

  // ?q=… preenche e delibera automaticamente — permite compartilhar o link
  // de uma consulta específica.
  const q = new URLSearchParams(location.search).get('q');
  if (q) {
    ui.query.value = q;
    deliberar();
  }
}

document.addEventListener('DOMContentLoaded', iniciar);
