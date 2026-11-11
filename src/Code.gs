/**
 * Hub da equipe Track&Field: servidor de dados do site (https://lucasfranco-dev.github.io/hub-trackfield/).
 *
 * Responde em JSON com os links da aba "Links" desta planilha e com a consulta de produtos no
 * site da TF. Sem ?acao, mostra a página que leva ao endereço novo do Hub.
 * Publicar em: Implantar > Nova implantação > App da Web
 *   Executar como: Eu  |  Quem pode acessar: Qualquer pessoa
 */

// Planilha "Hub Track&Field: links". Usada quando o script não está vinculado a ela.
const ID_PLANILHA = '1eSkaq6dsmBnoYOXWYdMJFE7LAEQMngrRszZE_ed4OUE';
const ABA_LINKS = 'Links';
const CHAVE_CACHE = 'links-v2';
// Edições na planilha aparecem no Hub em até 1 minuto.
const CACHE_SEGUNDOS = 60;

// Cabeçalhos aceitos (sem acento, minúsculos) para cada campo.
const COLUNAS = {
  ordem: 'ordem',
  ativo: 'ativo',
  nome: 'nome',
  categoria: 'categoria',
  descricao: 'descricao',
  url: 'url',
  produto: 'produto',
};

/**
 * Com ?acao=..., responde em JSON para o site do Hub no GitHub Pages:
 *   ?acao=links              -> { links: [...] }
 *   ?acao=produto&q=<busca>  -> { consulta, produtos: [...] }  (EAN, código TF ou nome)
 * Erros voltam como { erro: "mensagem" }. Sem acao, mostra o aviso do endereço novo.
 */
function doGet(e) {
  const acao = e && e.parameter && e.parameter.acao;
  if (acao) return responderJson_(acao, e.parameter);
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Hub Track&Field')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function responderJson_(acao, parametros) {
  let resposta;
  try {
    if (acao === 'links') resposta = { links: lerLinks_() };
    else if (acao === 'produto') resposta = buscarProduto(parametros.q);
    else throw new Error('Ação desconhecida: ' + acao);
  } catch (erro) {
    resposta = { erro: erro.message };
  }
  return ContentService.createTextOutput(JSON.stringify(resposta)).setMimeType(ContentService.MimeType.JSON);
}

/** Só dispara se o script estiver vinculado à planilha: limpa o cache na hora. */
function onEdit() {
  CacheService.getScriptCache().remove(CHAVE_CACHE);
}

/** Pode ser executado pelo editor para forçar a atualização. */
function limparCache() {
  CacheService.getScriptCache().remove(CHAVE_CACHE);
}

