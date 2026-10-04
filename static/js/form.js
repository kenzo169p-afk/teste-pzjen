document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('handoff-form');
  if (!form) return;

  const btnDraft = document.getElementById('btn-save-draft');
  const btnSubmit = document.getElementById('btn-submit-form');
  const nameInput = document.getElementById('nome_preenchedor');
  const nameCard = document.getElementById('name-card');
  const nameError = document.getElementById('name-error-msg');
  const saveStatusText = document.getElementById('save-status-text');
  const shareModal = document.getElementById('share-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');

  // Initial state from data attributes
  let currentEditToken = form.dataset.editToken || '';
  let currentViewToken = form.dataset.viewToken || '';
  let currentVersion = parseInt(form.dataset.version || '1', 10);
  const isEditMode = Boolean(currentEditToken);

  // 1. Auto-resize all textareas
  const textareas = form.querySelectorAll('textarea');
  function adjustHeight(el) {
    el.style.height = 'auto';
    el.style.height = Math.max(el.scrollHeight, 80) + 'px';
  }
  textareas.forEach(ta => {
    adjustHeight(ta);
    ta.addEventListener('input', () => adjustHeight(ta));
  });

  // 2. Checkbox visual toggle
  const checkboxes = form.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(cb => {
    const parentLabel = cb.closest('.checkbox-label');
    if (cb.checked && parentLabel) {
      parentLabel.classList.add('is-checked');
    }
    cb.addEventListener('change', () => {
      if (parentLabel) {
        if (cb.checked) {
          parentLabel.classList.add('is-checked');
        } else {
          parentLabel.classList.remove('is-checked');
        }
      }
    });
  });

  // 3. Optional CNPJ Mask
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

  // 4. Phone Mask for all .phone-mask elements
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

  // 5. Toast notifications
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

  // 6. Media and Documents Upload Management
  const fileInput = document.getElementById('file-upload-input');
  const btnTriggerUpload = document.getElementById('btn-trigger-upload');
  const uploadSpinner = document.getElementById('upload-spinner');
  const videoAlert = document.getElementById('video-duration-alert');
  const attachmentsContainer = document.getElementById('attachments-container');

  if (btnTriggerUpload && fileInput) {
    btnTriggerUpload.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      if (videoAlert) videoAlert.style.display = 'none';

      // Check if video -> enforce max 10 seconds
      if (file.type.startsWith('video/')) {
        const video = document.createElement('video');
        video.preload = 'metadata';
        const objectUrl = URL.createObjectURL(file);
        video.src = objectUrl;

        video.onloadedmetadata = () => {
          URL.revokeObjectURL(objectUrl);
          const duration = video.duration;
          if (duration > 10.5) {
            if (videoAlert) {
              videoAlert.textContent = `Atenção: O vídeo selecionado possui aproximadamente ${Math.round(duration)} segundos. O limite máximo permitido é de 10 segundos.`;
              videoAlert.style.display = 'block';
            }
            showToast('Vídeo excede o limite máximo de 10 segundos.', 'error');
            fileInput.value = '';
            return;
          }
          // Duration OK, upload
          uploadFile(file);
        };

        video.onerror = () => {
          URL.revokeObjectURL(objectUrl);
          if (videoAlert) {
            videoAlert.textContent = 'Não foi possível validar a duração do vídeo. Verifique se o formato é suportado.';
            videoAlert.style.display = 'block';
          }
          fileInput.value = '';
        };
      } else {
        // Image or PDF
        uploadFile(file);
      }
    });
  }

  async function uploadFile(file) {
    if (!uploadSpinner || !btnTriggerUpload) return;
    uploadSpinner.style.display = 'inline-block';
    btnTriggerUpload.disabled = true;

    // Capture the exact date and time from user PC
    const now = new Date();
    const clientDatePc = now.toLocaleDateString('pt-BR') + ' às ' + now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('client_date_pc', clientDatePc);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Erro ao processar envio do arquivo.');
      }

      addAttachmentCard({
        url: data.url,
        nome_original: data.nome_original,
        tipo: data.tipo,
        tamanho_formatado: data.tamanho_formatado,
        data_pc: data.data_pc,
        storage: data.storage
      });

      showToast('Documento anexado com sucesso!', 'success');
    } catch (err) {
      console.error(err);
      showToast(err.message || 'Erro ao realizar upload do documento.', 'error');
    } finally {
      uploadSpinner.style.display = 'none';
      btnTriggerUpload.disabled = false;
      fileInput.value = '';
    }
  }

  function addAttachmentCard(att) {
    if (!attachmentsContainer) return;
    const item = document.createElement('div');
    item.className = 'attachment-item';
    item.dataset.url = att.url;
    item.dataset.name = att.nome_original;
    item.dataset.tipo = att.tipo;
    item.dataset.size = att.tamanho_formatado;
    item.dataset.date = att.data_pc;
    item.dataset.storage = att.storage;
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
        <button type="button" class="btn btn-danger btn-remove-attachment" style="padding: 4px 10px; font-size: 0.8rem; min-height: 32px; width: auto;">Remover</button>
      </div>
    `;

    attachmentsContainer.appendChild(item);
  }

  // Handle remove attachment
  if (attachmentsContainer) {
    attachmentsContainer.addEventListener('click', (e) => {
      const btnRemove = e.target.closest('.btn-remove-attachment');
      if (btnRemove) {
        const item = btnRemove.closest('.attachment-item');
        if (item) {
          item.remove();
          showToast('Anexo removido do formulário.', 'normal');
        }
      }
    });
  }

  // 7. Gather Form Data
  function collectFormData() {
    const data = {};
    // Text, Tel, Email and Date inputs
    const inputs = form.querySelectorAll('input:not([type="checkbox"]):not([type="file"]), textarea');
    inputs.forEach(input => {
      if (input.name) {
        data[input.name] = input.value;
      }
    });

    // Checkbox groups
    const checkboxGroups = [
      'tipo_demanda',
      'plano_contratado',
      'faturamento_mensal_esperado',
      'tera_pro_labore',
      'simples_nacional',
      'regime_tributario',
      'tabela_apuracao_anexo',
      'frentes_acionadas',
      'status_repasse'
    ];

    checkboxGroups.forEach(groupName => {
      const checked = form.querySelectorAll(`input[name="${groupName}"]:checked`);
      data[groupName] = Array.from(checked).map(c => c.value);
    });

    // Anexos de documentos e mídias
    const attachmentItems = form.querySelectorAll('#attachments-container .attachment-item');
    const anexos = [];
    attachmentItems.forEach(it => {
      anexos.push({
        url: it.dataset.url,
        nome_original: it.dataset.name,
        tipo: it.dataset.tipo,
        tamanho_formatado: it.dataset.size,
        data_pc: it.dataset.date,
        storage: it.dataset.storage
      });
    });
    data['anexos_documentos'] = anexos;

    return data;
  }

  // 6. Save Draft action
  btnDraft.addEventListener('click', async () => {
    if (btnDraft.disabled) return;
    btnDraft.disabled = true;
    const origDraftText = btnDraft.innerHTML;
    btnDraft.innerHTML = 'Salvando...';
    if (saveStatusText) saveStatusText.textContent = 'Salvando rascunho...';

    const payload = collectFormData();
    payload['expected_version'] = currentVersion;

    try {
      let endpoint = currentEditToken ? `/api/edit/${currentEditToken}` : '/api/draft';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const res = await response.json();
      if (!response.ok) {
        throw new Error(res.error || 'Erro ao salvar rascunho.');
      }

      currentEditToken = res.edit_token;
      currentViewToken = res.view_token;
      currentVersion = res.version;
      form.dataset.editToken = currentEditToken;
      form.dataset.viewToken = currentViewToken;
      form.dataset.version = currentVersion;

      // Update URL if this was a new submission
      if (!window.location.pathname.startsWith('/edit/')) {
        window.history.replaceState({}, '', `/edit/${currentEditToken}`);
      }

      // Update PDF button if present
      const btnPdf = document.getElementById('btn-download-pdf');
      if (btnPdf) {
        btnPdf.style.display = 'inline-flex';
        btnPdf.href = `/pdf/${currentViewToken}`;
      }

      showToast('Informações salvas com sucesso!', 'success');
      if (saveStatusText) saveStatusText.textContent = 'Informações salvas';
    } catch (err) {
      console.error(err);
      showToast(err.message || 'Não foi possível salvar o rascunho. Suas respostas continuam na tela.', 'error');
      if (saveStatusText) saveStatusText.textContent = 'Erro ao salvar';
    } finally {
      btnDraft.disabled = false;
      btnDraft.innerHTML = origDraftText;
    }
  });

  // Clear invalid outline on typing or selection
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

  function validateAllRequiredFields() {
    let firstInvalid = null;
    let hasError = false;

    // Reset previous invalid states
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    if (nameCard) nameCard.classList.remove('error-state');
    if (nameError) nameError.style.display = 'none';

    // 1. Text, email, tel, date inputs and textareas
    const requiredInputIds = [
      'nome_preenchedor',
      'email_preenchedor',
      'data_venda',
      'cliente_razao_social',
      'email_cliente',
      'telefone_cliente',
      'data_repasse',
      'atividade_cnae_municipio',
      'atividades_secundarias',
      'pontos_atencao_tecnicos',
      'demandas_acordadas',
      'documentos_pendentes',
      'prazo_combinado',
      'responsavel_onboarding',
      'responsavel_tecnico',
      'proxima_acao_resp_data'
    ];

    requiredInputIds.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        const val = el.value.trim();
        if (!val) {
          el.classList.add('is-invalid');
          hasError = true;
          if (!firstInvalid) firstInvalid = el;
        }
      }
    });

    // 2. Checkbox groups
    const requiredCheckboxGroups = [
      'tipo_demanda',
      'plano_contratado',
      'faturamento_mensal_esperado',
      'tera_pro_labore',
      'regime_tributario',
      'tabela_apuracao_anexo',
      'frentes_acionadas',
      'status_repasse'
    ];

    requiredCheckboxGroups.forEach(groupName => {
      const checked = form.querySelectorAll(`input[name="${groupName}"]:checked`);
      if (checked.length === 0) {
        const firstCb = form.querySelector(`input[name="${groupName}"]`);
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
        if (typeof firstInvalid.focus === 'function') {
          firstInvalid.focus();
        }
      }
      showToast('Por favor, preencha todos os campos obrigatórios antes de enviar.', 'error');
      return false;
    }

    return true;
  }

  // 7. Submit / Save Changes action
  btnSubmit.addEventListener('click', async () => {
    if (btnSubmit.disabled) return;

    if (!validateAllRequiredFields()) {
      return;
    }

    // Prevent double click
    btnSubmit.disabled = true;
    if (btnDraft) btnDraft.disabled = true;
    const origSubmitText = btnSubmit.innerHTML;
    btnSubmit.innerHTML = 'Gravando...';
    if (saveStatusText) saveStatusText.textContent = 'Gravando respostas...';

    const payload = collectFormData();
    payload['expected_version'] = currentVersion;

    try {
      let endpoint = currentEditToken ? `/api/edit/${currentEditToken}` : '/api/submit';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const res = await response.json();
      if (!response.ok) {
        throw new Error(res.error || 'Erro ao gravar formulário.');
      }

      currentEditToken = res.edit_token;
      currentViewToken = res.view_token;
      currentVersion = res.version;
      form.dataset.editToken = currentEditToken;
      form.dataset.viewToken = currentViewToken;
      form.dataset.version = currentVersion;

      // Update URL if brand new
      if (!window.location.pathname.startsWith('/edit/')) {
        window.history.replaceState({}, '', `/edit/${currentEditToken}`);
      }

      // Update PDF button
      const btnPdf = document.getElementById('btn-download-pdf');
      if (btnPdf) {
        btnPdf.style.display = 'inline-flex';
        btnPdf.href = `/pdf/${currentViewToken}`;
      }

      if (saveStatusText) saveStatusText.textContent = 'Gravado com sucesso!';
      showToast('Tudo certo! Recebemos suas informações.', 'success');

      // Populate & open Share Modal
      openShareModal(res.view_token, res.edit_token, res.email_delivery, res.to_email);

    } catch (err) {
      console.error(err);
      showToast(err.message || 'Falha de conexão. Suas respostas permanecem na tela. Tente novamente.', 'error');
      if (saveStatusText) saveStatusText.textContent = 'Erro ao enviar';
      btnSubmit.disabled = false;
      if (btnDraft) btnDraft.disabled = false;
      btnSubmit.innerHTML = origSubmitText;
    }
  });

  // Modal setup
  function openShareModal(viewToken, editToken, emailDelivery, toEmail) {
    const origin = window.location.origin;
    const viewUrl = `${origin}/view/${viewToken}`;
    const editUrl = `${origin}/edit/${editToken}`;
    const pdfUrl = `${origin}/pdf/${viewToken}`;
    const docUrl = `${origin}/documento/${viewToken}`;

    const viewInput = document.getElementById('modal-view-url');
    const editInput = document.getElementById('modal-edit-url');
    const pdfBtn = document.getElementById('modal-pdf-download');
    const docBtn = document.getElementById('modal-doc-url');

    if (viewInput) viewInput.value = viewUrl;
    if (editInput) editInput.value = editUrl;
    if (pdfBtn) pdfBtn.href = pdfUrl;
    if (docBtn) docBtn.href = docUrl;

    const emailBox = document.getElementById('modal-email-box');
    const emailText = document.getElementById('modal-email-text');
    if (emailBox && emailText) {
      if (emailDelivery && emailDelivery.sent) {
        emailBox.style.display = 'block';
        emailBox.style.backgroundColor = '#ecfdf5';
        emailBox.style.border = '1px solid #a7f3d0';
        emailBox.style.color = '#065f46';
        emailText.innerHTML = `
          <strong style="font-size: 0.95rem;">📧 E-mail Enviado!</strong>
          <div style="margin-top: 4px; font-size: 0.86rem;">Uma cópia com os links deste registro e lista de anexos foi entregue para <strong>${toEmail}</strong>.</div>
        `;
      } else if (toEmail) {
        emailBox.style.display = 'block';
        emailBox.style.backgroundColor = 'var(--pj-offwhite)';
        emailBox.style.border = '1px solid var(--slate-200)';
        emailBox.style.borderLeft = '4px solid var(--pj-blue-intense)';
        emailBox.style.color = 'var(--pj-gray-dark)';
        
        emailText.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <strong style="color: var(--pj-blue-dark); font-size: 0.92rem;">📬 Envio do E-mail para: ${toEmail}</strong>
            <span class="view-tag-off" style="font-size: 0.75rem;">Aguardando ativação Gmail</span>
          </div>
          <p style="margin: 6px 0 10px 0; font-size: 0.84rem; line-height: 1.45;">
            Seu formulário e os anexos foram salvos com sucesso. Para que o e-mail chegue diretamente à sua caixa de entrada, ative a conexão com o seu Gmail ou veja a prévia do e-mail no navegador.
          </p>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button type="button" class="btn btn-primary" style="font-size: 0.84rem; padding: 6px 14px; width: auto;" onclick="openEmailConfigModal('${toEmail}', '${viewToken}')">
              ⚙️ Conectar Gmail para Enviar
            </button>
            <a href="/preview-email/${viewToken}" target="_blank" class="btn btn-secondary" style="font-size: 0.84rem; padding: 6px 14px; width: auto;">
              👁️ Ver Prévia do E-mail
            </a>
          </div>
        `;
      } else {
        emailBox.style.display = 'none';
      }
    }

    // Botão de compartilhamento nativo para celulares/tablets (WhatsApp, AirDrop, etc.)
    const btnShare = document.getElementById('btn-native-share');
    if (btnShare) {
      if (navigator.share) {
        btnShare.style.display = 'inline-flex';
        btnShare.onclick = async () => {
          try {
            await navigator.share({
              title: 'PJzen | Handoff Registrado',
              text: 'Registro de Handoff Comercial PJzen e documentos anexados:',
              url: viewUrl
            });
          } catch (err) {
            // Cancelado pelo usuário
          }
        };
      } else {
        btnShare.style.display = 'none';
      }
    }

    if (shareModal) {
      shareModal.style.display = 'flex';
    }
  }

  // Geração de PDF no lado do cliente (fallback universal para celulares/tablets/hosts estáticos)
  window.gerarPdfCliente = async function(nomeArquivo = 'PJzen-Handoff.pdf') {
    const el = document.querySelector('.container') || document.body;
    if (window.html2pdf) {
      showToast('Gerando PDF no seu dispositivo...', 'normal');
      const opt = {
        margin: [10, 8, 10, 8],
        filename: nomeArquivo,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
      };
      await html2pdf().set(opt).from(el).save();
      showToast('PDF baixado com sucesso!', 'success');
    } else {
      window.print();
    }
  };

  // Open / Close Email Config Modal
  const emailCfgModal = document.getElementById('email-config-modal');
  const btnCloseEmailCfg = document.getElementById('btn-close-email-cfg');
  const btnSaveEmailCfg = document.getElementById('btn-save-email-cfg');
  const cfgEmailUser = document.getElementById('cfg-email-user');
  const cfgEmailPass = document.getElementById('cfg-email-pass');
  const cfgEmailError = document.getElementById('cfg-email-error');

  window.openEmailConfigModal = function(defaultEmail, viewToken) {
    if (cfgEmailUser && defaultEmail) {
      cfgEmailUser.value = defaultEmail;
    }
    if (cfgEmailError) cfgEmailError.style.display = 'none';
    if (emailCfgModal) emailCfgModal.style.display = 'flex';
  };

  if (btnCloseEmailCfg && emailCfgModal) {
    btnCloseEmailCfg.addEventListener('click', () => {
      emailCfgModal.style.display = 'none';
    });
  }

  if (btnSaveEmailCfg) {
    btnSaveEmailCfg.addEventListener('click', async () => {
      const email = cfgEmailUser ? cfgEmailUser.value.trim() : '';
      const pass = cfgEmailPass ? cfgEmailPass.value.trim() : '';

      if (!email || !pass) {
        if (cfgEmailError) {
          cfgEmailError.textContent = 'Por favor, informe o seu Gmail e a senha de aplicativo de 16 letras.';
          cfgEmailError.style.display = 'block';
        }
        return;
      }

      if (cfgEmailError) cfgEmailError.style.display = 'none';
      btnSaveEmailCfg.disabled = true;
      const origText = btnSaveEmailCfg.textContent;
      btnSaveEmailCfg.textContent = 'Testando conexão com o Gmail...';

      try {
        const res = await fetch('/api/configure-email', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            smtp_user: email,
            smtp_password: pass,
            token: currentViewToken
          })
        });

        const data = await res.json();
        if (!res.ok || !data.success) {
          throw new Error(data.error || 'Erro ao autenticar com o Gmail.');
        }

        showToast('Gmail conectado! E-mail enviado com sucesso!', 'success');
        if (emailCfgModal) emailCfgModal.style.display = 'none';

        // Update modal box
        const emailBox = document.getElementById('modal-email-box');
        const emailText = document.getElementById('modal-email-text');
        if (emailBox && emailText) {
          emailBox.style.backgroundColor = '#ecfdf5';
          emailBox.style.border = '1px solid #a7f3d0';
          emailBox.style.color = '#065f46';
          emailText.innerHTML = `
            <strong style="font-size: 0.95rem;">📧 E-mail Enviado com Sucesso!</strong>
            <div style="margin-top: 4px; font-size: 0.86rem;">Uma cópia com os links deste registro e lista de anexos foi entregue para <strong>${email}</strong>.</div>
          `;
        }

      } catch (err) {
        if (cfgEmailError) {
          cfgEmailError.textContent = err.message;
          cfgEmailError.style.display = 'block';
        }
      } finally {
        btnSaveEmailCfg.disabled = false;
        btnSaveEmailCfg.textContent = origText;
      }
    });
  }

  if (modalCloseBtn && shareModal) {
    modalCloseBtn.addEventListener('click', () => {
      shareModal.style.display = 'none';
      btnSubmit.disabled = false;
      if (btnDraft) btnDraft.disabled = false;
      btnSubmit.innerHTML = 'Salvar alterações';
    });
  }

  // Copy helper
  window.copyToClipboard = function(inputId, feedbackBtnId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    navigator.clipboard.writeText(input.value).then(() => {
      const btn = document.getElementById(feedbackBtnId);
      if (btn) {
        const orig = btn.textContent;
        btn.textContent = 'Copiado!';
        btn.style.backgroundColor = '#FFD100';
        btn.style.color = '#1C1B1F';
        btn.style.borderColor = '#FFD100';
        setTimeout(() => {
          btn.textContent = orig;
          btn.style.backgroundColor = '';
          btn.style.color = '';
          btn.style.borderColor = '';
        }, 2000);
      }
      showToast('Link copiado com sucesso!', 'success');
    }).catch(err => {
      console.error(err);
      showToast('Não foi possível copiar automaticamente.', 'error');
    });
  };
});
