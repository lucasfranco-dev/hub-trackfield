// Configuração comum do site do Hub: o servidor de dados (Apps Script) e como falar com ele.
window.HUB = (function () {
  'use strict';

  // Implantação do Apps Script (a mesma de package.json, config.deploymentId).
  var API = 'https://script.google.com/macros/s/AKfycbxawbOdgqsfsxDmw7Tn0IR1l_76XcU93D5uxSl2q78mPSBlMnPn5A2DqqE8l1pIAR0bbQ/exec';

  // GET simples (sem cabeçalhos extras) para não disparar o preflight de CORS, que o
  // Apps Script não responde. Erros do servidor chegam como { erro: "mensagem" }.
  function api(acao, parametros) {
    var url = API + '?acao=' + encodeURIComponent(acao);
    Object.keys(parametros || {}).forEach(function (k) {
      url += '&' + encodeURIComponent(k) + '=' + encodeURIComponent(parametros[k]);
    });
    var controle = window.AbortController ? new AbortController() : null;
    var limite = setTimeout(function () { if (controle) controle.abort(); }, 25000);
    return fetch(url, controle ? { signal: controle.signal } : {}).then(function (r) {
      if (!r.ok) throw new Error('O servidor do Hub não respondeu (erro ' + r.status + '). Tente de novo.');
      return r.json();
    }).then(function (dados) {
      if (dados && dados.erro) throw new Error(dados.erro);
      return dados;
    }).catch(function (e) {
      if (e && e.name === 'AbortError') throw new Error('O servidor do Hub demorou para responder. Tente de novo.');
      if (e instanceof TypeError) throw new Error('Sem conexão com o servidor do Hub. Verifique a internet.');
      throw e;
    }).finally(function () { clearTimeout(limite); });
  }

  return { API: API, api: api, CHAVE_LINKS: 'hub-links-v1' };
})();
