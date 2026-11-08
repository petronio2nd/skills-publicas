# skills

Skills que eu uso no Claude Code e no Codex, compartilhadas com os amigos. Nas skills, "o Pet" sou eu: troque pelo seu nome ou por "o usuário".

Esta é uma cópia pública, gerada a partir do meu repositório privado. Ficaram de fora as skills com dado pessoal ou de licença que não permite redistribuir.

## Skills

| Skill | Para quê | Funciona fora do meu PC? |
|---|---|---|
| `1-simulador` | Estressa ideias e decisões antes de decidir (advogado do diabo) | Sim. Salva a síntese no Notion, se houver conector |
| `2-destilador` | Organiza material bruto (notas, transcrições, brain dump) | Sim. Idem |
| `3-protocolo` | Transforma decisão já tomada em checklist sem ambiguidade | Sim. Idem |
| `4-intencao` | Traduz fala, pedido ou oferta para a intenção real por trás; mensagem clara e ética | Sim |
| `dev-debug` | Causa raiz de um bug, sem corrigir | Sim |
| `agendar-retomada` | Bloco para retomar a conversa numa sessão nova e rotina que o entrega na data | Sim (agendar só no Claude) |
| `cpa` | Commit, push e arquivar a sessão em um passo | Sim, no app desktop do Claude |
| `diario-oficial-ac` | Diário Oficial do Acre: Gabinete da Governadora e SEICT, com alerta quando o seu nome aparece | Sim. Defina a variável `DOE_NOME` com o seu nome |
| `para-o-sei-formatado` | Texto formatado para o editor do SEI do Acre, pelo Claude in Chrome | Sim. Troque o bloco de assinatura pelo seu |
| `notas-fiscais-cpf` | Notas fiscais no seu CPF (Nota Goiana e Nota Premiada Acreana) em CSV; você faz o login | Sim, com o Claude in Chrome |
| `iniciar-analise` | Análise documental longa por checkpoints e evidências | Parcial: usa o meu molde `modelo-atual` |
| `pepita` | Consulta ao meu acervo de documentos pelo Pepita | Não: serve de exemplo |
| `sintese-coisas-legais` | Síntese curta de cada post ou vídeo salvo numa pasta de leitura | Parcial: ajuste os caminhos |

Os caminhos `D:\...` e o Python em `C:\Users\...` são os da minha máquina: ajuste para a sua.

## Instalar

Copie a pasta da skill para a pasta de skills do agente e abra uma sessão nova:

- Claude Code: `%USERPROFILE%\.claude\skills\<skill>` (Windows) ou `~/.claude/skills/<skill>`
- Codex: `%USERPROFILE%\.codex\skills\<skill>` ou `~/.codex/skills/<skill>`

No Windows, para seguir as atualizações sem copiar de novo: clone o repositório e rode o `ligar.ps1`. Ele liga cada skill às duas pastas por junction, sem precisar de administrador, e não sobrescreve pasta que já exista.

```powershell
git clone https://github.com/petronio2nd/skills-publicas.git
powershell -ExecutionPolicy Bypass -File .\skills-publicas\ligar.ps1
```

## sincronizar-delcouncil.py

Refaz a copia publica e sanitizada do repositorio `delcouncil` (skills orquestrador/dupla/revisor e mods orquestra/gemeo) a partir dos repositorios privados. `--simular` mostra o que mudaria e roda a varredura de dados pessoais (sai com 1 se sobrar algum); sem a flag, grava. Nao faz commit nem push: rode as suites no delcouncil, confira o diff e envie.

```
python _publico/sincronizar-delcouncil.py --simular
python _publico/sincronizar-delcouncil.py
```
