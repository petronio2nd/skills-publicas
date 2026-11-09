# skills

Este repositório não distribui mais skills avulsas (desde 09/11/2026). As versões antigas continuam no histórico do git, sem manutenção.

O que eu mantenho público está no **[delcouncil](https://github.com/petronio2nd/delcouncil)**: um método para orquestrar agentes de IA por capacidade (N1/N2/N3), com revisão cruzada entre famílias de modelos e trava de consumo por fonte.

| Lá você encontra | O que é |
|---|---|
| `skills/orquestrador` | Skill da sessão que recebe o pedido: fatia o trabalho, escolhe nível e executor, confere e registra |
| `skills/dupla` | Skill e scripts PowerShell: revisão cruzada, reservas por falta de cota, executores e a trava de fontes |
| `skills/revisor` | Papel do revisor: só lê e devolve achados com severidade e evidência |
| `mods/orquestra` e `mods/gemeo` | Mods do Claude Code e do OpenCode que aplicam a rota por fatia |

Instalação e método: veja o README e a pasta `docs` do delcouncil.
