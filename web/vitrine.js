(function () {
  'use strict';

  // Imagens e vídeos da vitrine 3D: a pasta midia/ publicada junto com o site.
  var MIDIA = 'midia/';

  // Paradas da vitrine 3D, na ordem em que a câmera passa (3d/vitrine.py).
  var VITRINE = ['Casaco PowerCool', 'Mala Duffel Matelassê', 'Camiseta ThermoDry', 'Shorts Laser',
                 'Jaqueta Winter', 'Mala Trip', 'Camiseta Sports', 'Garrafa Urban 950 ml'];

  var $ = function (id) { return document.getElementById(id); };
  var loja = $('loja'), vitrine = $('vitrine'), adesivo = $('adesivo'), alvo = $('alvoProduto');
  var indice = $('indice'), contador = $('contador'), anuncio = $('anuncio');
  var btnAnterior = $('anterior'), btnProxima = $('proxima');
  var quadros = [$('quadroA'), $('quadroB')];
  var frente = 0;  // índice em `quadros` da imagem visível
  var moldura = $('moldura');
  var faixas = moldura.querySelectorAll('.faixa');
  var faixaFrente = 0;  // índice em `faixas` da camada visível das laterais

  var reduzido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var links = [];
  var paradas = [];
  var montado = false;
  var atual = 0;
  var ocupado = false;
  var pedido = null;
  var videos = {};

  function normalizar(t) {
    return String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  // Parada da vitrine de cada link: pelo nome do produto na planilha, ou pela ordem.
  function paradaDoLink(link, i) {
    var alvoNome = normalizar(link.produto);
    for (var k = 0; k < VITRINE.length; k++) if (normalizar(VITRINE[k]) === alvoNome) return k;
    return i % VITRINE.length;
  }

  function urlSegura(url) { return /^https?:\/\//i.test(String(url || '')) ? url : null; }
  function srcQuadro(p) { return MIDIA + 'paradas/parada-' + p + '.webp'; }
  // MP4 (H.264) onde o navegador toca; senão WebM (VP9).
  var EXTENSAO_VIDEO = document.createElement('video').canPlayType('video/mp4; codecs="avc1.64001F"') ? '.mp4' : '.webm';
  function srcVideo(de, para) {
    return para === de + 1 ? MIDIA + 'transicoes/transicao-' + de + '-ida' + EXTENSAO_VIDEO
         : para === de - 1 ? MIDIA + 'transicoes/transicao-' + para + '-volta' + EXTENSAO_VIDEO : null;
  }

  function el(tag, classe, texto) {
    var n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texto) n.textContent = texto;
    return n;
  }

  var ICONE_ABRIR = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 11L11 5M6 5h5v5"/></svg>';

  // ------------------------------------------------------------ montagem

  // ------------------------------------------------------------ links da planilha
  // Os links vêm da API do Apps Script (planilha). A última lista fica guardada no aparelho:
  // a vitrine abre na hora com ela e se atualiza quando a resposta chega.

  function carregar() {
    var guardados = null;
    try { guardados = JSON.parse(localStorage.getItem(HUB.CHAVE_LINKS)); } catch (e) { /* sem cópia */ }
    if (Array.isArray(guardados) && guardados.length) definirLinks(guardados);
    HUB.api('links').then(function (r) {
      var novos = r.links || [];
      try { localStorage.setItem(HUB.CHAVE_LINKS, JSON.stringify(novos)); } catch (e) { /* armazenamento cheio ou bloqueado */ }
      if (!montado || JSON.stringify(novos) !== JSON.stringify(links)) definirLinks(novos);
    }).catch(function (e) {
      if (!montado) mostrarAviso('Não foi possível carregar os links', (e && e.message) || 'Verifique a internet e recarregue a página.');
    });
  }

  function definirLinks(lista) {
    links = lista;
    paradas = links.map(paradaDoLink);
    if (!links.length) return mostrarAviso('Nenhum link ativo', 'Marque a coluna Ativo na planilha para exibir os links aqui.');
    var aviso = vitrine.querySelector('.aviso');
    if (aviso) aviso.remove();
    if (!montado) return montar();
    // Atualização com a vitrine já aberta: refaz o índice e o adesivo, mantendo a posição.
    atual = Math.min(atual, links.length - 1);
    desenharIndice();
    preencherAdesivo(atual);
    marcar(atual, true);
    trocarQuadro(srcQuadro(paradas[atual]), true);
  }

  function desenharIndice() {
    indice.textContent = '';
    links.forEach(function (link, i) {
      var li = el('li');
      var b = el('button', null, link.nome);
      b.type = 'button';
      b.addEventListener('click', function () { irPara(i); });
      li.appendChild(b);
      indice.appendChild(li);
    });
  }

  function montar() {
    montado = true;
    desenharIndice();

    quadros[0].src = srcQuadro(paradas[0]);
    quadros[0].setAttribute('fetchpriority', 'high');
    trocarAmbiente(srcQuadro(paradas[0]));
    medirLaterais();
    if (window.ResizeObserver) new ResizeObserver(medirLaterais).observe(moldura);
    else window.addEventListener('resize', medirLaterais);
    preencherAdesivo(0);
    marcar(0, true);
    adesivo.classList.add('visivel');
    prepararVizinhos();
    ligarEventos();
    acenderQuandoPronto(quadros[0]);
  }

  function mostrarAviso(titulo, texto) {
    var anterior = vitrine.querySelector('.aviso');
    if (anterior) anterior.remove();
    var aviso = el('div', 'aviso');
    var caixa = el('div');
    caixa.appendChild(el('strong', null, titulo));
    caixa.appendChild(document.createTextNode(texto));
    aviso.appendChild(caixa);
    vitrine.appendChild(aviso);
    btnAnterior.disabled = btnProxima.disabled = true;
    acender();
  }

  function preencherAdesivo(i) {
    var link = links[i];
    var url = urlSegura(link.url);
    adesivo.textContent = '';
    adesivo.setAttribute('aria-label', (i + 1) + ' de ' + links.length);
    var placa = el('div', 'placa');
    var texto = el('div', 'texto');
    if (link.categoria) texto.appendChild(el('p', 'categoria', link.categoria));
    texto.appendChild(el('h2', 'nome', link.nome));
    if (link.descricao) texto.appendChild(el('p', 'descricao', link.descricao));
    placa.appendChild(texto);
    adesivo.appendChild(placa);
    if (url) {
      var abrir = el('a', 'abrir');
      abrir.href = url;
      abrir.target = '_blank';
      abrir.rel = 'noopener noreferrer';
      abrir.textContent = 'Abrir';
      abrir.insertAdjacentHTML('beforeend', ICONE_ABRIR);
      abrir.setAttribute('aria-label', 'Abrir ' + link.nome + ' em nova aba');
      placa.appendChild(abrir);
      alvo.href = url;
    } else {
      alvo.removeAttribute('href');
    }
  }

  function marcar(i, inicial) {
    Array.prototype.forEach.call(indice.querySelectorAll('button'), function (b, k) {
      b.setAttribute('aria-current', k === i ? 'true' : 'false');
    });
    btnAnterior.disabled = i === 0;
    btnProxima.disabled = i === links.length - 1;
    contador.textContent = (i + 1) + ' de ' + links.length;
    var b = indice.querySelectorAll('button')[i];
    if (b) indice.scrollTo({ left: b.offsetLeft - (indice.clientWidth - b.offsetWidth) / 2, behavior: inicial ? 'auto' : 'smooth' });
    if (!inicial) anuncio.textContent = links[i].nome + ', ' + (i + 1) + ' de ' + links.length;
  }

  // ------------------------------------------------------------ mídia

  // Pré-carrega as imagens dos vizinhos e os vídeos das transições possíveis a partir daqui.
  function prepararVizinhos() {
    [atual - 1, atual + 1].forEach(function (i) {
      if (i < 0 || i >= links.length) return;
      new Image().src = srcQuadro(paradas[i]);
      if (!reduzido) obterVideo(srcVideo(paradas[atual], paradas[i]));
    });
    // Depois do primeiro instante, carrega o resto das imagens sem pressa.
    setTimeout(function () { paradas.forEach(function (p) { new Image().src = srcQuadro(p); }); }, 2500);
  }

  function obterVideo(src) {
    if (!src) return null;
    if (videos[src]) return videos[src];
    var v = document.createElement('video');
    v.className = 'travelling';
    v.muted = true;
    v.defaultMuted = true;
    v.playsInline = true;
    v.setAttribute('playsinline', '');
    v.setAttribute('aria-hidden', 'true');
    v.preload = 'auto';
    v.src = src;
    vitrine.insertBefore(v, alvo);
    videos[src] = v;
    return v;
  }

  function carregarImagem(img, src) {
    return new Promise(function (ok) {
      if (img.getAttribute('src') === src && img.complete && img.naturalWidth) return ok();
      img.onload = img.onerror = function () { ok(); };
      img.src = src;
      if (img.decode) img.decode().then(ok, ok);
    });
  }

  function videoPronto(v, ms) {
    return new Promise(function (ok) {
      if (v.readyState >= 3) return ok(true);
      var feito = false;
      var fim = function (r) { if (!feito) { feito = true; ok(r); } };
      v.addEventListener('canplaythrough', function () { fim(true); }, { once: true });
      setTimeout(function () { fim(v.readyState >= 3); }, ms);
    });
  }

  // Troca a imagem visível por outra, com fade (ou na hora, com `instantaneo`).
  function trocarQuadro(src, instantaneo) {
    var atras = quadros[1 - frente];
    return carregarImagem(atras, src).then(function () {
      if (instantaneo) atras.style.transition = 'none';
      atras.classList.remove('fundo', 'saindo');
      atras.classList.add('frente');
      void atras.offsetWidth;  // aplica a troca antes de devolver a transição
      var antes = quadros[frente];
      antes.classList.remove('frente');
      antes.classList.add('fundo');
      frente = 1 - frente;
      return new Promise(function (ok) {
        setTimeout(function () {
          antes.classList.add('saindo');
          atras.style.transition = '';
          ok();
        }, instantaneo ? 0 : 460);
      });
    });
  }

  // Laterais (telas mais largas que a vitrine): troca a cena espelhada e desfocada
  // com fade, a nova camada por cima da antiga, para não aparecer o fundo no meio.
  function trocarAmbiente(src) {
    var nova = faixas[1 - faixaFrente], antiga = faixas[faixaFrente];
    faixaFrente = 1 - faixaFrente;
    var imgs = nova.querySelectorAll('img');
    return Promise.all(Array.prototype.map.call(imgs, function (img) {
      return carregarImagem(img, src);
    })).then(function () {
      if (nova !== faixas[faixaFrente]) return;  // já houve outra troca depois desta
      antiga.classList.remove('topo');
      nova.classList.add('topo', 'visivel');
      setTimeout(function () {
        if (antiga !== faixas[faixaFrente]) antiga.classList.remove('visivel');
      }, 950);
    });
  }

  // Liga as laterais só quando sobra espaço ao lado da vitrine (além do padding).
  function medirLaterais() {
    var estilo = getComputedStyle(moldura);
    var livre = moldura.clientWidth - parseFloat(estilo.paddingLeft) - parseFloat(estilo.paddingRight);
    moldura.classList.toggle('larga', livre - vitrine.offsetWidth > 2);
  }

  // ------------------------------------------------------------ navegação

  function irPara(i) {
    i = Math.max(0, Math.min(links.length - 1, i));
    if (i === atual) return;
    if (ocupado) { pedido = i; return; }
    ocupado = true;
    var de = atual;
    atual = i;
    marcar(i);
    adesivo.classList.remove('visivel');

    var destino = srcQuadro(paradas[i]);
    trocarAmbiente(destino);
    var video = reduzido ? null : obterVideo(srcVideo(paradas[de], paradas[i]));
    var passo = video ? videoPronto(video, 450).then(function (pronto) {
      return pronto ? tocarTravelling(video, destino) : trocarQuadro(destino);
    }) : trocarQuadro(destino, reduzido);

    passo.then(function () {
      preencherAdesivo(i);
      requestAnimationFrame(function () { adesivo.classList.add('visivel'); });
      ocupado = false;
      prepararVizinhos();
      if (pedido !== null) { var p = pedido; pedido = null; irPara(p); }
    });
  }

  // O vídeo cobre a imagem atual, faz o travelling e, no fim, a imagem do destino
  // (já carregada por trás) fica no lugar dele.
  function tocarTravelling(video, destino) {
    return new Promise(function (ok) {
      var atras = quadros[1 - frente];
      var preparo = carregarImagem(atras, destino);
      video.currentTime = 0;
      video.classList.add('visivel');
      var terminou = function () {
        preparo.then(function () {
          trocarQuadro(destino, true).then(function () {
            video.classList.remove('visivel');
            ok();
          });
        });
      };
      video.addEventListener('ended', terminou, { once: true });
      var tocando = video.play();
      if (tocando && tocando.catch) tocando.catch(function () {
        video.removeEventListener('ended', terminou);
        video.classList.remove('visivel');
        trocarQuadro(destino).then(ok);
      });
    });
  }

  function abrirAtual() {
    var a = adesivo.querySelector('.abrir');
    if (a) a.click();
  }

  function ligarEventos() {
    btnAnterior.addEventListener('click', function () { irPara(atual - 1); });
    btnProxima.addEventListener('click', function () { irPara(atual + 1); });

    document.addEventListener('keydown', function (e) {
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      // Com a consulta aberta, ou digitando em um campo, as teclas não mexem na vitrine.
      if (document.querySelector('dialog[open]') || e.target.closest('input, textarea')) return;
      if (e.key === 'ArrowRight') { irPara(atual + 1); e.preventDefault(); }
      else if (e.key === 'ArrowLeft') { irPara(atual - 1); e.preventDefault(); }
      else if (e.key === 'Home') { irPara(0); e.preventDefault(); }
      else if (e.key === 'End') { irPara(links.length - 1); e.preventDefault(); }
      else if (/^[1-9]$/.test(e.key)) irPara(Number(e.key) - 1);
      else if (e.key === 'Enter' && (e.target === document.body || e.target === vitrine)) abrirAtual();
    });

    // Roda do mouse ou trackpad: um passo por gesto.
    var acumulado = 0, travadoAte = 0;
    vitrine.addEventListener('wheel', function (e) {
      e.preventDefault();
      var agora = Date.now();
      if (agora < travadoAte) return;
      acumulado += Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
      if (Math.abs(acumulado) > 40) {
        irPara(atual + (acumulado > 0 ? 1 : -1));
        acumulado = 0;
        travadoAte = agora + 900;
      }
    }, { passive: false });

    // Deslizar o dedo (ou arrastar o mouse) para os lados troca de link.
    var inicioX = null, inicioY = 0, inicioT = 0, arrastou = false;
    vitrine.addEventListener('pointerdown', function (e) {
      if (e.button !== 0 || e.target.closest('.seta, .abrir')) return;
      inicioX = e.clientX; inicioY = e.clientY; inicioT = performance.now(); arrastou = false;
    });
    vitrine.addEventListener('pointermove', function (e) {
      if (inicioX !== null && Math.abs(e.clientX - inicioX) > 10) arrastou = true;
    });
    vitrine.addEventListener('pointerup', function (e) {
      if (inicioX === null) return;
      var dx = e.clientX - inicioX, dy = e.clientY - inicioY;
      var rapido = Math.abs(dx) / Math.max(1, performance.now() - inicioT) > 0.4;
      if (Math.abs(dx) > Math.abs(dy) && (Math.abs(dx) > vitrine.clientWidth * 0.15 || (rapido && Math.abs(dx) > 30))) {
        irPara(atual + (dx < 0 ? 1 : -1));
      }
      inicioX = null;
    });
    vitrine.addEventListener('pointercancel', function () { inicioX = null; });
    // Um arraste não pode virar clique no produto.
    alvo.addEventListener('click', function (e) { if (arrastou) { e.preventDefault(); arrastou = false; } });
  }

  function acender() { requestAnimationFrame(function () { loja.classList.add('acesa'); }); }

  // Acende a loja quando a primeira imagem chega (ou depois de 1,2 s, o que vier antes).
  function acenderQuandoPronto(img) {
    var feito = false;
    var vai = function () { if (!feito) { feito = true; acender(); } };
    if (img.complete && img.naturalWidth) return vai();
    img.addEventListener('load', vai, { once: true });
    img.addEventListener('error', vai, { once: true });
    setTimeout(vai, 1200);
  }

  carregar();
})();
