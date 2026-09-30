// Nota Premiada Acreana: coleta todas as notas do CPF logado pela API do próprio portal.
// Rodar com javascript_tool na aba https://notapremiadaacreana.ac.gov.br (já logada).
// O token fica em localStorage.AccessToken (JWT); o CPF é o campo "sub". Nenhum dos dois é impresso.
// Guarda o CSV em window.__notasCsv e devolve só o resumo (o texto inteiro não cabe na saída da ferramenta).
await (async () => {
  let token = localStorage.getItem('AccessToken');
  if (!token) throw new Error('Sem AccessToken. O Pet está logado no portal?');
  try { const j = JSON.parse(token); if (typeof j === 'string') token = j; else if (j && j.token) token = j.token; } catch (e) {}
  const cpf = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).sub;

  const api = 'https://notapremiadaacreanaapi.ac.gov.br/api/v1/user/historic-documents';
  const todas = [];
  for (let p = 0; p < 500; p++) {
    const r = await fetch(`${api}?page=${p}&per_page=100&cpfCnpjDestinatario=${cpf}`,
                          { headers: { Authorization: 'Bearer ' + token } });
    if (!r.ok) throw new Error(`API respondeu ${r.status} na página ${p}. Sessão expirada? Peça ao Pet para logar de novo.`);
    const lote = (await r.json()).historicDocuments || [];
    todas.push(...lote);
    if (lote.length < 100) break;
  }

  const cnpj = c => c.length === 14 ? c.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5') : c;
  const tipo = t => ({ NFE: 'NF-e', NFCE: 'NFC-e' })[t] || t;
  const status = s => ({ AUTORIZADA: 'Autorizada', CANCELADA: 'Cancelada' })[s] || s;
  const q = s => '"' + String(s ?? '').replace(/"/g, '""') + '"';
  const hoje = new Date().toISOString().slice(0, 10);
  window.__notasCsv = {
    arquivo: `notas-ac-${hoje}.csv`,
    linhas: [
      'Data;Tipo;Numero;CNPJ;Empresa;Valor (R$);Status;Chave de acesso',
      ...todas.map(n => {
        const k = n.chaveAcesso || '';
        return [n.dataEmissao.split('-').reverse().join('/'), tipo(n.tipoDocumento), k ? String(+k.slice(25, 34)) : '',
                cnpj(n.cnpjCpfEmitente || ''), q(n.nomeFantasia), n.valorTotal.toFixed(2).replace('.', ','),
                status(n.status), k ? `="${k}"` : ''].join(';');
      })
    ]
  };

  const validas = todas.filter(n => n.status !== 'CANCELADA');
  const porAno = {}, porTipo = {}, porStatus = {};
  todas.forEach(n => {
    porTipo[tipo(n.tipoDocumento)] = (porTipo[tipo(n.tipoDocumento)] || 0) + 1;
    porStatus[status(n.status)] = (porStatus[status(n.status)] || 0) + 1;
  });
  validas.forEach(n => {
    const a = n.dataEmissao.slice(0, 4); porAno[a] = porAno[a] || [0, 0]; porAno[a][0]++; porAno[a][1] += n.valorTotal;
  });
  return JSON.stringify({
    notas: todas.length, porTipo, porStatus,
    totalAutorizadas: Math.round(validas.reduce((s, n) => s + n.valorTotal, 0)),
    porAno: Object.fromEntries(Object.entries(porAno).sort().map(([a, x]) => [a, [x[0], Math.round(x[1])]]))
  });
})();
