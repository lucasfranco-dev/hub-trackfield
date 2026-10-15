# Hub da equipe Track&Field

Página de links da equipe com o tema da vitrine da loja. A câmera passa pela vitrine e cada manequim ou cubo leva a um site. Roda no Google Apps Script, sem login, e os links vêm de uma Planilha Google.

| | |
|---|---|
| Hub (endereço da equipe) | <https://script.google.com/macros/s/AKfycbxawbOdgqsfsxDmw7Tn0IR1l_76XcU93D5uxSl2q78mPSBlMnPn5A2DqqE8l1pIAR0bbQ/exec> |
| Planilha de links | [Hub Track&Field: links](https://docs.google.com/spreadsheets/d/1eSkaq6dsmBnoYOXWYdMJFE7LAEQMngrRszZE_ed4OUE/edit) |
| Projeto no Apps Script | [abrir no editor](https://script.google.com/d/1g-Re2_3aVLnRRAj_56KY8RO1RIAdNUp-9NhAM2XxMt5NHkWEf-Kkn_2c/edit) |
| Histórico de mudanças | [CHANGELOG.md](CHANGELOG.md) |

![Prévia no computador](docs/previa/computador.png)

## Estrutura

| Caminho | O que é |
|---|---|
| `src/Code.gs` | Servidor: lê a aba **Links** da planilha e entrega a página. |
| `src/Index.html` | A vitrine: visual, animações e navegação, num único arquivo. |
| `src/appsscript.json` | Manifesto do Apps Script: fuso horário e acesso do app da Web (qualquer pessoa, sem login). |
| `package.json` | Dependência do clasp e, em `config.deploymentId`, o ID da implantação do app da Web. |
| `scripts/publicar.sh` | Envia `src/` para o Apps Script e atualiza a implantação. |
| `.github/workflows/publicar.yml` | Roda o `publicar.sh` a cada mudança em `src/` na branch `main`. |
| `.clasp.json` | Liga a pasta `src/` ao projeto do Apps Script. |
| `3d/vitrine.py` | Monta a vitrine no Blender por script e renderiza uma parada (veja [Vitrine 3D](#vitrine-3d)). |
| `3d/produtos.py` | Veste os manequins com as roupas de cada parada e modela as malas e a garrafa. |
| `3d/gerar_manequins.py` | Gera os manequins feminino e masculino a partir do MakeHuman (MPFB 2, CC0). |
| `3d/modelos/` | Manequins prontos em `.glb`, com as regiões do corpo marcadas em cada vértice. |
| `3d/renderizar_todas.sh` | Renderiza as 8 paradas e gera as imagens da página. |
| `3d/exportar_midia.py` | Converte os renders das paradas nas imagens WebP da página (`midia/paradas/`). |
| `3d/renderizar_transicoes.sh` | Renderiza o travelling de câmera entre paradas vizinhas e gera os vídeos (`midia/transicoes/`). |
| `3d/baixar_texturas.sh` | Baixa as texturas de madeira (CC0, Poly Haven) para `3d/texturas/`, que fica fora do Git. |
| `3d/fontes/` | Fonte Outfit do letreiro (licença SIL OFL em `OFL.txt`). |
| `3d/renders/` | Renders originais das paradas (PNG 1600x1200). |
| `midia/` | Imagens e vídeos que a página carrega, servidos pelo jsDelivr (veja [Mídias da página](#mídias-da-página)). |
| `docs/` | Conceito visual (`conceito/storyboard.html`) e prévias da página. |

## Editar os links

Os links ficam na planilha, não no código. A mudança aparece no Hub em até 1 minuto (o script guarda a lista em cache por esse tempo).

| Coluna | Uso |
|---|---|
| Ordem | Posição na vitrine, da esquerda para a direita. |
| Ativo | Desmarque para esconder o link sem apagar a linha. |
| Nome | Texto do letreiro e da barra de links. |
| Categoria | Linha pequena acima do nome. |
| Descrição | Uma frase sobre o destino. |
| URL | Endereço completo, começando com `https://`. Outros formatos são ignorados. |
| Produto | Produto da vitrine 3D que representa o link (lista na própria coluna). Se ficar vazio ou não for um dos 8, o link usa a parada da mesma posição. |

## Desenvolvimento

1. `npm install`
2. Para ver a página sem publicar, abra `src/Index.html` no navegador. Fora do Apps Script ela usa os 8 links de exemplo que estão no próprio arquivo.
3. Faça a mudança, atualize a documentação (veja abaixo) e faça o commit na `main`.

Navegação da página: setas na tela, teclado (← →, Home, End, 1 a 9, Enter abre o link atual), roda do mouse, arrastar com o mouse ou deslizar o dedo, e a barra com todos os links. Entre produtos vizinhos na vitrine a câmera faz o travelling em vídeo; em saltos maiores, ou com "reduzir movimento" ligado no aparelho, a imagem troca com um fade.

## Publicação

O código publicado é sempre o que está na `main`.

**Automática.** Cada push na `main` que muda `src/` roda o workflow **Publicar no Apps Script**: ele envia os arquivos com o clasp e atualiza a implantação do app da Web. A URL da equipe não muda. Também dá para rodar o workflow à mão na aba **Actions**.

**Manual**, de um computador com as credenciais do clasp:

```sh
npm run publicar
```

O script envia `src/` com `clasp push` e atualiza a implantação cujo ID está em `package.json` (`config.deploymentId`). Nunca crie uma implantação nova: a URL da equipe mudaria.

### Configuração inicial (uma vez)

1. Ative a **API do Google Apps Script** em <https://script.google.com/home/usersettings>.
2. **Autorize o script:** abra a URL do Hub logado com a conta dona do script e aceite as permissões. Sem isso, quem não tem login vê "acesso negado".
3. **Credenciais para o GitHub Actions:** no seu computador, rode `npx @google/clasp login` e autorize com a conta dona do script. Isso cria o arquivo `~/.clasprc.json`. No GitHub, em **Settings → Secrets and variables → Actions → New repository secret**, crie `CLASPRC_JSON` com o conteúdo inteiro desse arquivo.

Sem o segredo, o workflow termina com um aviso e não publica. O `~/.clasprc.json` dá acesso aos seus scripts do Google: ele nunca entra no repositório (está no `.gitignore`) e não deve ser colado em conversas ou issues.

O script do Apps Script é independente, não vinculado à planilha. Ele abre a planilha pelo ID que está em `src/Code.gs` (`ID_PLANILHA`).

## Vitrine 3D

A loja é montada inteira por código em `3d/vitrine.py`, com o Blender como módulo Python (`bpy`) e render no Cycles:

- fachada com ripado de madeira e letreiro iluminado na fonte Outfit;
- vidro contínuo com reflexos das luminárias do corredor;
- piso de madeira, parede branca com o logo em relevo e fachos de luz dos spots;
- 8 paradas na ordem da planilha: manequins vestidos com os produtos e cubos de madeira com malas e garrafa.

![As 8 paradas da vitrine 3D](docs/previa/vitrine-3d-paradas.jpg)

**Manequins.** `gerar_manequins.py` usa o corpo base do MakeHuman pelo add-on MPFB 2 (licença CC0, sem login): proporções de manequim de loja, braços relaxados e cabeça lisa em forma de ovo, sem rosto. Cada vértice guarda a região do corpo (`_REGIAO`: tronco, braço, coxa...) e a posição ao longo do osso (`_T`). Os `.glb` já gerados estão em `3d/modelos/`; para gerar de novo é preciso o zip do MPFB (<https://extensions.blender.org/add-ons/mpfb/>):

```sh
.venv-blender/bin/python 3d/gerar_manequins.py --mpfb add-on-mpfb-v2.0.18.zip
```

**Produtos.** Em `produtos.py`, cada roupa é uma casca da superfície do manequim: escolhe as regiões que cobre, corta barra, punho e gola e se afasta do corpo alguns milímetros (ou mais, com gomos, na jaqueta acolchoada). Cores e detalhes seguem as fotos do site: os "pretos" da marca são um azul-marinho muito escuro, o shorts Laser é azul, o casaco tem zíper e gola alta, a camiseta ThermoDry tem o recorte em gota nas costas, a Sports tem logo e faixa refletivos. Malas e garrafa são modeladas por forma (matelassê em chevron da duffel, alças de mochila da Mala Trip, anel metálico e tampa com alça da garrafa).

| Parada | Produto | Expositor |
|---|---|---|
| 1 | Casaco PowerCool, com bermuda de ciclista | Manequim feminino |
| 2 | Mala Duffel Matelassê | Cubo |
| 3 | Camiseta ThermoDry Gota, com legging | Manequim feminino |
| 4 | Shorts Laser, com camiseta Sports | Manequim masculino |
| 5 | Jaqueta Winter, com bermuda caqui | Manequim masculino |
| 6 | Mala Trip | Cubo |
| 7 | Camiseta Sports, com legging | Manequim masculino |
| 8 | Garrafa Urban 950 ml | Cubo |

Para trocar o produto de uma parada, mude `PARADAS` em `vitrine.py` e, se for um produto novo, crie a função dele em `produtos.py`.

A câmera fica do lado de fora, sem inclinação (as verticais ficam retas), com o produto em 65% da largura. Nos manequins ela mostra o corpo inteiro; nos cubos usa uma lente mais longa, na altura do produto. O render sai em 4:3; a página recorta para a tela (no computador a vitrine é no máximo 1,8 vez mais larga que alta, para não cortar cabeças; no celular o recorte é vertical, centrado no produto).

**Transições.** Para cada par de paradas vizinhas, `vitrine.py --transicao` anima a câmera de uma até a outra (aceleração e frenagem suaves; a lente muda pelo ângulo de visão). São 23 quadros em 960x720 a 24 quadros por segundo: 1 segundo de travelling. Cada transição tem o vídeo de ida e o de volta (o mesmo, invertido), em MP4 (H.264) e WebM (VP9); a página escolhe o formato que o navegador toca.

### Renderizar

```sh
python3 -m venv .venv-blender && .venv-blender/bin/pip install bpy==5.2.2 pillow
sh 3d/baixar_texturas.sh
.venv-blender/bin/python 3d/vitrine.py --parada 0 --previa                    # 480x360, ~20 s
.venv-blender/bin/python 3d/vitrine.py --parada 0 --amostras 160              # 1600x1200, ~15 min em CPU de 4 núcleos
sh 3d/renderizar_todas.sh 96          # as 8 paradas (~12 min cada) e as imagens de midia/paradas/
sh 3d/renderizar_transicoes.sh        # as 7 transições (~12 min cada) e os vídeos de midia/transicoes/
```

### Mídias da página

A página carrega as imagens e os vídeos de `midia/` pelo jsDelivr, a partir de uma tag fixa do repositório (por isso o repositório é público): `https://cdn.jsdelivr.net/gh/lucasfranco-dev/hub-trackfield@midia-v1/midia/`. Uma tag nunca muda, então o cache da CDN não atrapalha. Para trocar as mídias:

1. Gere os arquivos novos em `midia/` e faça o commit.
2. Crie a próxima tag (`git tag midia-v2 && git push origin midia-v2`).
3. Troque `midia-v1` por `midia-v2` na constante `MIDIA` de `src/Index.html` e publique.

| Arquivo | Uso |
|---|---|
| `midia/paradas/parada-N.webp` | Imagem da parada N (0 a 7), 1600x1200, 20 a 35 KB |
| `midia/transicoes/transicao-N-ida.mp4` / `.webm` | Travelling da parada N até a N+1 |
| `midia/transicoes/transicao-N-volta.mp4` / `.webm` | O mesmo, de volta |

Opções de `vitrine.py`: `--parada` (0 a 7), `--largura`, `--altura`, `--amostras`, `--previa`, `--saida` e `--blend` (salva o arquivo `.blend` para abrir no Blender).

## Roteiro

| Fase | Conteúdo | Situação |
|---|---|---|
| 1 | Planilha, Apps Script e vitrine com fotos do site | Concluída |
| 2 | Cenário da loja no Blender e render de teste de uma parada | Cenário aprovado |
| 3 | Manequins e produtos em 3D, renders na página e transições em vídeo | Concluída |
| 4 | Acabamento, testes em celular e computador | A fazer |

## Créditos

- Corpo dos manequins: MakeHuman, pelo add-on MPFB 2 (CC0).
- Texturas de madeira: Poly Haven (CC0).
- Fonte Outfit: The Outfit Project Authors (SIL Open Font License 1.1, em `3d/fontes/OFL.txt`).

## Cuidados

- Qualquer pessoa com a URL vê a lista de links. Não coloque senhas nem links com token na planilha.
- Por ser uma conta pessoal, o Google mostra uma faixa no topo da página dizendo que o app foi criado por um usuário. Não dá para remover.

## Documentação

Toda mudança no projeto atualiza, no mesmo commit, o que ela afeta neste README e uma entrada no [CHANGELOG.md](CHANGELOG.md).
