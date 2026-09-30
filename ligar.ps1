# Liga cada skill deste repositório às pastas de skills do Claude Code e do Codex por junction.
# Idempotente: pula o que já aponta para cá e recusa pasta real no caminho (não sobrescreve nada).
# Uso: powershell -ExecutionPolicy Bypass -File .\ligar.ps1

$repo = $PSScriptRoot
$destinos = @("$env:USERPROFILE\.claude\skills", "$env:USERPROFILE\.codex\skills")
$skills = Get-ChildItem $repo -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') }

foreach ($base in $destinos) {
  if (-not (Test-Path $base)) { New-Item -ItemType Directory -Path $base | Out-Null }
  foreach ($s in $skills) {
    $link = Join-Path $base $s.Name
    $item = Get-Item $link -Force -ErrorAction SilentlyContinue
    if ($null -eq $item) {
      New-Item -ItemType Junction -Path $link -Target $s.FullName | Out-Null
      Write-Output "criado   $link"
    } elseif ($item.LinkType -eq 'Junction' -and $item.Target -contains $s.FullName) {
      Write-Output "ok       $link"
    } else {
      Write-Output "RECUSADO $link (já existe e não aponta para este repositório; mova para backup e rode de novo)"
    }
  }
}
