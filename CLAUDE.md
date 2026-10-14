# Instruções para o Claude

Projeto: Hub de links da equipe Track&Field (Google Apps Script). Visão geral, estrutura e publicação estão no [README.md](README.md).

## Regras

- **Documentação sempre em dia.** Toda mudança atualiza, no mesmo commit, as seções do README que ela afeta e adiciona uma entrada em `## [Não publicado]` no CHANGELOG.md. Isso vale para mudanças de código, de estrutura, de fluxo de publicação e de planilha.
- **Tudo em português do Brasil**: código, comentários, commits e documentação.
- **Publicação:** o que chega na `main` com mudança em `src/` é enviado ao Apps Script pelo workflow `publicar.yml`. Se houver credenciais do clasp na sessão, também dá para publicar com `npm run publicar` (o ID da implantação está em `package.json`, `config.deploymentId`). Nunca crie uma implantação nova: atualize a existente, para a URL não mudar.
- **Credenciais:** nunca faça commit, imprima ou cole o `~/.clasprc.json` ou qualquer token.
- **Pré-visualização:** `src/Index.html` funciona aberto direto no navegador (usa a lista `AMOSTRA`). Mantenha a `AMOSTRA` em sincronia com a planilha quando mudar campos.
- **Segurança da página:** os links vêm de uma planilha editável. Monte o DOM com `textContent`, nunca `innerHTML` com dados da planilha, e aceite só URLs `http(s)`.
- **Vitrine 3D:** a cena inteira vem de `3d/vitrine.py`; não edite renders à mão nem faça commit de `.blend` ou de `3d/texturas/` (baixadas por `3d/baixar_texturas.sh`). Teste com `--previa` antes de um render completo.
