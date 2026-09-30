// Nota Fiscal Goiana: coleta todas as notas do CPF logado.
// Rodar com javascript_tool na aba https://nfgoiana.economia.go.gov.br/nfg/cidadao/inicioSite (já logada).
// Percorre o modal "Consultar minhas notas em detalhe" página por página, clicando em "»".
// São ~50 páginas e o javascript_tool corta em 45 s, então a coleta roda em segundo plano na página:
// este script só a inicia. Consulte o andamento com  JSON.stringify(window.__coleta)  até fase = "pronto" ou "erro".
// No fim, o CSV fica em window.__notasCsv e o resumo em window.__coleta.resumo.
(() => {
  if (window.__coleta && window.__coleta.fase === 'rodando') return 'já está rodando: ' + JSON.stringify(window.__coleta);
  const st = window.__coleta = { fase: 'rodando', pagina: 0, paginas: null };
  window.__notasCsv = null;

  (async () => {
    // Aba em segundo plano: o Chrome segura setTimeout por até 1 min. A espera é feita com MutationObserver,
    // que não é desacelerado; o setTimeout fica só como limite de tempo.
    const esperar = (alvo, cond, ms = 90000) => new Promise((ok, falha) => {
      if (cond()) return ok();
      const obs = new MutationObserver(() => { if (cond()) { obs.disconnect(); clearTimeout(t); ok(); } });
      obs.observe(alvo, { childList: true, subtree: true, characterData: true, attributes: true });
      const t = setTimeout(() => { obs.disconnect(); cond() ? ok() : falha(new Error('tempo esgotado')); }, ms);
    });
    const acharModal = () => [...document.querySelectorAll('.modal')]
      .find(m => m.textContent.includes('Consultar minhas notas em detalhe'));

    // O modal só é montado depois do clique no link.
    const abrir = [...document.querySelectorAll('a')].find(a => a.textContent.trim() === 'Consultar Minhas Notas em Detalhe');
    if (!abrir) throw new Error('Link "Consultar Minhas Notas em Detalhe" não encontrado. O Pet está logado e na página inicial do portal?');
    abrir.click();
    try { await esperar(document.body, () => !!acharModal()); }
    catch (e) { throw new Error('O modal de notas não abriu.'); }
    const modal = acharModal();

    const ler = () => [...modal.querySelectorAll('tbody tr')].map(r => {
      const c = [...r.cells].map(x => x.textContent.trim());
      const chave = (r.innerHTML.match(/\d{44}/) || [''])[0];
      const fant = ((r.cells[4] && r.cells[4].querySelector('[title]')) || {}).title || '';
      return { num: c[0], cnpj: c[1], emp: c[2], fant: fant.replace('Nome Fantasia: ', '').replace('Em branco', ''),
               data: c[6], valor: (c[7] || '').replace('R$ ', ''), pontos: c[8], sorteio: c[9], chave };
    }).filter(n => n.num);

    // A página ativa da paginação é o único número sem href.
    const ativa = () => { const a = [...modal.querySelectorAll('ul a')].find(x => /^\d+$/.test(x.textContent.trim()) && !x.getAttribute('href'));
                          return a ? +a.textContent.trim() : 0; };
    await esperar(modal, () => ler().length > 0);
    if (ativa() !== 1) {
      const primeira = modal.querySelector('a[href="#1"]');
      if (!primeira) throw new Error('Sem link para a página 1.');
      primeira.click();
      await esperar(modal, () => ativa() === 1 && ler().length > 0);
    }
    const numeros = [...modal.querySelectorAll('ul a')].map(a => parseInt(a.textContent.trim(), 10)).filter(n => n > 0);
    const paginas = st.paginas = numeros.length ? Math.max(...numeros) : 1;

    const todas = [];
    for (let p = 1; p <= paginas; p++) {
      st.pagina = p;
      const antes = JSON.stringify(ler()[0]);
      if (p > 1) {
        const prox = [...modal.querySelectorAll('ul a')].find(a => a.textContent.trim() === '»');
        if (!prox) throw new Error(`Sem botão "»" na página ${p - 1}.`);
        prox.click();
        try { await esperar(modal, () => ativa() === p && JSON.stringify(ler()[0]) !== antes); }
        catch (e) { throw new Error(`A página ${p} não carregou.`); }
      }
      todas.push(...ler());
    }

    const tipo = k => ({ '55': 'NF-e', '65': 'NFC-e' })[k.slice(20, 22)] || (k ? 'Outro' : 'Cupom sem chave');
    const q = s => '"' + String(s ?? '').replace(/"/g, '""') + '"';
    const hoje = new Date().toISOString().slice(0, 10);
    window.__notasCsv = {
      arquivo: `notas-go-${hoje}.csv`,
      linhas: [
        'Data;Tipo;Numero;CNPJ;Empresa;Nome fantasia;Valor (R$);Pontos;Sorteio;Chave de acesso',
        ...todas.map(n => [n.data, tipo(n.chave), n.num, n.cnpj, q(n.emp), q(n.fant), n.valor, n.pontos, n.sorteio,
                           n.chave ? `="${n.chave}"` : ''].join(';'))
      ]
    };

    const valor = n => parseFloat(n.valor.replace(/\./g, '').replace(',', '.')) || 0;
    const porAno = {}, porTipo = {};
    todas.forEach(n => {
      const a = n.data.slice(6); porAno[a] = porAno[a] || [0, 0]; porAno[a][0]++; porAno[a][1] += valor(n);
      const t = tipo(n.chave); porTipo[t] = (porTipo[t] || 0) + 1;
    });
    st.resumo = {
      notas: todas.length, semChave: todas.filter(n => !n.chave).length, porTipo,
      total: Math.round(todas.reduce((s, n) => s + valor(n), 0)),
      porAno: Object.fromEntries(Object.entries(porAno).sort().map(([a, x]) => [a, [x[0], Math.round(x[1])]]))
    };
    st.fase = 'pronto';
  })().catch(e => { st.fase = 'erro'; st.erro = String(e && e.message || e); });

  return 'coleta iniciada; consulte JSON.stringify(window.__coleta)';
})();
