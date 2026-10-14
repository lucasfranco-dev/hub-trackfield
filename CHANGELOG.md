# Histórico de mudanças

Todas as mudanças relevantes do Hub ficam registradas aqui, da mais recente para a mais antiga. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não publicado]

### Adicionado
- Repositório versionado, com o código do Apps Script em `src/`.
- Envio para o Apps Script com o clasp (`npm run publicar`) e publicação automática pelo GitHub Actions a cada mudança em `src/` na `main`. Sem o segredo `CLASPRC_JSON`, o workflow avisa e não publica.
- Manifesto `appsscript.json`, que publica o app da Web para qualquer pessoa, sem login.
- Implantação do app da Web criada; o ID fica em `package.json` (`config.deploymentId`).
- O `Code.gs` abre a planilha pelo ID quando o script não está vinculado a ela.

### Alterado
- Cache da lista de links reduzido de 5 minutos para 1 minuto, porque o script é independente e o gatilho de edição da planilha não dispara.

## [1.0.0] - 2026-10-14

### Adicionado
- Fase 1 do Hub: fachada com ripado e letreiro, vitrine com 8 paradas (manequins e cubos), transição com profundidade entre fundo, produtos e vidro, e barra com todos os links.
- Navegação por setas, teclado, roda do mouse, arrastar e deslizar no celular.
- Leitura dos links da planilha **Hub Track&Field: links**, com cache de 5 minutos e atualização imediata ao editar a planilha.
- Esboço do conceito visual em `docs/conceito/storyboard.html`.
