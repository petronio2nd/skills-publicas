// Baixa o CSV montado por um dos scripts de coleta (window.__notasCsv) para a pasta de downloads do Chrome.
// UTF-8 com BOM e ponto e vírgula, para abrir direto no Excel em português.
// A chave vai como ="..." para o Excel não transformar os 44 dígitos em notação científica.
await (async () => {
  const c = window.__notasCsv;
  if (!c) throw new Error('Nada coletado nesta aba. Rode antes o script de coleta do estado.');
  const bom = String.fromCharCode(0xFEFF);
  const blob = new Blob([bom + c.linhas.join('\r\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = c.arquivo;
  document.body.appendChild(a); a.click(); a.remove();
  return `${c.arquivo}: ${c.linhas.length - 1} notas, ${blob.size} bytes`;
})();
