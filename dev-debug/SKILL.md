---
name: dev-debug
description: Investiga a causa raiz de um bug sem corrigir. Use quando houver relato de erro, comportamento inesperado ou ticket de BUG e a causa não for óbvia. Não use para implementar nem para aplicar correção.
---

# Debug: causa raiz, sem corrigir

## Regras
- Não altere código, configuração nem dados. Pode criar script de diagnóstico ou log temporário no rascunho, fora do projeto.
- Não aceite a primeira explicação plausível. A causa só está confirmada quando você consegue ligar e desligar o erro com ela.
- Separe o que foi **observado** (saída, log, comando) do que é **suposição**.
- Se não conseguir reproduzir, diga isso e pare. Não chute a causa.

## Passos
1. **Reproduzir:** execute os passos do relato e registre o comando e a saída exata.
2. **Delimitar:** onde funciona e onde falha (versão, entrada, ambiente, usuário, máquina).
3. **Hipóteses:** liste as candidatas e teste uma por vez, da mais barata de verificar para a mais cara.
4. **Confirmar:** mostre a evidência que prova a causa (log, valor, diff, teste que falha).
5. **Alcance:** que outros pontos usam o mesmo código ou a mesma configuração e podem ter o mesmo defeito.

## Saída (formato fixo)
- **Sintoma:** o que o usuário vê, em uma frase.
- **Reprodução:** passos numerados, comando e resultado observado.
- **Causa raiz:** o que, onde (arquivo:linha ou componente) e por quê.
- **Evidência:** o que prova a causa.
- **Hipóteses descartadas:** cada uma com o motivo.
- **Alcance:** outros pontos afetados ou suspeitos.
- **Correção sugerida:** o que mudar e onde, sem aplicar.
- **Risco da correção:** o que pode quebrar.
- **Confiança:** confirmada / provável / não reproduzido.
