# Instruções para o Claude

Projeto: Hub de links da equipe Track&Field (Google Apps Script). Visão geral, estrutura e publicação estão no [README.md](README.md).

## Regras

- **Documentação sempre em dia.** Toda mudança atualiza, no mesmo commit, as seções do README que ela afeta e adiciona uma entrada em `## [Não publicado]` no CHANGELOG.md. Isso vale para mudanças de código, de estrutura, de fluxo de publicação e de planilha.
- **Tudo em português do Brasil**: código, comentários, commits e documentação.
- **Publicação:** o site (`web/` e `midia/`) vai para o GitHub Pages pelo workflow `publicar-site.yml`; o que chega na `main` com mudança em `src/` (servidor de dados) é enviado ao Apps Script pelo workflow `publicar.yml`. Se houver credenciais do clasp na sessão, também dá para publicar com `npm run publicar` (o ID da implantação está em `package.json`, `config.deploymentId`). Nunca crie uma implantação nova: atualize a existente, para a URL não mudar.
- **Credenciais:** nunca faça commit, imprima ou cole o `~/.clasprc.json` ou qualquer token.
- **Pré-visualização:** `sh scripts/montar-site.sh && python3 -m http.server -d _site 8080`; o site usa a API de verdade (links e consulta). A câmera da lupa só funciona em `localhost` ou HTTPS.
- **Segurança da página:** os links vêm de uma planilha editável e a consulta de produtos traz dados do site da TF. Monte o DOM com `textContent`, nunca `innerHTML` com esses dados; aceite só URLs `http(s)` nos links da planilha, e na consulta só imagens de `trackfield.vtexassets.com` e links de `www.tf.com.br`.
- **Vitrine 3D:** a cena inteira vem de `3d/vitrine.py`; não edite renders à mão nem faça commit de `.blend` ou de `3d/texturas/` (baixadas por `3d/baixar_texturas.sh`). Teste com `--previa` antes de um render completo.
- **Mídias da página:** o site publica `midia/` junto com as páginas e lê os arquivos por caminho relativo (`midia/`). Basta commit e push das mídias.
- **API do Apps Script:** o site fala com o servidor só por GET simples (`HUB.api` em `web/hub.js`), porque o Apps Script não responde ao preflight de CORS. Ações novas entram em `responderJson_` no `Code.gs`.
- **Permissões do Google:** um serviço novo no `Code.gs` (ex.: `UrlFetchApp`, Drive, Gmail) muda as permissões do projeto, e o Hub para de funcionar até a conta dona autorizar. Antes de publicar algo assim na `main` (que publica sozinha), envie só o código com `npx clasp push -f` (não muda a implantação), peça à pessoa para rodar uma função no editor e aceitar, e só então publique.
- **Dados de clientes:** as vendas anotadas na lupa (CPF, nome, telefone, endereço) ficam só no `localStorage` do aparelho. O site e a API são públicos e sem login: nunca envie esses dados ao Apps Script, à planilha ou a serviços externos, nem os escreva em logs.
