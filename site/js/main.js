(() => {
  const button = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  const scrim = document.querySelector('.mobile-scrim');
  if (!button || !sidebar || !scrim) return;
  const close = () => {
    sidebar.classList.remove('is-open');
    button.setAttribute('aria-expanded', 'false');
    button.setAttribute('aria-label', 'Abrir menu');
    scrim.hidden = true;
  };
  button.addEventListener('click', () => {
    const open = !sidebar.classList.contains('is-open');
    sidebar.classList.toggle('is-open', open);
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    scrim.hidden = !open;
  });
  scrim.addEventListener('click', close);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
  window.matchMedia('(min-width: 721px)').addEventListener('change', event => { if (event.matches) close(); });
})();

// Publication text is always inserted as textContent, never as trusted HTML.
(() => {
  const feed = document.querySelector('#feed');
  if (!feed) return;
  const status = document.querySelector('#job-status');
  const search = document.querySelector('#search');
  const moduleSelect = document.querySelector('#module-filter');
  const sortSelect = document.querySelector('#sort-order');
  const links = Array.from(document.querySelectorAll('[data-module]'));
  const count = document.querySelector('#item-count');
  const moduleNames = { rotinas:'Rotinas', conteudos:'Conteúdos e mídias', dashboards:'Dashboards', relatorios:'Relatórios', pesquisas:'Pesquisas', operacoes:'Operações' };
  let items = [];
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  };
  const date = value => {
    const n = new Date(value);
    return Number.isNaN(n.getTime()) ? 'Data não informada' : new Intl.DateTimeFormat('pt-BR', {dateStyle:'medium', timeStyle:'short'}).format(n);
  };
  const metadata = item => [
    item.duration_seconds == null ? null : `Duração: ${item.duration_seconds} s`,
    item.model ? `Modelo: ${item.model}` : null,
    item.tokens == null ? null : `Tokens: ${item.tokens}`,
    item.cost_usd == null ? null : `Custo estimado: US$ ${item.cost_usd}`
  ].filter(Boolean);
  function render() {
    const q = search.value.trim().toLocaleLowerCase('pt-BR');
    const selected = moduleSelect.value;
    const visible = items.filter(item => (selected === 'todos' || item.module === selected) &&
      [item.title, item.summary, moduleNames[item.module] || item.module].some(v => String(v || '').toLocaleLowerCase('pt-BR').includes(q)));
    visible.sort((a,b) => (Date.parse(b.timestamp) - Date.parse(a.timestamp)) * (sortSelect.value === 'oldest' ? -1 : 1));
    count.textContent = `${visible.length} ${visible.length === 1 ? 'publicação' : 'publicações'}`;
    feed.replaceChildren();
    if (!visible.length) {
      feed.append(el('p', 'empty-panel', items.length ? 'Nenhuma publicação corresponde aos filtros.' : 'Ainda não há publicações. A central está pronta para receber a primeira entrega.'));
      return;
    }
    for (const item of visible) {
      const card = el('article', 'activity-card');
      const top = el('div', 'activity-top');
      top.append(el('span', 'activity-module', moduleNames[item.module] || item.module));
      const time = el('time', '', date(item.timestamp));
      time.dateTime = item.timestamp;
      top.append(time);
      card.append(top);
      const validUrl = /^\/publicacoes\/[a-z0-9-]+\.html$/.test(item.url || '');
      const heading = el('h3', '', item.title);
      if (validUrl) {
        const anchor = el('a', '', item.title);
        anchor.href = item.url;
        heading.replaceChildren(anchor);
      }
      card.append(heading, el('p', 'activity-summary', item.summary));
      const image = (item.media || []).find(x => /^media\/[a-f0-9]{64}\.(png|jpe?g|webp|gif|avif)$/.test(x));
      if (image) {
        const img = el('img', 'activity-thumbnail');
        img.src = image;
        img.alt = `Miniatura de ${item.title}`;
        img.loading = 'lazy';
        card.append(img);
      }
      const info = el('div', 'activity-meta');
      info.append(el('span', item.status === 'failed' ? 'status-bad' : 'status-neutral', item.status || 'Publicado'));
      for (const value of metadata(item)) info.append(el('span', '', value));
      if (!metadata(item).length) info.append(el('span', '', 'Métricas não informadas'));
      card.append(info);
      if (validUrl) {
        const more = el('a', 'activity-open', 'Abrir publicação ↗');
        more.href = item.url;
        card.append(more);
      }
      feed.append(card);
    }
  }
  function renderStatus(jobs) {
    status.replaceChildren();
    if (!jobs.length) {
      status.append(el('p', 'empty-panel', 'Nenhum cron job configurado no Agente. Novas rotinas aparecerão aqui após o cadastro.'));
      return;
    }
    const list = el('div', 'job-list');
    for (const job of jobs) {
      const row = el('div', 'job-row');
      row.append(el('strong', '', job.name));
      const state = job.running ? 'Em execução' : job.last_status === 'failed' ? 'Falhou' : job.state === 'paused' || job.state === 'completed' ? job.state : job.last_status === 'completed' ? 'Concluída' : 'Pendente';
      row.append(el('span', state === 'Falhou' ? 'status-bad' : 'status-neutral', state));
      row.append(el('small', '', job.next_run_at ? `Próxima: ${date(job.next_run_at)}` : 'Sem próxima execução'));
      list.append(row);
    }
    status.append(list);
  }
  async function load() {
    try {
      const [catalog, health] = await Promise.all(['data/catalog.json','data/status.json'].map(url => fetch(url, {cache:'no-store'})));
      if (!catalog.ok || !health.ok) throw new Error('Dados indisponíveis');
      const feedData = await catalog.json();
      const healthData = await health.json();
      if (!Array.isArray(feedData.items) || !Array.isArray(healthData.jobs)) throw new Error('Dados inválidos');
      items = feedData.items;
      render();
      renderStatus(healthData.jobs);
    } catch (_) {
      feed.replaceChildren(el('p', 'empty-panel', 'Não foi possível carregar as publicações. Atualize a página.'));
      status.replaceChildren(el('p', 'empty-panel', 'Estado das rotinas indisponível.'));
      count.textContent = 'Indisponível';
    }
  }
  for (const input of [search, moduleSelect, sortSelect]) input.addEventListener('input', render);
  links.forEach(link => link.addEventListener('click', () => {
    moduleSelect.value = link.dataset.module;
    links.forEach(node => {
      node.classList.toggle('active', node === link);
      if (node === link) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current');
    });
    render();
    if (window.matchMedia('(max-width: 720px)').matches && document.querySelector('.sidebar')?.classList.contains('is-open')) document.querySelector('.menu-toggle')?.click();
  }));
  load();
  setInterval(load, 60000);
})();
