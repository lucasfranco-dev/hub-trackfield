// Lupa do Hub: consulta de produtos, soma de produtos e vendas anotadas para lançar depois,
// com leitor de código de barras ao vivo.
//
// Consulta: busca por EAN, código TF (com ou sem a cor) ou parte do nome e mostra foto, nome,
// código, cor e preços. Soma: cada código bipado entra numa lista e o total soma sozinho; dá
// para mudar a quantidade, remover (com desfazer) e limpar. "Anotar venda" guarda os itens da
// soma com os dados do cliente; a venda fica em Pendentes até ser marcada como lançada.
// A soma e as vendas ficam só neste aparelho (localStorage): nada do cliente vai para o servidor.
// Os produtos vêm do site tf.com.br pela API do Hub (buscarProduto, em src/Code.gs).
(function () {
  'use strict';

  // Leitor para navegadores sem BarcodeDetector nativo (iPhone, Firefox, Windows). É a mesma
  // biblioteca do sistema de contagem de estoque, baseada no ZXing.
  var LIB_LEITOR = 'https://cdn.jsdelivr.net/npm/barcode-detector@3.2.3/pure/+esm';
  var FORMATOS = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128'];
  var PAUSA_MESMO_CODIGO = 1200;  // ms que um código precisa sumir da câmera para contar de novo
  var SITE = 'https://www.tf.com.br/';
  var IMAGENS = 'https://trackfield.vtexassets.com/';
  var CHAVE_SOMA = 'hub-soma-v1';
  var CHAVE_MODO = 'hub-lupa-modo';
  var CHAVE_VENDAS = 'hub-vendas-v1';
  // Em celular e tablet, focar o campo abre o teclado e atrapalha quem só quer bipar.
  var TOQUE = window.matchMedia('(hover: none), (pointer: coarse)').matches;
  var EAN = /^\d{8,14}$/;

  var $ = function (id) { return document.getElementById(id); };
  var dialogo = $('lupaPainel'), form = $('lupaForm'), campo = $('lupaCampo'), enviar = $('lupaEnviar');
  var botaoCamera = $('botaoCamera'), camera = $('camera'), video = $('cameraVideo'), leitura = $('leitura');
  var status = $('lupaStatus');
  var abaConsulta = $('modoConsulta'), abaSoma = $('modoSoma'), contagemAba = $('somaQtd');
  var painelConsulta = $('painelConsulta'), resultados = $('resultados');
  var painelSoma = $('painelSoma'), somaBusca = $('somaBusca'), somaItens = $('somaItens'), somaVazia = $('somaVazia');
  var somaTotal = $('somaTotal'), somaResumo = $('somaResumo'), somaEconomia = $('somaEconomia'), somaValor = $('somaValor');
  var limpar = $('limparSoma');
  var abaPendentes = $('modoPendentes'), contagemPendentes = $('pendentesQtd');
  var painelPendentes = $('painelPendentes'), listaPendentes = $('listaPendentes'), pendentesVazia = $('pendentesVazia');
  var painelVenda = $('painelVenda'), vendaItens = $('vendaItens'), vendaTotal = $('vendaTotal'), camposNovo = $('camposNovo');
  var ABAS = { consulta: abaConsulta, soma: abaSoma, pendentes: abaPendentes };
  var dataHora = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  var reais = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

  var modo = 'consulta';
  var pedido = 0;
  var soma = lerSoma();
  var buscandoEan = {};
  var removido = null;  // último item removido, para desfazer
  var vendas = lerLista(CHAVE_VENDAS);
  var anotando = false;  // formulário "Anotar venda" aberto por cima da soma
  var lancada = null;    // última venda marcada como lançada, para desfazer
  var leitor = { ativo: false, abrindo: false, stream: null, detector: null, ultimo: '', visto: 0, audio: null };

  // ------------------------------------------------------------ utilidades

  function el(tag, classe, texto) {
    var n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texto != null) n.textContent = texto;
    return n;
  }

  function icone(caminho) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', caminho);
    svg.appendChild(p);
    return svg;
  }

  // Mensagem da lupa; com `acao`, mostra um botão junto (ex.: Desfazer).
  function avisar(texto, erro, acao) {
    status.textContent = texto;
    status.classList.toggle('erro', !!erro);
    if (acao) {
      var b = el('button', 'link-acao', acao.rotulo);
      b.type = 'button';
      b.addEventListener('click', acao.fazer);
      status.appendChild(document.createTextNode(' '));
      status.appendChild(b);
    }
  }

  function sinal(tipo) {
    try { if (navigator.vibrate) navigator.vibrate(tipo === 'ok' ? 40 : [90, 60, 90]); } catch (e) { /* sem vibração */ }
    try {
      var ctx = leitor.audio;
      if (!ctx) return;
      var osc = ctx.createOscillator(), volume = ctx.createGain();
      osc.frequency.value = tipo === 'ok' ? 1250 : 320;
      volume.gain.value = 0.08;
      osc.connect(volume);
      volume.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + (tipo === 'ok' ? 0.08 : 0.3));
    } catch (e) { /* sem som */ }
  }

  function buscarProduto(termo) {
    return HUB.api('produto', { q: termo }).then(function (r) { return r.produtos || []; });
  }

  function descontoDe(p) { return p.preco > 0 && p.precoCheio - p.preco > 0.009; }

  function textoCor(p) { return 'Cor ' + [p.corCodigo, p.corNome].filter(Boolean).join(' '); }

  function textoTamanho(t) { return t === 'UNICO' ? 'Único' : t; }

  function foto(p, classe) {
    var img = el('img', classe);
    img.alt = '';
    img.loading = 'lazy';
    img.decoding = 'async';
    if (String(p.imagem).indexOf(IMAGENS) === 0) img.src = p.imagem;
    return img;
  }

  function amostraCor(p) {
    if (!/^#[0-9a-f]{6}$/i.test(p.corHex)) return null;
    var a = el('span', 'amostra-cor');
    a.style.background = p.corHex;
    a.setAttribute('aria-hidden', 'true');
    return a;
  }

  // ------------------------------------------------------------ abrir, fechar e modos

  function abrir() {
    if (!dialogo.open) dialogo.showModal();
    campo.focus();
    campo.select();
  }

  function focarCampo() { if (!TOQUE) campo.focus(); }

  // Troca de aba. Não foca o campo em aparelhos de toque (abriria o teclado).
  function definirModo(novo) {
    modo = novo;
    anotando = false;
    if (modo !== 'pendentes') {
      try { localStorage.setItem(CHAVE_MODO, modo); } catch (e) { /* sem armazenamento */ }
    }
    enviar.textContent = modo === 'soma' ? 'Adicionar' : 'Buscar';
    campo.placeholder = modo === 'soma' ? 'Bipe ou digite o código' : 'EAN, código TF ou nome do produto';
    avisar('');
    mostrarVista();
  }

  // Mostra o painel da aba atual, ou o formulário de venda por cima da soma.
  function mostrarVista() {
    Object.keys(ABAS).forEach(function (m) {
      ABAS[m].setAttribute('aria-selected', String(m === modo));
      ABAS[m].tabIndex = m === modo ? 0 : -1;
    });
    painelConsulta.hidden = modo !== 'consulta';
    painelSoma.hidden = modo !== 'soma' || anotando;
    painelVenda.hidden = !(modo === 'soma' && anotando);
    painelPendentes.hidden = modo !== 'pendentes';
    // Pendentes e o formulário de venda não usam a busca nem a câmera.
    var semBusca = modo === 'pendentes' || anotando;
    dialogo.classList.toggle('sem-busca', semBusca);
    if (semBusca) desligarCamera();
    desenharSoma();
    desenharPendentes();
  }

  // ------------------------------------------------------------ consulta

  function consultar(termo) {
    termo = String(termo || '').trim();
    if (termo.length < 2) { avisar('Digite pelo menos 2 caracteres.', true); return; }
    var meu = ++pedido;
    var lista = modo === 'soma' ? somaBusca : resultados;
    lista.textContent = '';
    lista.setAttribute('aria-busy', 'true');
    avisar('Buscando "' + termo + '" no site da Track&Field…');
    buscarProduto(termo).then(function (produtos) {
      if (meu !== pedido) return;
      if (!produtos.length) {
        avisar('Nada encontrado para "' + termo + '". Confira o código ou tente parte do nome.', true);
        return;
      }
      if (modo === 'soma') {
        avisar(produtos.length === 1 ? 'Toque em Adicionar para somar.' : produtos.length + ' produtos encontrados: toque no que quer somar.');
      } else {
        avisar(produtos.length === 1 ? '1 produto encontrado.' : produtos.length + ' produtos encontrados.');
      }
      produtos.forEach(function (p) { lista.appendChild(cartao(p, modo === 'soma')); });
    }, function (e) {
      if (meu === pedido) avisar(e.message, true);
    }).then(function () { if (meu === pedido) lista.removeAttribute('aria-busy'); });
  }

  function cartao(p, comAdicionar) {
    var li = el('li', 'produto-consulta');
    li.appendChild(foto(p));
    var corpo = el('div');
    corpo.appendChild(el('h3', null, p.nome));
    var ficha = el('p', 'ficha');
    ficha.appendChild(document.createTextNode((p.modelo || p.referencia) + ' · '));
    var cor = el('span', 'cor');
    var amostra = amostraCor(p);
    if (amostra) cor.appendChild(amostra);
    cor.appendChild(document.createTextNode(textoCor(p)));
    ficha.appendChild(cor);
    // Tamanho e EAN só vêm na busca por código de barras: o EAN é de um tamanho só.
    if (p.tamanho) {
      ficha.appendChild(document.createTextNode(' · Tam. ' + textoTamanho(p.tamanho)));
      if (p.ean) { ficha.appendChild(el('br')); ficha.appendChild(document.createTextNode('EAN ' + p.ean)); }
    }
    corpo.appendChild(ficha);
    corpo.appendChild(precos(p));
    var acoes = el('div', 'acoes-cartao');
    if (comAdicionar) {
      var b = el('button', 'botao pequeno primario', 'Adicionar à soma');
      b.type = 'button';
      b.addEventListener('click', function () {
        somarProduto(p);
        somaBusca.textContent = '';
        campo.value = '';
        focarCampo();
      });
      acoes.appendChild(b);
    }
    if (String(p.link).indexOf(SITE) === 0) {
      var a = el('a', 'ver-site', 'Ver no site');
      a.href = p.link;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      acoes.appendChild(a);
    }
    corpo.appendChild(acoes);
    li.appendChild(corpo);
    return li;
  }

  function precos(p) {
    var bloco = el('div', 'precos');
    if (p.preco > 0) bloco.appendChild(el('span', 'preco', reais.format(p.preco)));
    if (descontoDe(p)) {
      var cheio = el('span', 'preco-cheio');
      cheio.appendChild(document.createTextNode('de '));
      cheio.appendChild(el('s', null, reais.format(p.precoCheio)));
      bloco.appendChild(cheio);
      bloco.appendChild(el('span', 'selo', '−' + Math.round((1 - p.preco / p.precoCheio) * 100) + '%'));
    }
    if (p.disponivel === false) bloco.appendChild(el('span', 'selo esgotado', 'Esgotado no site'));
    return bloco;
  }

  // ------------------------------------------------------------ soma

  function lerLista(chave) {
    try {
      var s = JSON.parse(localStorage.getItem(chave));
      return Array.isArray(s) ? s : [];
    } catch (e) { return []; }
  }

  function lerSoma() { return lerLista(CHAVE_SOMA); }

  function guardarSoma() {
    try { localStorage.setItem(CHAVE_SOMA, JSON.stringify(soma)); } catch (e) { /* sem armazenamento */ }
  }

  // Um item por EAN (produto + tamanho). Busca por nome ou TF não traz tamanho: aí a chave é a referência.
  function chaveDe(p) { return p.tamanho && p.ean ? 'ean:' + p.ean : 'ref:' + p.referencia; }

  function somarProduto(p, origem) {
    var chave = chaveDe(p);
    var item = soma.filter(function (i) { return i.chave === chave; })[0];
    if (item) {
      item.qtd += 1;
      soma.splice(soma.indexOf(item), 1);
    } else {
      item = {
        chave: chave, nome: p.nome, modelo: p.modelo || p.referencia, referencia: p.referencia, corCodigo: p.corCodigo,
        corNome: p.corNome, corHex: p.corHex, tamanho: p.tamanho, ean: p.ean, imagem: p.imagem,
        preco: p.preco, precoCheio: p.precoCheio, qtd: 1
      };
    }
    soma.unshift(item);
    guardarSoma();
    desenharSoma(chave);
    avisar((item.qtd > 1 ? item.qtd + '× ' : '') + item.nome + ' (' + textoCor(item) + (item.tamanho ? ', ' + textoTamanho(item.tamanho) : '') + ') na soma.');
    if (origem === 'camera') mostrarLeitura('✓ ' + item.nome, 'ok');
  }

  // Código bipado ou digitado no modo soma. O mesmo EAN de novo só aumenta a quantidade.
  function somarEan(ean, origem) {
    // O bipe da câmera toca em receberCodigo, na hora da leitura; aqui só o som de erro.
    var jaTem = soma.filter(function (i) { return i.chave === 'ean:' + ean; })[0];
    if (jaTem) return somarProduto(jaTem, origem);
    if (buscandoEan[ean]) return;
    buscandoEan[ean] = true;
    avisar('Buscando ' + ean + ' no site da Track&Field…');
    if (origem === 'camera') mostrarLeitura('Buscando ' + ean + '…', '');
    buscarProduto(ean).then(function (produtos) {
      var p = produtos.filter(function (x) { return x.ean === ean; })[0];
      if (!p) {
        sinal('erro');
        avisar('O código ' + ean + ' não está no site da Track&Field.', true);
        if (origem === 'camera') mostrarLeitura('Código ' + ean + ' não encontrado', 'erro');
        return;
      }
      somarProduto(p, origem);
    }, function (e) {
      sinal('erro');
      avisar(e.message, true);
      if (origem === 'camera') mostrarLeitura('Não consegui buscar ' + ean, 'erro');
    }).then(function () { delete buscandoEan[ean]; });
  }

  function mudarQtd(item, delta) {
    if (item.qtd + delta <= 0) return remover(item);
    item.qtd += delta;
    guardarSoma();
    desenharSoma();
  }

  function remover(item) {
    var posicao = soma.indexOf(item);
    soma.splice(posicao, 1);
    removido = { item: item, posicao: posicao };
    guardarSoma();
    desenharSoma();
    avisar(item.nome + ' saiu da soma.', false, { rotulo: 'Desfazer', fazer: desfazer });
  }

  function desfazer() {
    if (!removido) return;
    soma.splice(Math.min(removido.posicao, soma.length), 0, removido.item);
    var chave = removido.item.chave;
    removido = null;
    guardarSoma();
    desenharSoma(chave);
    avisar('Item de volta na soma.');
  }

  var confirmarLimpar = 0;
  function limparSoma() {
    if (Date.now() - confirmarLimpar > 3000) {
      confirmarLimpar = Date.now();
      limpar.textContent = 'Toque de novo para limpar';
      setTimeout(function () { limpar.textContent = 'Limpar soma'; }, 3000);
      return;
    }
    confirmarLimpar = 0;
    limpar.textContent = 'Limpar soma';
    soma = [];
    removido = null;
    guardarSoma();
    desenharSoma();
    avisar('Soma limpa.');
    focarCampo();
  }

  function desenharSoma(destaque) {
    var unidades = soma.reduce(function (t, i) { return t + i.qtd; }, 0);
    contagemAba.textContent = unidades;
    contagemAba.hidden = !unidades;
    somaItens.textContent = '';
    somaVazia.hidden = soma.length > 0;
    somaTotal.hidden = modo !== 'soma' || anotando || !soma.length;
    soma.forEach(function (item) { somaItens.appendChild(linhaSoma(item, item.chave === destaque)); });

    var total = soma.reduce(function (t, i) { return t + i.preco * i.qtd; }, 0);
    var cheio = soma.reduce(function (t, i) { return t + Math.max(i.precoCheio, i.preco) * i.qtd; }, 0);
    somaResumo.textContent = unidades === 1 ? '1 item' : unidades + ' itens';
    somaValor.textContent = reais.format(total);
    somaEconomia.textContent = cheio - total > 0.009
      ? 'Sem desconto ' + reais.format(cheio) + ' · economia de ' + reais.format(cheio - total) : '';
  }

  function linhaSoma(item, destacar) {
    var li = el('li', 'item-soma' + (destacar ? ' novo' : ''));
    li.appendChild(foto(item, 'miniatura'));
    var info = el('div', 'item-info');
    info.appendChild(el('p', 'item-nome', item.nome));
    var ficha = el('p', 'ficha');
    var cor = el('span', 'cor');
    var amostra = amostraCor(item);
    if (amostra) cor.appendChild(amostra);
    cor.appendChild(document.createTextNode(textoCor(item)));
    ficha.appendChild(cor);
    if (item.tamanho) ficha.appendChild(document.createTextNode(' · ' + textoTamanho(item.tamanho)));
    info.appendChild(ficha);
    var unit = el('p', 'item-unitario');
    unit.appendChild(document.createTextNode(reais.format(item.preco)));
    if (descontoDe(item)) {
      unit.appendChild(document.createTextNode(' '));
      unit.appendChild(el('s', null, reais.format(item.precoCheio)));
    }
    info.appendChild(unit);
    li.appendChild(info);

    var lado = el('div', 'item-lado');
    lado.appendChild(el('p', 'item-total', reais.format(item.preco * item.qtd)));
    var qtd = el('div', 'quantidade');
    var menos = el('button', 'qtd-botao');
    menos.type = 'button';
    menos.setAttribute('aria-label', item.qtd === 1 ? 'Remover ' + item.nome : 'Diminuir quantidade de ' + item.nome);
    menos.appendChild(icone(item.qtd === 1 ? 'M4 7h16M9 7V5h6v2M7 7l1 13h8l1-13' : 'M6 12h12'));
    menos.addEventListener('click', function () { mudarQtd(item, -1); });
    var numero = el('span', 'qtd-numero', String(item.qtd));
    numero.setAttribute('aria-label', item.qtd + (item.qtd === 1 ? ' unidade' : ' unidades'));
    var mais = el('button', 'qtd-botao');
    mais.type = 'button';
    mais.setAttribute('aria-label', 'Aumentar quantidade de ' + item.nome);
    mais.appendChild(icone('M12 6v12M6 12h12'));
    mais.addEventListener('click', function () { mudarQtd(item, 1); });
    qtd.appendChild(menos);
    qtd.appendChild(numero);
    qtd.appendChild(mais);
    lado.appendChild(qtd);
    if (item.qtd > 1) {
      var tirar = el('button', 'link-acao pequeno', 'Remover');
      tirar.type = 'button';
      tirar.setAttribute('aria-label', 'Remover ' + item.nome + ' da soma');
      tirar.addEventListener('click', function () { remover(item); });
      lado.appendChild(tirar);
    }
    li.appendChild(lado);
    return li;
  }

  // ------------------------------------------------------------ anotar venda
  // O vendedor anota a venda no celular para lançar depois no computador da loja. Os dados do
  // cliente ficam só neste aparelho e são apagados quando a venda é marcada como lançada.

  function digitos(v) { return String(v || '').replace(/\D/g, ''); }

  function formatarCpf(v) {
    var d = digitos(v).slice(0, 11);
    return d.replace(/^(\d{3})(\d)/, '$1.$2').replace(/^(\d{3}\.\d{3})(\d)/, '$1.$2').replace(/^(\d{3}\.\d{3}\.\d{3})(\d)/, '$1-$2');
  }

  function formatarTelefone(v) {
    var d = digitos(v).slice(0, 11);
    if (d.length <= 2) return d.length ? '(' + d : '';
    var meio = d.length > 10 ? 7 : 6;
    return '(' + d.slice(0, 2) + ') ' + d.slice(2, meio) + (d.length > meio ? '-' + d.slice(meio) : '');
  }

  function formatarCep(v) {
    var d = digitos(v).slice(0, 8);
    return d.length > 5 ? d.slice(0, 5) + '-' + d.slice(5) : d;
  }

  // Confere os dois dígitos verificadores do CPF, para pegar erro de digitação na hora.
  function cpfValido(v) {
    var d = digitos(v);
    if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
    for (var t = 9; t < 11; t++) {
      var soma_ = 0;
      for (var k = 0; k < t; k++) soma_ += Number(d[k]) * (t + 1 - k);
      if (Number(d[t]) !== (soma_ * 10) % 11 % 10) return false;
    }
    return true;
  }

  var CAMPOS = {
    vendaCpf: { formatar: formatarCpf, validar: function (v) { return cpfValido(v) ? '' : 'CPF inválido. Confira os números.'; } },
    vendaNome: { novo: true, validar: function (v) { return /\S+\s+\S+/.test(v.trim()) ? '' : 'Digite o nome completo (nome e sobrenome).'; } },
    vendaTelefone: { novo: true, formatar: formatarTelefone, validar: function (v) { var n = digitos(v).length; return n === 10 || n === 11 ? '' : 'Digite o telefone com DDD (10 ou 11 números).'; } },
    vendaCep: { novo: true, formatar: formatarCep, validar: function (v) { return digitos(v).length === 8 ? '' : 'O CEP tem 8 números.'; } },
    vendaNumero: { novo: true, validar: function (v) { return v.trim() ? '' : 'Digite o número (ou S/N).'; } },
    vendaComplemento: { novo: true, validar: function () { return ''; } }
  };

  function clienteNovo() { return painelVenda.elements.cadastro.value === 'nao'; }

  function erroDoCampo(id, mensagem) {
    var input = $(id), erro = $(id + 'Erro');
    if (erro) erro.textContent = mensagem;
    input.setAttribute('aria-invalid', String(!!mensagem));
    return !mensagem;
  }

  function abrirAnotacao() {
    if (!soma.length) return;
    anotando = true;
    avisar('');
    vendaItens.textContent = '';
    soma.forEach(function (item) { vendaItens.appendChild(linhaVenda(item, true)); });
    var total = soma.reduce(function (t, i) { return t + i.preco * i.qtd; }, 0);
    var unidades = soma.reduce(function (t, i) { return t + i.qtd; }, 0);
    vendaTotal.textContent = (unidades === 1 ? '1 item' : unidades + ' itens') + ' · ' + reais.format(total);
    camposNovo.hidden = !clienteNovo();
    mostrarVista();
    painelVenda.scrollTop = 0;
    if (!TOQUE) $('vendaCpf').focus();
  }

  // Linha de item da venda: "2× Nome" e "TF · Cor · Tam.". No formulário (editavel), o item
  // que entrou pela busca por nome ou TF não tem tamanho, então o vendedor informa.
  function linhaVenda(item, editavel) {
    var li = el('li', 'venda-item');
    li.appendChild(el('span', 'venda-qtd', item.qtd + '×'));
    var corpo = el('div');
    corpo.appendChild(el('p', 'item-nome', item.nome));
    var ficha = el('p', 'ficha', (item.modelo || item.referencia) + ' · ' + textoCor(item) + (item.tamanho ? ' · Tam.\u00a0' + textoTamanho(item.tamanho) : ''));
    corpo.appendChild(ficha);
    if (editavel && !item.tamanho) {
      var rotulo = el('label', 'campo-tamanho', 'Tamanho ');
      var input = el('input');
      input.type = 'text';
      input.maxLength = 6;
      input.autocapitalize = 'characters';
      input.autocomplete = 'off';
      input.placeholder = 'Ex.: M';
      input.value = item.tamanhoDigitado || '';
      input.setAttribute('data-tamanho', item.chave);
      input.addEventListener('input', function () {
        item.tamanhoDigitado = input.value.trim().toUpperCase();
        input.setAttribute('aria-invalid', 'false');
        guardarSoma();
      });
      rotulo.appendChild(input);
      corpo.appendChild(rotulo);
    }
    li.appendChild(corpo);
    li.appendChild(el('span', 'venda-preco', reais.format(item.preco * item.qtd)));
    return li;
  }

  function salvarVenda() {
    var novo = clienteNovo();
    var primeiroErro = null;
    Object.keys(CAMPOS).forEach(function (id) {
      var regra = CAMPOS[id];
      var ok = regra.novo && !novo ? erroDoCampo(id, '') : erroDoCampo(id, regra.validar($(id).value));
      if (!ok && !primeiroErro) primeiroErro = $(id);
    });
    Array.prototype.forEach.call(vendaItens.querySelectorAll('[data-tamanho]'), function (input) {
      var falta = !input.value.trim();
      input.setAttribute('aria-invalid', String(falta));
      if (falta && !primeiroErro) primeiroErro = input;
    });
    if (primeiroErro) {
      avisar('Confira os campos marcados antes de salvar.', true);
      primeiroErro.focus();
      return;
    }

    var cliente = { cadastro: !novo, cpf: formatarCpf($('vendaCpf').value) };
    if (novo) {
      cliente.nome = $('vendaNome').value.replace(/\s+/g, ' ').trim();
      cliente.telefone = formatarTelefone($('vendaTelefone').value);
      cliente.cep = formatarCep($('vendaCep').value);
      cliente.numero = $('vendaNumero').value.trim();
      cliente.complemento = $('vendaComplemento').value.trim();
    }
    vendas.unshift({
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      criada: new Date().toISOString(),
      cliente: cliente,
      itens: soma.map(function (i) {
        return {
          qtd: i.qtd, nome: i.nome, modelo: i.modelo, referencia: i.referencia, corCodigo: i.corCodigo, corNome: i.corNome,
          tamanho: i.tamanho || i.tamanhoDigitado, ean: i.tamanho ? i.ean : '', preco: i.preco, precoCheio: i.precoCheio
        };
      }),
      total: soma.reduce(function (t, i) { return t + i.preco * i.qtd; }, 0)
    });
    var guardou = guardarVendas();
    soma = [];
    removido = null;
    guardarSoma();
    painelVenda.reset();
    Object.keys(CAMPOS).forEach(function (id) { erroDoCampo(id, ''); });
    definirModo('pendentes');
    avisar(guardou ? 'Venda anotada. Ela fica aqui até você marcar como lançada.'
      : 'Venda anotada, mas este navegador não está guardando dados (aba anônima?): ela some se a página fechar.', !guardou);
  }

  function guardarVendas() {
    try { localStorage.setItem(CHAVE_VENDAS, JSON.stringify(vendas)); return true; } catch (e) { return false; }
  }

  // ------------------------------------------------------------ vendas pendentes

  function desenharPendentes() {
    contagemPendentes.textContent = vendas.length;
    contagemPendentes.hidden = !vendas.length;
    if (modo !== 'pendentes') return;
    listaPendentes.textContent = '';
    pendentesVazia.hidden = vendas.length > 0;
    vendas.forEach(function (venda) { listaPendentes.appendChild(cartaoVenda(venda)); });
  }

  function linhaDado(dl, rotulo, valor) {
    if (!valor) return;
    dl.appendChild(el('dt', null, rotulo));
    dl.appendChild(el('dd', null, valor));
  }

  function cartaoVenda(venda) {
    var li = el('li', 'venda-pendente');
    var topo = el('div', 'venda-topo');
    var quando = el('time', null, dataHora.format(new Date(venda.criada)).replace(',', ' às'));
    quando.dateTime = venda.criada;
    topo.appendChild(quando);
    topo.appendChild(el('strong', null, reais.format(venda.total)));
    li.appendChild(topo);

    var c = venda.cliente;
    li.appendChild(el('p', 'venda-cliente', c.cadastro ? 'Cliente com cadastro' : 'Cliente novo: cadastrar'));
    var dl = el('dl', 'venda-dados');
    linhaDado(dl, 'CPF', c.cpf);
    linhaDado(dl, 'Nome', c.nome);
    linhaDado(dl, 'Telefone', c.telefone);
    linhaDado(dl, 'CEP', c.cep);
    linhaDado(dl, 'Número', c.numero);
    linhaDado(dl, 'Complemento', c.complemento);
    li.appendChild(dl);

    var itens = el('ul', 'venda-itens');
    venda.itens.forEach(function (item) { itens.appendChild(linhaVenda(item, false)); });
    li.appendChild(itens);

    var b = el('button', 'botao pequeno primario', 'Marcar como lançada');
    b.type = 'button';
    b.addEventListener('click', function () { marcarLancada(venda); });
    li.appendChild(b);
    return li;
  }

  function marcarLancada(venda) {
    var posicao = vendas.indexOf(venda);
    if (posicao < 0) return;
    vendas.splice(posicao, 1);
    lancada = { venda: venda, posicao: posicao };
    guardarVendas();
    desenharPendentes();
    avisar('Venda marcada como lançada e apagada deste aparelho.', false, { rotulo: 'Desfazer', fazer: desfazerLancada });
  }

  function desfazerLancada() {
    if (!lancada) return;
    vendas.splice(Math.min(lancada.posicao, vendas.length), 0, lancada.venda);
    lancada = null;
    guardarVendas();
    desenharPendentes();
    avisar('Venda de volta nas pendentes.');
  }

  // ------------------------------------------------------------ leitor ao vivo

  function criarDetector() {
    if (leitor.detector) return leitor.detector;
    leitor.detector = (function () {
      if ('BarcodeDetector' in window) {
        return window.BarcodeDetector.getSupportedFormats().then(function (suportados) {
          var formatos = FORMATOS.filter(function (f) { return suportados.indexOf(f) >= 0; });
          if (formatos.indexOf('ean_13') >= 0) return new window.BarcodeDetector({ formats: formatos });
          throw new Error('sem EAN');
        });
      }
      return Promise.reject(new Error('sem BarcodeDetector'));
    })().catch(function () {
      return import(LIB_LEITOR).then(function (lib) { return new lib.BarcodeDetector({ formats: FORMATOS }); });
    });
    leitor.detector.catch(function () { leitor.detector = null; });
    return leitor.detector;
  }

  function atualizarBotaoCamera() {
    botaoCamera.lastChild.textContent = leitor.abrindo ? ' Abrindo a câmera…' : leitor.ativo ? ' Parar a câmera' : ' Ler código de barras';
    botaoCamera.setAttribute('aria-pressed', String(leitor.ativo));
    camera.hidden = !leitor.ativo;
  }

  function alternarCamera() {
    if (leitor.ativo) return desligarCamera();
    if (leitor.abrindo) return;
    leitor.abrindo = true;
    atualizarBotaoCamera();
    // O som do bipe precisa nascer de um toque do usuário (regra dos navegadores).
    try {
      leitor.audio = leitor.audio || new (window.AudioContext || window.webkitAudioContext)();
      leitor.audio.resume();
    } catch (e) { /* sem som */ }
    Promise.resolve().then(function () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Este navegador não libera a câmera. Use o Chrome (Android) ou o Safari (iPhone).');
      }
      return Promise.all([criarDetector(), navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false
      })]);
    }).then(function (r) {
      leitor.stream = r[1];
      video.srcObject = leitor.stream;
      return video.play();
    }).then(function () {
      leitor.ativo = true;
      mostrarLeitura('Aponte para o código de barras', '');
      lerQuadro();
    }).catch(function (e) {
      desligarCamera();
      avisar(e && e.name === 'NotAllowedError' ? 'A câmera foi bloqueada. Libere o acesso à câmera para este site nas configurações do navegador.'
        : e && e.name === 'NotFoundError' ? 'Nenhuma câmera encontrada neste aparelho. Digite o código ou use um leitor USB/Bluetooth.'
        : (e && e.message) || 'Não foi possível abrir a câmera.', true);
    }).then(function () {
      leitor.abrindo = false;
      atualizarBotaoCamera();
    });
  }

  function desligarCamera() {
    leitor.ativo = false;
    if (leitor.stream) leitor.stream.getTracks().forEach(function (t) { t.stop(); });
    leitor.stream = null;
    video.srcObject = null;
    atualizarBotaoCamera();
  }

  // Lê uns 8 quadros por segundo enquanto a câmera estiver ligada.
  function lerQuadro() {
    if (!leitor.ativo) return;
    var passo = video.readyState >= 2 ? leitor.detector.then(function (d) { return d.detect(video); }) : Promise.resolve(null);
    passo.then(function (codigos) {
      if (codigos) processarQuadro(codigos, Date.now());
    }, function () { /* quadro ruim: tenta o próximo */ }).then(function () {
      setTimeout(lerQuadro, 120);
    });
  }

  // O mesmo código só conta de novo depois de sumir da câmera por PAUSA_MESMO_CODIGO.
  function processarQuadro(codigos, agora) {
    if (codigos.length > 1) return mostrarLeitura('Mais de um código na câmera. Mire em um só.', 'erro');
    if (codigos.length !== 1) return;
    var codigo = codigos[0].rawValue;
    var mesmo = codigo === leitor.ultimo && agora - leitor.visto < PAUSA_MESMO_CODIGO;
    leitor.visto = agora;
    if (mesmo) return;
    leitor.ultimo = codigo;
    receberCodigo(codigo, 'camera');
  }

  // O bipe toca aqui, no instante em que o código é lido; se depois o produto não for
  // encontrado, toca o som de erro.
  function receberCodigo(codigo, origem) {
    if (modo === 'soma') {
      if (!EAN.test(codigo)) {
        sinal('erro');
        return avisar('Esse código (' + codigo + ') não é um EAN de produto.', true);
      }
      sinal('ok');
      return somarEan(codigo, origem);
    }
    sinal('ok');
    campo.value = codigo;
    if (origem === 'camera') mostrarLeitura('✓ ' + codigo, 'ok');
    consultar(codigo);
  }

  var limpaLeitura = 0;
  function mostrarLeitura(texto, tipo) {
    leitura.textContent = texto;
    leitura.className = 'leitura' + (tipo ? ' ' + tipo : '');
    clearTimeout(limpaLeitura);
    if (tipo) limpaLeitura = setTimeout(function () { if (leitor.ativo) mostrarLeitura('Aponte para o código de barras', ''); }, 1800);
  }

  // ------------------------------------------------------------ eventos

  $('abrirConsulta').addEventListener('click', abrir);
  $('fecharLupa').addEventListener('click', function () { dialogo.close(); });
  dialogo.addEventListener('click', function (e) { if (e.target === dialogo) dialogo.close(); });
  dialogo.addEventListener('close', desligarCamera);
  document.addEventListener('visibilitychange', function () { if (document.hidden) desligarCamera(); });
  var ORDEM = ['consulta', 'soma', 'pendentes'];
  ORDEM.forEach(function (m) {
    ABAS[m].addEventListener('click', function () {
      definirModo(m);
      // No computador o campo já fica pronto para digitar ou para o leitor USB; no celular
      // o foco fica na aba, para o teclado não abrir sozinho.
      if (m !== 'pendentes') focarCampo();
    });
    ABAS[m].addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      var destino = ORDEM[(ORDEM.indexOf(modo) + (e.key === 'ArrowRight' ? 1 : ORDEM.length - 1)) % ORDEM.length];
      definirModo(destino);
      ABAS[destino].focus();
    });
  });
  $('anotarVenda').addEventListener('click', abrirAnotacao);
  $('voltarSoma').addEventListener('click', function () { anotando = false; avisar(''); mostrarVista(); });
  painelVenda.addEventListener('submit', function (e) { e.preventDefault(); salvarVenda(); });
  painelVenda.addEventListener('change', function (e) {
    if (e.target.name === 'cadastro') camposNovo.hidden = !clienteNovo();
  });
  // Ao corrigir qualquer campo, o aviso de erro do formulário sai da tela.
  painelVenda.addEventListener('input', function () { if (status.classList.contains('erro')) avisar(''); });
  Object.keys(CAMPOS).forEach(function (id) {
    $(id).addEventListener('input', function () {
      if (CAMPOS[id].formatar) $(id).value = CAMPOS[id].formatar($(id).value);
      erroDoCampo(id, '');
    });
  });
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var termo = campo.value.trim();
    if (modo === 'soma' && EAN.test(termo)) {
      somarEan(termo, 'campo');
      campo.value = '';
      return;
    }
    consultar(termo);
  });
  botaoCamera.addEventListener('click', alternarCamera);
  limpar.addEventListener('click', limparSoma);
  // "/" abre a lupa (fora de campos de texto), como em muitos sites.
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && !dialogo.open && !e.target.closest('input, textarea')) { e.preventDefault(); abrir(); }
  });

  var salvo = null;
  try { salvo = localStorage.getItem(CHAVE_MODO); } catch (e) { /* sem armazenamento */ }
  definirModo(salvo === 'soma' ? 'soma' : 'consulta');
})();
