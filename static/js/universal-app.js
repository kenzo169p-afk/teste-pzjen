/**
 * PJzen Universal App Script
 * Funciona em celulares, tablets, computadores e qualquer hospedagem (Estática, PHP, Node, Python, Docker).
 * Suporte a salvamento em servidor ou offline (LocalStorage), geração de PDF direto no aparelho e PWA.
 */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('handoff-form');
  const viewContainer = document.getElementById('view-mode-container');
  const appStatusBadge = document.getElementById('app-status-badge');
  const btnDraft = document.getElementById('btn-save-draft');
  const btnSubmit = document.getElementById('btn-submit-form');
  const btnDirectPdf = document.getElementById('btn-download-pdf-direct');
  const nameInput = document.getElementById('nome_preenchedor');
  const nameCard = document.getElementById('name-card');
  const nameError = document.getElementById('name-error-msg');
  const saveStatusText = document.getElementById('save-status-text');
  const shareModal = document.getElementById('share-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');

  // Registro de PWA (celular offline e instalar na tela inicial)
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }

  // Identificação de Parâmetros de URL (?view=..., ?edit=..., ?doc=...)
  const urlParams = new URLSearchParams(window.location.search);
  const viewTokenParam = urlParams.get('view');
  const editTokenParam = urlParams.get('edit');
  const docTokenParam = urlParams.get('doc');

  let currentEditToken = editTokenParam || '';
  let currentViewToken = viewTokenParam || '';
  let currentVersion = 1;
  let attachmentsList = [];

  // 1. Auto-resize de Textareas
  const textareas = document.querySelectorAll('textarea');
  function adjustHeight(el) {
    el.style.height = 'auto';
    el.style.height = Math.max(el.scrollHeight, 88) + 'px';
  }
  textareas.forEach(ta => {
    adjustHeight(ta);
    ta.addEventListener('input', () => adjustHeight(ta));
  });

  // 2. Visual Toggle de Checkboxes
  const checkboxes = document.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(cb => {
    const parent = cb.closest('.checkbox-label');
    if (cb.checked && parent) parent.classList.add('is-checked');
    cb.addEventListener('change', () => {
      if (parent) {
        if (cb.checked) parent.classList.add('is-checked');
        else parent.classList.remove('is-checked');
      }
    });
  });

  // 3. Máscara de CNPJ
  const cnpjInput = document.getElementById('cnpj');
  if (cnpjInput) {
    cnpjInput.addEventListener('input', (e) => {
      let v = e.target.value.replace(/\D/g, '');
      if (v.length > 14) v = v.substring(0, 14);
      if (v.length > 12) {
        v = v.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{1,2})$/, '$1.$2.$3/$4-$5');
      } else if (v.length > 8) {
        v = v.replace(/^(\d{2})(\d{3})(\d{3})(\d{1,4})$/, '$1.$2.$3/$4');
      } else if (v.length > 5) {
        v = v.replace(/^(\d{2})(\d{3})(\d{1,3})$/, '$1.$2.$3');
      } else if (v.length > 2) {
        v = v.replace(/^(\d{2})(\d{1,3})$/, '$1.$2');
      }
      e.target.value = v;
    });
  }

  // 4. Máscara de Telefone
  const phoneInputs = document.querySelectorAll('.phone-mask');
  phoneInputs.forEach(input => {
    input.addEventListener('input', (e) => {
      let v = e.target.value.replace(/\D/g, '');
      if (v.length > 11) v = v.substring(0, 11);
      if (v.length > 10) {
        v = v.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
      } else if (v.length > 6) {
        v = v.replace(/^(\d{2})(\d{4})(\d{0,4})$/, '($1) $2-$3');
      } else if (v.length > 2) {
        v = v.replace(/^(\d{2})(\d{0,5})$/, '($1) $2');
      } else if (v.length > 0) {
        v = v.replace(/^(\d{0,2})$/, '($1');
      }
      e.target.value = v;
    });
  });

  // 5. Toast Notifications
  function showToast(message, type = 'normal') {
    let toast = document.getElementById('app-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'app-toast';
      toast.className = 'toast';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = `toast show ${type === 'error' ? 'toast-error' : type === 'success' ? 'toast-success' : ''}`;
    setTimeout(() => {
      toast.className = 'toast';
    }, 3500);
  }

  // 6. Gerenciamento de Anexos (Suporta Base64 no navegador ou servidor)
  const fileInput = document.getElementById('file-upload-input');
  const btnTriggerUpload = document.getElementById('btn-trigger-upload');
  const uploadSpinner = document.getElementById('upload-spinner');
  const attachmentsContainer = document.getElementById('attachments-container');

  if (btnTriggerUpload && fileInput) {
    btnTriggerUpload.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      if (uploadSpinner) uploadSpinner.style.display = 'inline';
      const now = new Date();
      const dataPc = now.toLocaleDateString('pt-BR') + ' às ' + now.toLocaleTimeString('pt-BR');

      // Tenta upload no servidor se disponível
      let uploadSuccess = false;
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('data_pc', dataPc);

        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        if (res.ok) {
          const json = await res.json();
          if (json.success) {
            addAttachmentCard({
              nome_original: json.nome_original,
              tipo: json.tipo,
              url: json.url,
              tamanho_formatado: json.tamanho_formatado,
              data_pc: json.data_pc,
              storage: json.storage || 'Servidor'
            });
            uploadSuccess = true;
          }
        }
      } catch (err) {
        // Servidor indisponível, fallback local
      }

      // Se não há backend de upload, converte para visualização local
      if (!uploadSuccess) {
        const reader = new FileReader();
        reader.onload = (re) => {
          const tamKb = (file.size / 1024).toFixed(1);
          let tipo = 'Documento';
          if (file.type.startsWith('image/')) tipo = 'Imagem';
          else if (file.type.startsWith('video/')) tipo = 'Vídeo';
          else if (file.type.includes('pdf')) tipo = 'PDF';

          addAttachmentCard({
            nome_original: file.name,
            tipo: tipo,
            url: re.target.result,
            tamanho_formatado: `${tamKb} KB`,
            data_pc: dataPc,
            storage: 'Armazenamento do Aparelho'
          });
        };
        reader.readAsDataURL(file);
      }

      if (uploadSpinner) uploadSpinner.style.display = 'none';
      fileInput.value = '';
      showToast('Documento anexado com sucesso!', 'success');
    });
  }

  function addAttachmentCard(att) {
    attachmentsList.push(att);
    if (!attachmentsContainer) return;
    const item = document.createElement('div');
    item.className = 'attachment-item';
    item.dataset.index = attachmentsList.length - 1;
    item.style.cssText = 'background: var(--pj-white); border: 1px solid var(--slate-200); border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-top: 8px;';
    item.innerHTML = `
      <div>
        <strong>${att.nome_original}</strong> (${att.tipo})
        <div style="font-size: 0.8rem; color: var(--slate-500); margin-top: 2px;">
          Registrado em: <strong>${att.data_pc}</strong> | Armazenamento: ${att.storage}
        </div>
      </div>
      <div style="display: flex; gap: 8px;">
        <a href="${att.url}" target="_blank" class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem; min-height: 32px; width: auto;">Ver</a>
        <button type="button" class="btn btn-danger btn-remove-att" style="padding: 4px 10px; font-size: 0.8rem; min-height: 32px; width: auto;">Remover</button>
      </div>
    `;
    item.querySelector('.btn-remove-att').addEventListener('click', () => {
      const idx = parseInt(item.dataset.index, 10);
      attachmentsList.splice(idx, 1);
      item.remove();
      showToast('Anexo removido.', 'normal');
    });
    attachmentsContainer.appendChild(item);
  }

  // 7. Coleta de Dados do Formulário
  function collectFormData() {
    const data = {};
    const inputs = form.querySelectorAll('input:not([type="checkbox"]):not([type="file"]), textarea');
    inputs.forEach(input => {
      if (input.name) data[input.name] = input.value.trim();
    });

    const checkboxGroups = [
      'tipo_demanda', 'plano_contratado', 'faturamento_mensal_esperado',
      'tera_pro_labore', 'regime_tributario', 'tabela_apuracao_anexo',
      'frentes_acionadas', 'status_repasse'
    ];
    checkboxGroups.forEach(grp => {
      const checked = form.querySelectorAll(`input[name="${grp}"]:checked`);
      data[grp] = Array.from(checked).map(c => c.value);
    });

    data['anexos_documentos'] = attachmentsList;
    return data;
  }

  // 8. Limpar classes de erro ao digitar/interagir
  form.addEventListener('input', (e) => {
    if (e.target && e.target.classList.contains('is-invalid')) {
      e.target.classList.remove('is-invalid');
    }
  });
  form.addEventListener('change', (e) => {
    if (e.target && e.target.classList.contains('is-invalid')) {
      e.target.classList.remove('is-invalid');
    }
    if (e.target && e.target.type === 'checkbox') {
      const group = e.target.closest('.checkbox-group');
      if (group && group.classList.contains('is-invalid')) {
        group.classList.remove('is-invalid');
      }
    }
  });

  // 9. Validação Estrita de Todos os Itens para Envio
  function validateAllRequiredFields() {
    let firstInvalid = null;
    let hasError = false;

    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    if (nameCard) nameCard.classList.remove('error-state');
    if (nameError) nameError.style.display = 'none';

    const requiredInputIds = [
      'nome_preenchedor', 'email_preenchedor', 'data_venda', 'cliente_razao_social',
      'cnpj', 'email_cliente', 'telefone_cliente', 'data_repasse',
      'atividade_cnae_municipio', 'atividades_secundarias', 'pontos_atencao_tecnicos',
      'demandas_acordadas', 'documentos_pendentes', 'prazo_combinado',
      'responsavel_onboarding', 'responsavel_tecnico', 'proxima_acao_resp_data'
    ];

    requiredInputIds.forEach(id => {
      const el = document.getElementById(id);
      if (el && !el.value.trim()) {
        el.classList.add('is-invalid');
        hasError = true;
        if (!firstInvalid) firstInvalid = el;
      }
    });

    const requiredCheckboxGroups = [
      'tipo_demanda', 'plano_contratado', 'faturamento_mensal_esperado',
      'tera_pro_labore', 'regime_tributario', 'tabela_apuracao_anexo',
      'frentes_acionadas', 'status_repasse'
    ];

    requiredCheckboxGroups.forEach(grp => {
      const checked = form.querySelectorAll(`input[name="${grp}"]:checked`);
      if (checked.length === 0) {
        const firstCb = form.querySelector(`input[name="${grp}"]`);
        const groupEl = firstCb ? firstCb.closest('.checkbox-group') : null;
        if (groupEl) {
          groupEl.classList.add('is-invalid');
          hasError = true;
          if (!firstInvalid) firstInvalid = groupEl;
        }
      }
    });

    if (hasError) {
      if (nameInput && nameInput.classList.contains('is-invalid')) {
        if (nameCard) nameCard.classList.add('error-state');
        if (nameError) {
          nameError.textContent = 'Informe seu nome para enviar';
          nameError.style.display = 'block';
        }
      }
      if (firstInvalid) {
        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        if (typeof firstInvalid.focus === 'function') firstInvalid.focus();
      }
      showToast('Por favor, preencha todos os campos obrigatórios antes de enviar.', 'error');
      return false;
    }
    return true;
  }

  // 10. Gerador de Token Seguro Local (para funcionamento offline e estático)
  function generateRandomToken() {
    const bytes = new Uint8Array(18);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, b => ('0' + b.toString(16)).slice(-2)).join('');
  }

  // 11. Banco de Dados Local (LocalStorage Fallback)
  function saveToLocalStorage(payload, isDraft = false) {
    const records = JSON.parse(localStorage.getItem('pjzen_records') || '{}');
    let viewToken = currentViewToken;
    let editToken = currentEditToken;

    if (!editToken) {
      editToken = 'edit_' + generateRandomToken();
      viewToken = 'view_' + generateRandomToken();
    }

    const now = new Date().toISOString();
    const existing = records[editToken] || {};

    const record = {
      ...existing,
      ...payload,
      edit_token: editToken,
      view_token: viewToken,
      version: (existing.version || 0) + 1,
      status_tecnico: isDraft ? 'rascunho' : 'enviado',
      submitted_at: isDraft ? null : (existing.submitted_at || now),
      updated_at: now
    };

    records[editToken] = record;
    records[viewToken] = record;
    localStorage.setItem('pjzen_records', JSON.stringify(records));

    return record;
  }

  function getFromLocalStorage(token) {
    const records = JSON.parse(localStorage.getItem('pjzen_records') || '{}');
    return records[token] || null;
  }

  // 12. Salvar Rascunho
  btnDraft.addEventListener('click', async () => {
    btnDraft.disabled = true;
    const orig = btnDraft.innerHTML;
    btnDraft.innerHTML = 'Salvando...';
    if (saveStatusText) saveStatusText.textContent = 'Salvando rascunho...';

    const payload = collectFormData();
    let resData = null;

    try {
      let endpoint = currentEditToken ? `/api/edit/${currentEditToken}` : '/api/draft';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) resData = await res.json();
    } catch (e) {
      // Sem servidor, usa LocalStorage
    }

    if (!resData) {
      resData = saveToLocalStorage(payload, true);
    }

    currentEditToken = resData.edit_token;
    currentViewToken = resData.view_token;
    currentVersion = resData.version;

    window.history.replaceState({}, '', `?edit=${currentEditToken}`);
    showToast('Rascunho salvo com sucesso!', 'success');
    if (saveStatusText) saveStatusText.textContent = 'Rascunho salvo';
    if (btnDirectPdf) btnDirectPdf.style.display = 'inline-flex';

    btnDraft.disabled = false;
    btnDraft.innerHTML = orig;
  });

  // 13. Enviar Formulário / Salvar Alterações
  btnSubmit.addEventListener('click', async () => {
    if (!validateAllRequiredFields()) return;

    btnSubmit.disabled = true;
    btnDraft.disabled = true;
    const orig = btnSubmit.innerHTML;
    btnSubmit.innerHTML = 'Gravando...';
    if (saveStatusText) saveStatusText.textContent = 'Gravando respostas...';

    const payload = collectFormData();
    let resData = null;

    try {
      let endpoint = currentEditToken ? `/api/edit/${currentEditToken}` : '/api/submit';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) resData = await res.json();
    } catch (e) {
      // Fallback LocalStorage
    }

    if (!resData) {
      resData = saveToLocalStorage(payload, false);
    }

    currentEditToken = resData.edit_token;
    currentViewToken = resData.view_token;
    currentVersion = resData.version;

    window.history.replaceState({}, '', `?edit=${currentEditToken}`);
    if (saveStatusText) saveStatusText.textContent = 'Gravado com sucesso!';
    showToast('Tudo certo! Recebemos suas informações.', 'success');
    if (btnDirectPdf) btnDirectPdf.style.display = 'inline-flex';

    openShareModal(currentViewToken, currentEditToken, payload.cliente_razao_social);

    btnSubmit.disabled = false;
    btnDraft.disabled = false;
    btnSubmit.innerHTML = orig;
  });

  // 14. Modal de Compartilhamento
  function openShareModal(viewToken, editToken, clienteNome) {
    const base = window.location.origin + window.location.pathname;
    const viewUrl = `${base}?view=${viewToken}`;
    const editUrl = `${base}?edit=${editToken}`;
    const docUrl = `${base}?doc=${viewToken}`;

    const viewInput = document.getElementById('modal-view-url');
    const editInput = document.getElementById('modal-edit-url');
    const docBtn = document.getElementById('modal-doc-url');
    const btnShare = document.getElementById('btn-native-share');

    if (viewInput) viewInput.value = viewUrl;
    if (editInput) editInput.value = editUrl;
    if (docBtn) docBtn.href = docUrl;

    if (btnShare && navigator.share) {
      btnShare.style.display = 'inline-flex';
      btnShare.onclick = async () => {
        try {
          await navigator.share({
            title: `PJzen | Handoff: ${clienteNome || 'Cliente'}`,
            text: `Registro de Handoff PJzen:`,
            url: viewUrl
          });
        } catch (e) {}
      };
    }

    if (shareModal) shareModal.style.display = 'flex';
  }

  if (modalCloseBtn && shareModal) {
    modalCloseBtn.addEventListener('click', () => {
      shareModal.style.display = 'none';
    });
  }

  // 15. Geração de PDF no Aparelho (iOS, Android, Windows, Mac)
  async function downloadPdfDirect(filename = 'PJzen-Handoff.pdf') {
    const el = document.querySelector('.container') || document.body;
    if (window.html2pdf) {
      showToast('Gerando PDF no seu aparelho...', 'normal');
      const opt = {
        margin: [10, 8, 10, 8],
        filename: filename,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
      };
      await html2pdf().set(opt).from(el).save();
      showToast('PDF baixado com sucesso!', 'success');
    } else {
      window.print();
    }
  }

  if (btnDirectPdf) {
    btnDirectPdf.addEventListener('click', () => downloadPdfDirect());
  }

  const modalPdfBtn = document.getElementById('modal-pdf-download');
  if (modalPdfBtn) {
    modalPdfBtn.addEventListener('click', () => downloadPdfDirect());
  }

  // 16. Modos de Visualização e Edição a partir de Parâmetros de URL
  async function carregarDados(token) {
    try {
      const res = await fetch(`/api/get/${token}`);
      if (res.ok) {
        const json = await res.json();
        if (json.data) return json.data;
      }
    } catch (e) {}
    return getFromLocalStorage(token);
  }

  // Se o usuário abriu ?view=TOKEN
  if (viewTokenParam) {
    carregarDados(viewTokenParam).then(sub => {
      if (!sub) {
        showToast('Registro não encontrado neste aparelho.', 'error');
        return;
      }
      renderViewMode(sub);
    });
  } else if (docTokenParam) {
    carregarDados(docTokenParam).then(sub => {
      if (!sub) {
        showToast('Comprovante não encontrado neste aparelho.', 'error');
        return;
      }
      renderDossieMode(sub);
    });
  } else if (editTokenParam) {
    carregarDados(editTokenParam).then(sub => {
      if (!sub) return;
      populateForm(sub);
    });
  }

  function populateForm(sub) {
    currentVersion = sub.version || 1;
    currentEditToken = sub.edit_token || '';
    currentViewToken = sub.view_token || '';

    if (appStatusBadge) {
      appStatusBadge.style.display = 'inline-flex';
      appStatusBadge.className = `status-badge ${sub.status_tecnico || 'rascunho'}`;
      appStatusBadge.textContent = `${sub.status_tecnico === 'enviado' ? 'Enviado' : 'Rascunho'} (v${currentVersion})`;
    }

    const fields = [
      'nome_preenchedor', 'email_preenchedor', 'data_venda', 'cliente_razao_social',
      'cnpj', 'email_cliente', 'telefone_cliente', 'data_repasse',
      'atividade_cnae_municipio', 'atividades_secundarias', 'pontos_atencao_tecnicos',
      'demandas_acordadas', 'documentos_pendentes', 'prazo_combinado',
      'responsavel_onboarding', 'responsavel_tecnico', 'proxima_acao_resp_data'
    ];

    fields.forEach(f => {
      const el = document.getElementById(f);
      if (el && sub[f]) {
        el.value = sub[f];
        if (el.tagName === 'TEXTAREA') adjustHeight(el);
      }
    });

    const checkboxGroups = [
      'tipo_demanda', 'plano_contratado', 'faturamento_mensal_esperado',
      'tera_pro_labore', 'regime_tributario', 'tabela_apuracao_anexo',
      'frentes_acionadas', 'status_repasse'
    ];
    checkboxGroups.forEach(grp => {
      const vals = sub[grp] || [];
      form.querySelectorAll(`input[name="${grp}"]`).forEach(cb => {
        if (vals.includes(cb.value)) {
          cb.checked = true;
          const p = cb.closest('.checkbox-label');
          if (p) p.classList.add('is-checked');
        }
      });
    });

    if (sub.anexos_documentos && Array.isArray(sub.anexos_documentos)) {
      sub.anexos_documentos.forEach(att => addAttachmentCard(att));
    }

    if (btnDirectPdf) btnDirectPdf.style.display = 'inline-flex';
    if (saveStatusText) saveStatusText.textContent = 'Pronto para complementar ou salvar';
    const subBtn = document.getElementById('btn-submit-form');
    if (subBtn) subBtn.textContent = 'Salvar alterações';
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderViewMode(sub) {
    if (form) form.style.display = 'none';
    if (!viewContainer) return;
    viewContainer.style.display = 'block';

    const base = window.location.origin + window.location.pathname;
    const editUrl = `${base}?edit=${sub.edit_token || ''}`;
    const docUrl = `${base}?doc=${sub.view_token || ''}`;

    viewContainer.innerHTML = `
      <div class="name-highlight-card" style="border-left: 5px solid var(--pj-blue-dark);">
        <div class="form-grid-2">
          <div>
            <div class="view-label">Preenchido por</div>
            <div class="view-val" style="font-weight: 700; font-size: 1.05rem;">
              ${sub.nome_preenchedor || 'Não informado'}
            </div>
            ${sub.email_preenchedor ? `<div style="font-size: 0.85rem; color: var(--slate-500); margin-top: 2px;">E-mail: ${sub.email_preenchedor}</div>` : ''}
            ${sub.data_venda ? `<div style="font-size: 0.85rem; color: var(--slate-500); margin-top: 2px;">Data da venda: ${sub.data_venda}</div>` : ''}
          </div>
          <div>
            <div class="view-label">Status & Versão</div>
            <div class="view-val">
              <span class="status-badge ${sub.status_tecnico || 'enviado'}">${sub.status_tecnico === 'enviado' ? 'Enviado' : 'Rascunho'} (v${sub.version || 1})</span>
            </div>
            <div style="font-size: 0.82rem; color: var(--slate-500); margin-top: 6px;">
              Atualizado em: ${sub.updated_at ? sub.updated_at.replace('T', ' às ').substring(0, 19) : 'Hoje'}
            </div>
          </div>
        </div>
      </div>

      <!-- 01 Identificação -->
      <section class="form-section">
        <div class="section-header">01 IDENTIFICAÇÃO E CONTRATAÇÃO | Comercial</div>
        <div class="section-body">
          <div class="form-grid-2">
            <div class="view-field-row"><div class="view-label">Nome do cliente</div><div class="view-val">${sub.cliente_razao_social || 'Não informado'}</div></div>
            <div class="view-field-row"><div class="view-label">CNPJ</div><div class="view-val">${sub.cnpj || 'Não informado'}</div></div>
          </div>
          <div class="form-grid-2">
            <div class="view-field-row"><div class="view-label">E-mail do cliente</div><div class="view-val">${sub.email_cliente || 'Não informado'}</div></div>
            <div class="view-field-row"><div class="view-label">Telefone do cliente</div><div class="view-val">${sub.telefone_cliente || 'Não informado'}</div></div>
          </div>
          <div class="view-field-row"><div class="view-label">Data do repasse</div><div class="view-val">${sub.data_repasse || 'Não informado'}</div></div>
          <div class="view-field-row"><div class="view-label">Tipo de demanda</div><div class="view-val">${(sub.tipo_demanda || []).join(', ') || 'Nenhum'}</div></div>
          <div class="view-field-row"><div class="view-label">Plano contratado</div><div class="view-val">${(sub.plano_contratado || []).join(', ') || 'Nenhum'}</div></div>
          <div class="view-field-row"><div class="view-label">Faturamento mensal esperado</div><div class="view-val">${(sub.faturamento_mensal_esperado || []).join(', ') || 'Nenhum'}</div></div>
          <div class="view-field-row"><div class="view-label">Atividade principal / CNAE e município</div><div class="view-val">${sub.atividade_cnae_municipio || 'Não informado'}</div></div>
          <div class="view-field-row"><div class="view-label">Atividades secundárias</div><div class="view-val">${sub.atividades_secundarias || 'Não informado'}</div></div>
        </div>
      </section>

      <!-- 02 Diagnóstico -->
      <section class="form-section">
        <div class="section-header">02 DIAGNÓSTICO TRIBUTÁRIO | Time técnico</div>
        <div class="section-body">
          <div class="view-field-row"><div class="view-label">Terá pró-labore?</div><div class="view-val">${(sub.tera_pro_labore || []).join(', ') || 'Não informado'}</div></div>
          <div class="view-field-row"><div class="view-label">Regime tributário</div><div class="view-val">${(sub.regime_tributario || []).join(', ') || 'Não informado'}</div></div>
          <div class="view-field-row"><div class="view-label">Tabelas e anexo</div><div class="view-val">${(sub.tabela_apuracao_anexo || []).join(', ') || 'Não informado'}</div></div>
          <div class="view-field-row"><div class="view-label">Pontos de atenção técnicos</div><div class="view-val">${sub.pontos_atencao_tecnicos || 'Não informado'}</div></div>
        </div>
      </section>

      <!-- 03 O que precisa ser feito -->
      <section class="form-section">
        <div class="section-header">03 O QUE PRECISA SER FEITO | Comercial + Técnico</div>
        <div class="section-body">
          <div class="view-field-row"><div class="view-label">Frentes acionadas</div><div class="view-val">${(sub.frentes_acionadas || []).join(', ') || 'Nenhuma'}</div></div>
          <div class="view-field-row"><div class="view-label">Demandas acordadas</div><div class="view-val">${sub.demandas_acordadas || 'Não informado'}</div></div>
          <div class="view-field-row"><div class="view-label">Descrição de documentos anexados</div><div class="view-val">${sub.documentos_pendentes || 'Não informado'}</div></div>
          <div class="view-field-row"><div class="view-label">Prazo combinado</div><div class="view-val">${sub.prazo_combinado || 'Não informado'}</div></div>
        </div>
      </section>

      <!-- 04 Validação -->
      <section class="form-section">
        <div class="section-header">04 VALIDAÇÃO DO REPASSE</div>
        <div class="section-body">
          <div class="form-grid-2">
            <div class="view-field-row"><div class="view-label">Responsável pelo onboarding</div><div class="view-val">${sub.responsavel_onboarding || 'Não informado'}</div></div>
            <div class="view-field-row"><div class="view-label">Responsável técnico</div><div class="view-val">${sub.responsavel_tecnico || 'Não informado'}</div></div>
          </div>
          <div class="view-field-row"><div class="view-label">Status</div><div class="view-val">${(sub.status_repasse || []).join(', ') || 'Não informado'}</div></div>
          <div class="view-field-row"><div class="view-label">Próxima ação / responsável / data</div><div class="view-val">${sub.proxima_acao_resp_data || 'Não informado'}</div></div>
        </div>
      </section>

      <!-- Barra de Ações -->
      <div class="action-bar">
        <div class="action-status-text">Visualização oficial de repasse (somente leitura)</div>
        <div class="action-buttons">
          <a href="${editUrl}" class="btn btn-secondary">Editar Informações</a>
          <a href="${docUrl}" class="btn btn-secondary">Ver Dossiê</a>
          <button type="button" class="btn btn-pdf" onclick="downloadPdfDirect('Handoff-${sub.cliente_razao_social || 'PJzen'}.pdf')">Baixar PDF</button>
          <button type="button" class="btn btn-secondary" onclick="window.print()">Imprimir</button>
        </div>
      </div>
    `;
  }

  function renderDossieMode(sub) {
    if (form) form.style.display = 'none';
    if (!viewContainer) return;
    viewContainer.style.display = 'block';

    const anexos = sub.anexos_documentos || [];
    const base = window.location.origin + window.location.pathname;

    viewContainer.innerHTML = `
      <div class="name-highlight-card" style="border-left: 5px solid var(--pj-blue-dark);">
        <div class="form-grid-2">
          <div>
            <div class="view-label">Preenchido por</div>
            <div class="view-val" style="font-weight: 700;">${sub.nome_preenchedor || 'Não informado'}</div>
            ${sub.email_preenchedor ? `<div style="font-size: 0.85rem; color: var(--slate-500);">E-mail: ${sub.email_preenchedor}</div>` : ''}
          </div>
          <div>
            <div class="view-label">Nome do cliente</div>
            <div class="view-val" style="font-weight: 700;">${sub.cliente_razao_social || 'Não informado'}</div>
            ${sub.cnpj ? `<div style="font-size: 0.85rem; color: var(--slate-500);">CNPJ: ${sub.cnpj}</div>` : ''}
          </div>
        </div>
      </div>

      <section class="form-section">
        <div class="section-header">
          <span>Documentos e Mídias Registrados</span>
          <span style="font-size: 0.85rem; font-weight: 500; background: var(--pj-beige); padding: 4px 10px; border-radius: 6px;">Total: ${anexos.length} item(ns)</span>
        </div>
        <div class="section-body">
          ${anexos.length === 0 ? '<p style="text-align: center; color: var(--slate-500); padding: 20px;">Nenhum anexo registrado.</p>' : ''}
          ${anexos.map(anexo => `
            <div style="background: var(--pj-white); border: 1px solid var(--slate-200); border-radius: 8px; padding: 14px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
              <div>
                <strong>${anexo.nome_original}</strong> (${anexo.tipo})
                <div style="font-size: 0.82rem; color: var(--slate-500); margin-top: 2px;">
                  Carimbo de Data: <strong>${anexo.data_pc}</strong> | ${anexo.storage}
                </div>
              </div>
              <a href="${anexo.url}" target="_blank" class="btn btn-secondary" style="padding: 6px 14px; font-size: 0.85rem; width: auto;">Abrir Arquivo</a>
            </div>
          `).join('')}
        </div>
      </section>

      <div class="action-bar">
        <div class="action-status-text">Comprovante cronológico de documentos</div>
        <div class="action-buttons">
          <a href="${base}?view=${sub.view_token || ''}" class="btn btn-secondary">Ver Handoff Completo</a>
          <button type="button" class="btn btn-primary" onclick="window.print()">Imprimir Comprovante</button>
        </div>
      </div>
    `;
  }
});