function lerLinks_() {
  const cache = CacheService.getScriptCache();
  const salvo = cache.get(CHAVE_CACHE);
  if (salvo) return JSON.parse(salvo);

  const planilha = SpreadsheetApp.getActiveSpreadsheet() || SpreadsheetApp.openById(ID_PLANILHA);
  const aba = planilha.getSheetByName(ABA_LINKS);
  if (!aba) throw new Error('Crie uma aba chamada "' + ABA_LINKS + '" na planilha.');

  const [cabecalho, ...linhas] = aba.getDataRange().getValues();
  const col = indexarColunas_(cabecalho);

  const links = linhas
    .map((linha) => ({
      ordem: Number(linha[col.ordem]) || 999,
      ativo: linha[col.ativo] === true || /^(sim|s|x|true)$/i.test(String(linha[col.ativo]).trim()),
      nome: texto_(linha[col.nome]),
      categoria: texto_(linha[col.categoria]),
      descricao: texto_(linha[col.descricao]),
      url: texto_(linha[col.url]),
      produto: texto_(linha[col.produto]),
    }))
    .filter((l) => l.ativo && l.nome && /^https?:\/\//i.test(l.url))
    .sort((a, b) => a.ordem - b.ordem)
    .map(({ ordem, ativo, ...link }) => link);

  cache.put(CHAVE_CACHE, JSON.stringify(links), CACHE_SEGUNDOS);
  return links;
}

function indexarColunas_(cabecalho) {
  const normalizado = cabecalho.map((c) =>
    String(c).normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase()
  );
  const col = {};
  Object.keys(COLUNAS).forEach((campo) => {
    col[campo] = normalizado.indexOf(COLUNAS[campo]);
  });
  ['nome', 'url', 'ativo'].forEach((obrigatorio) => {
    if (col[obrigatorio] === -1) {
      throw new Error('A aba "' + ABA_LINKS + '" precisa de uma coluna "' + obrigatorio + '".');
    }
  });
  return col;
}

function texto_(valor) {
  return valor === undefined || valor === null ? '' : String(valor).trim();
}


// ---------------------------------------------------------------- consulta de produtos

const SITE_TF = 'https://www.tf.com.br';
const CONSULTA_CACHE_SEGUNDOS = 600;
const CONSULTA_MAX_RESULTADOS = 12;

/**
 * Consulta de produtos da lupa do Hub (chamada pelo site com ?acao=produto&q=...).
 * Aceita EAN (só números), código TF (com ou sem a cor, ex.: TF041024 ou TF041024-0003)
 * ou parte do nome. Usa a busca do site tf.com.br, que a página não pode chamar direto
 * (o navegador bloqueia por CORS), e devolve só o que a tela mostra.
 */
function buscarProduto(consulta) {
  const termo = String(consulta || '').replace(/\s+/g, ' ').trim().slice(0, 80);
  if (termo.length < 2) throw new Error('Digite pelo menos 2 caracteres.');
  const ean = /^\d{8,14}$/.test(termo) ? termo : null;

  const cache = CacheService.getScriptCache();
  const chave = 'produto:' + termo.toLowerCase();
  const salvo = cache.get(chave);
  if (salvo) return JSON.parse(salvo);

  let produtos = buscarNoSite_('/api/io/_v/api/intelligent-search/product_search/?count=' + CONSULTA_MAX_RESULTADOS +
                               '&query=' + encodeURIComponent(termo), 'products');
  if (ean) {
    // A busca do site é aproximada; para EAN vale só o produto que tem exatamente esse código.
    produtos = produtos.filter((p) => (p.items || []).some((i) => i.ean === ean));
    if (!produtos.length) {
      produtos = buscarNoSite_('/api/catalog_system/pub/products/search?fq=alternateIds_Ean:' + ean, null);
    }
  }
  const resultado = {
    consulta: termo,
    produtos: produtos.map((p) => resumirProduto_(p, ean)).filter(Boolean).slice(0, CONSULTA_MAX_RESULTADOS),
  };
  cache.put(chave, JSON.stringify(resultado), CONSULTA_CACHE_SEGUNDOS);
  return resultado;
}

function buscarNoSite_(caminho, campo) {
  const resposta = UrlFetchApp.fetch(SITE_TF + caminho, {
    muteHttpExceptions: true,
    headers: { Accept: 'application/json' },
  });
  if (resposta.getResponseCode() !== 200) {
    throw new Error('O site da TF não respondeu agora. Tente de novo em instantes.');
  }
  const dados = JSON.parse(resposta.getContentText());
  return (campo ? dados[campo] : dados) || [];
}

/** Reduz um produto do site ao que a consulta mostra. Com EAN, usa o tamanho daquele código. */
function resumirProduto_(produto, ean) {
  const itens = produto.items || [];
  const oferta = (item) => ((item.sellers || [])[0] || {}).commertialOffer || {};
  const item = ean
    ? itens.find((i) => i.ean === ean)
    : itens.find((i) => oferta(i).AvailableQuantity > 0) || itens[0];
  if (!item) return null;

  const ref = texto_(produto.productReference);
  const partes = /^(.+)-(\d{3,4})$/.exec(ref);
  const imagem = texto_(((item.images || [])[0] || {}).imageUrl)
    .replace(/(\/arquivos\/ids\/\d+)(-\d+-\d+)?\/.*/, '$1-400-559');
  const link = texto_(produto.link);
  const precos = produto.priceRange || {};
  let preco = Number(oferta(item).Price) || 0;
  let precoCheio = Number(oferta(item).ListPrice) || 0;
  if (!preco && precos.sellingPrice) {
    preco = precos.sellingPrice.lowPrice || 0;
    precoCheio = (precos.listPrice || {}).lowPrice || preco;
  }

  return {
    nome: texto_(produto.productName),
    referencia: ref,
    modelo: partes ? partes[1] : ref,
    corCodigo: partes ? partes[2] : '',
    corNome: tituloCor_(nomeDaCor_(item)),
    corHex: variacao_(item, 'COR HEX'),
    tamanho: ean ? variacao_(item, 'TAMANHO') : '',
    ean: texto_(item.ean),
    imagem: /^https:\/\/trackfield\.vtexassets\.com\//.test(imagem) ? imagem : '',
    link: /^https?:\/\//.test(link) ? link : SITE_TF + link,
    preco: preco,
    precoCheio: Math.max(precoCheio, preco),
    disponivel: itens.some((i) => oferta(i).AvailableQuantity > 0),
  };
}

// O nome do item no site é "Cor - Tamanho" (ex.: "Azul Noturno - UNICO"): a cor exata da TF.
// "CORES E ESTAMPAS" traz só a cor genérica (ex.: "AZUL") e fica como reserva.
function nomeDaCor_(item) {
  const tamanho = variacao_(item, 'TAMANHO');
  const nome = texto_(item.name);
  if (tamanho && nome.endsWith(' - ' + tamanho)) return nome.slice(0, -(' - ' + tamanho).length);
  return variacao_(item, 'CORES E ESTAMPAS') || nome;
}

function variacao_(item, nome) {
  const valor = item[nome] || ((item.variations || []).find((v) => v.name === nome) || {}).values;
  return texto_(Array.isArray(valor) ? valor[0] : valor);
}

function tituloCor_(cor) {
  return cor.toLowerCase().replace(/(^|[\s/-])(\p{L})/gu, (_, sep, letra) => sep + letra.toUpperCase());
}

/** Rode uma vez no editor do Apps Script para autorizar a consulta ao site da TF. */
function autorizarConsulta() {
  const r = buscarProduto('7909563108891');
  Logger.log('Consulta autorizada: ' + (r.produtos[0] ? r.produtos[0].nome : 'sem resultado'));
}
