# Histórico de mudanças

Todas as mudanças relevantes do Hub ficam registradas aqui, da mais recente para a mais antiga. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não publicado]

### Adicionado
- Manequins feminino e masculino realistas gerados do MakeHuman (MPFB 2, CC0), com braços relaxados e cabeça lisa sem rosto (`3d/gerar_manequins.py`, `3d/modelos/`).
- Produtos de todas as paradas (`3d/produtos.py`): casaco PowerCool, camiseta ThermoDry Gota, shorts Laser, jaqueta Winter acolchoada e camiseta Sports nos manequins; Mala Duffel Matelassê, Mala Trip e garrafa Urban nos cubos.
- Câmera por parada: corpo inteiro nos manequins, lente mais longa na altura do produto nos cubos.
- `3d/renderizar_todas.sh` renderiza as 8 paradas e gera os recortes.
- Renders das 8 paradas em 1600x1200, com recortes `.webp` para computador e celular, e folha de prévia em `docs/previa/vitrine-3d-paradas.jpg`.
- Fase 2: vitrine 3D montada por script no Blender (`3d/vitrine.py`), com fachada, ripado, letreiro, vidro, piso de madeira, parede com logo em relevo, spots e 8 paradas entre manequins e cubos.
- Render de teste da parada 1 e recortes para computador e celular (`3d/recortes.py`).

### Alterado
- O manequim feito por esqueleto simples foi substituído pelos manequins do MakeHuman; a haste entre as pernas saiu da base.
- Script para baixar as texturas CC0 do Poly Haven (`3d/baixar_texturas.sh`) e fonte Outfit com a licença OFL.
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
