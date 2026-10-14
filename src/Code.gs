/**
 * Hub da equipe Track&Field
 *
 * Lê os links da aba "Links" desta planilha e serve a página da vitrine.
 * Publicar em: Implantar > Nova implantação > App da Web
 *   Executar como: Eu  |  Quem pode acessar: Qualquer pessoa
 */

// Planilha "Hub Track&Field: links". Usada quando o script não está vinculado a ela.
const ID_PLANILHA = '1eSkaq6dsmBnoYOXWYdMJFE7LAEQMngrRszZE_ed4OUE';
const ABA_LINKS = 'Links';
const CHAVE_CACHE = 'links-v1';
const CACHE_SEGUNDOS = 300;

// Cabeçalhos aceitos (sem acento, minúsculos) para cada campo.
const COLUNAS = {
  ordem: 'ordem',
  ativo: 'ativo',
  nome: 'nome',
  categoria: 'categoria',
  descricao: 'descricao',
  url: 'url',
  produto: 'produto',
  expositor: 'expositor',
  imagem: 'imagem',
};

function doGet() {
  let dados;
  try {
    dados = { links: lerLinks_() };
  } catch (erro) {
    dados = { erro: erro.message };
  }

  const template = HtmlService.createTemplateFromFile('Index');
  template.dadosJson = jsonSeguro_(dados);
  return template
    .evaluate()
    .setTitle('Hub Track&Field')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1, viewport-fit=cover');
}

/** Gatilho simples: qualquer edição na planilha atualiza o Hub na próxima visita. */
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
      expositor: texto_(linha[col.expositor]) || 'Manequim',
      imagem: texto_(linha[col.imagem]),
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

// JSON que pode ir dentro de <script> sem fechar a tag por engano.
function jsonSeguro_(valor) {
  return JSON.stringify(valor)
    .replace(/</g, '\\u003c')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}
