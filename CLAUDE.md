# Instruções para o Claude

Projeto: Hub de links da equipe Track&Field (Google Apps Script). Visão geral, estrutura e publicação estão no [README.md](README.md).

## Regras

- **Documentação sempre em dia.** Toda mudança atualiza, no mesmo commit, as seções do README que ela afeta e adiciona uma entrada em `## [Não publicado]` no CHANGELOG.md. Isso vale para mudanças de código, de estrutura, de fluxo de publicação e de planilha.
- **Tudo em português do Brasil**: código, comentários, commits e documentação.
- **Publicação:** o que chega na `main` com mudança em `src/` é enviado ao Apps Script pelo workflow `publicar.yml`. Se houver credenciais do clasp na sessão, também dá para publicar com `DEPLOYMENT_ID=... npm run publicar`. Nunca crie uma implantação nova: atualize a existente, para a URL não mudar.
- **Credenciais:** nunca faça commit, imprima ou cole o `~/.clasprc.json` ou qualquer token.
- **Pré-visualização:** `src/Index.html` funciona aberto direto no navegador (usa a lista `AMOSTRA`). Mantenha a `AMOSTRA` em sincronia com a planilha quando mudar campos.
- **Segurança da página:** os links vêm de uma planilha editável. Monte o DOM com `textContent`, nunca `innerHTML` com dados da planilha, e aceite só URLs `http(s)`.
