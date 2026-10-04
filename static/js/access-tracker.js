/**
 * PJzen Access Tracker
 * Registra entradas e saídas no Supabase com data, horário e IP do computador.
 * 
 * REGRA ESTRITA:
 * - Só registra no Supabase quando estiver ativo na Hostinger (ou ambiente de produção).
 * - Em Localhost (127.0.0.1, localhost, desenvolvimento local) NÃO REGISTRA NADA.
 */
(function () {
  'use strict';

  // 1. Verificação se o ambiente é Localhost
  function checkIsLocalhost() {
    const hostname = window.location.hostname.toLowerCase();
    return (
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '0.0.0.0' ||
      hostname === '::1' ||
      hostname.endsWith('.local') ||
      window.location.protocol === 'file:'
    );
  }

  if (checkIsLocalhost()) {
    console.log('[PJzen Tracker] Localhost ativo: Registro de acessos no Supabase desativado.');
    return; // Encerra imediatamente sem registrar
  }

  // 2. Gerenciamento de Sessão Única do Visitante
  let sessionId = sessionStorage.getItem('pjzen_session_id');
  if (!sessionId) {
    sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    sessionStorage.setItem('pjzen_session_id', sessionId);
  }

  const startTime = Date.now();
  let saidaEnviada = false;

  // 3. Função de Envio de Log para o Endpoint /api/log-acesso
  function enviarLog(tipoEvento, dadosExtras) {
    dadosExtras = dadosExtras || {};
    const now = new Date();
    const horarioFormatado = now.toLocaleDateString('pt-BR') + ' ' + now.toLocaleTimeString('pt-BR');

    const payload = Object.assign({
      tipo_evento: tipoEvento, // 'entrada' ou 'saida'
      session_id: sessionId,
      horario: horarioFormatado,
      pagina: window.location.pathname + window.location.search,
      dispositivo: navigator.userAgent,
      host: window.location.host
    }, dadosExtras);

    const jsonStr = JSON.stringify(payload);

    // No fechamento do site (saída), utiliza sendBeacon ou fetch keepalive para garantir envio
    if (tipoEvento === 'saida' && navigator.sendBeacon) {
      try {
        const blob = new Blob([jsonStr], { type: 'application/json' });
        navigator.sendBeacon('/api/log-acesso', blob);
        return;
      } catch (e) {
        // Fallback para fetch keepalive
      }
    }

    fetch('/api/log-acesso', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: jsonStr,
      keepalive: true
    }).catch(function () {
      // Falha silenciosa de rede para não atrapalhar o usuário
    });
  }

  // 4. Registro de ENTRADA ao carregar a página
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    enviarLog('entrada');
  } else {
    window.addEventListener('DOMContentLoaded', function () {
      enviarLog('entrada');
    });
  }

  // 5. Registro de SAÍDA ao fechar, trocar de aba ou sair do site
  function handleSaida() {
    if (saidaEnviada) return;
    saidaEnviada = true;
    const duracaoSegundos = Math.max(0, Math.round((Date.now() - startTime) / 1000));
    enviarLog('saida', {
      tempo_permanencia_segundos: duracaoSegundos
    });
  }

  // Evento em celulares (iOS/Android): ao minimizar ou trocar de aba
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') {
      handleSaida();
    } else if (document.visibilityState === 'visible') {
      // Se o usuário voltou para a aba, permite registrar uma nova saída posterior
      saidaEnviada = false;
    }
  });

  // Evento em navegadores desktop: ao fechar a janela ou navegar para outro site
  window.addEventListener('pagehide', handleSaida);
  window.addEventListener('beforeunload', handleSaida);

})();
