---
name: dev-correcao
description: Aplica a correção de um bug a partir do diagnóstico do dev-debug. Use quando houver relatório de causa raiz com confiança "confirmada". Não use sem diagnóstico, nem para refatorar ou adicionar funcionalidade.
---

# Correção: aplicar o mínimo necessário

## Antes de mexer
- Confira se o diagnóstico tem reprodução e evidência. Se a confiança não for "confirmada", devolva para o dev-debug.
- Reproduza o erro você mesmo antes de corrigir. Se não reproduzir, pare e avise.
- Se discordar do diagnóstico, explique o motivo **antes** de agir diferente.

## Regras
- Corrija só a causa apontada. Nada de refatoração, renomeação ou melhoria "de passagem". Se enxergar algo, anote em "Fora do escopo".
- Siga o padrão do código ao redor.
- Mexeu em configuração, script de produção ou dados: descreva como desfazer antes de aplicar.
- Não mude dados reais para testar. Use cópia ou ambiente de teste.

## Validar
1. Repita os passos de reprodução: o erro não pode mais acontecer.
2. Teste os pontos listados em "Alcance" no diagnóstico.
3. Deixe um teste de regressão quando o projeto permitir. Se não houver suíte, deixe um checklist ou script de verificação.

## Saída (formato fixo)
- **O que mudou:** arquivos e trecho, em uma linha cada.
- **Por que resolve:** ligação entre a mudança e a causa raiz.
- **Validação:** comandos rodados e resultado, antes e depois.
- **Regressão:** o que foi testado ao redor.
- **Como desfazer:** passo concreto (reverter commit, restaurar configuração).
- **Risco residual:** o que não foi possível testar.
- **Fora do escopo:** problemas vistos e não tratados.
