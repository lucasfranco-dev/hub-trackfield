# Renderizar a vitrine no seu PC com o Claude

Este guia é para renderizar a vitrine 3D em qualidade máxima num PC com placa de vídeo, com o Claude rodando no próprio PC, e publicar o resultado no Hub. A sessão do Claude na nuvem não usa a sua placa de vídeo; uma sessão no PC usa.

## 1. O que instalar (uma vez)

| Programa | Para quê | Como |
|---|---|---|
| Driver da placa de vídeo | Render na GPU | NVIDIA: GeForce Experience ou o site da NVIDIA. AMD: Adrenalin. |
| Git para Windows | Baixar e enviar o projeto; traz o Git Bash, que o Claude usa para rodar os scripts | <https://git-scm.com/download/win> |
| Python 3.13 | Blender como módulo (`bpy`) | <https://www.python.org/downloads/>, marcando "Add python.exe to PATH". Precisa ser 3.13: o `bpy` 5.2.2 só existe para essa versão. |
| ffmpeg | Gerar os vídeos das transições | No PowerShell: `winget install Gyan.FFmpeg` (feche e abra o terminal depois) |
| Node.js LTS | Publicar no Apps Script (clasp) | <https://nodejs.org/> |
| Claude Code | O Claude trabalhando no seu PC | App Claude Desktop (parte de código) ou o comando `claude` num terminal |

## 2. Abrir o projeto

Num terminal (Git Bash ou PowerShell):

```sh
git clone https://github.com/lucasfranco-dev/hub-trackfield.git
```

Abra o Claude Code nessa pasta (`hub-trackfield`). Ele lê o `CLAUDE.md` sozinho, com as regras do projeto.

## 3. O pedido para colar no chat

Copie o texto abaixo inteiro e envie como primeira mensagem:

```text
Este é o projeto Hub Track&Field. Leia o CLAUDE.md e, no README.md, as seções "Vitrine 3D", "Renderizar em outro computador" e "Mídias da página". Estou no meu PC com placa de vídeo e quero renderizar a vitrine 3D em qualidade máxima e publicar no Hub. Siga estes passos, um de cada vez, e me mostre o resultado de cada um:

1. Ambiente: crie o venv .venv-blender com o Python 3.13 (python -m venv .venv-blender), instale bpy==5.2.2 e pillow nele, baixe as texturas com sh 3d/baixar_texturas.sh e rode sh 3d/verificar.sh. A placa de vídeo tem que aparecer como GPU. Se cair na CPU, descubra o motivo (driver, tipo OPTIX/CUDA/HIP) antes de seguir; não renderize na CPU.

2. Prévia: rode a parada 0 com --previa e DISPOSITIVO=GPU e me mostre a imagem. Diga quanto tempo levou.

3. Render: rode sh 3d/renderizar_maxima.sh em segundo plano e acompanhe até o fim. Se algo falhar, me mostre o erro antes de tentar de novo. No fim, me mostre uma folha com as 8 paradas (midia/paradas) e alguns quadros de uma transição, e diga quanto tempo levou e o tamanho dos arquivos de midia/.

4. Só depois da minha aprovação: faça o commit e o push de 3d/renders e midia/. Depois aponte a constante MIDIA de src/Index.html para o hash completo desse commit, atualize README e CHANGELOG (regra do CLAUDE.md), faça o commit e o push.

5. Publicar: se este PC ainda não tiver as credenciais do clasp, me peça para rodar npx clasp login no terminal (eu autorizo no navegador com a conta lucfpscs@gmail.com; nunca me peça o conteúdo do arquivo de credenciais). Depois rode npm ci e npm run publicar, abra a URL do Hub (está no README) e confira se as imagens e os vídeos novos aparecem no computador e no celular.
```

## 4. O que só você pode fazer

- Aprovar os comandos quando o Claude pedir permissão.
- Fazer login no GitHub no primeiro `git push` (abre uma janela do Git).
- Rodar `npx clasp login` e autorizar no navegador, com a conta dona do script (lucfpscs@gmail.com).
- Nunca colar no chat o conteúdo de `~/.clasprc.json` nem outro token.

## 5. O que esperar

| Etapa | Tempo aproximado |
|---|---|
| Instalar o `bpy` e baixar as texturas | 5 a 10 min (o `bpy` tem cerca de 400 MB) |
| Prévia de uma parada | menos de 1 min |
| `renderizar_maxima.sh` completo | 30 min a 2 h, conforme a placa |

O resultado: imagens das paradas com até 1920 px de largura (mais nítidas em telas grandes) e transições em 1600x1200 com desfoque de movimento. O logo em relevo da parede sai deste render, porque ficava atrás do nome do link na página.

Não rode o render no PC e na nuvem ao mesmo tempo: os dois escreveriam os mesmos arquivos.
