import io
import re
from datetime import datetime
import requests
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory, redirect, url_for, abort
import database
import pdf_generator
import supabase_storage
import email_service

import time
from collections import defaultdict

TOKEN_SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]{8,64}$')
_failed_lookups = defaultdict(list)

def is_safe_token(token: str) -> bool:
    if not token or not isinstance(token, str):
        return False
    return bool(TOKEN_SAFE_PATTERN.match(token))

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    _failed_lookups[ip] = [t for t in _failed_lookups[ip] if now - t < 60]
    return len(_failed_lookups[ip]) >= 30

def record_failed_lookup(ip: str):
    _failed_lookups[ip].append(time.time())

app = Flask(__name__)
database.init_db()

@app.after_request
def apply_security_headers(response):
    """Aplica cabeçalhos de defesa para proteção de dados contra vazamentos."""
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
def index():
    """Formulário limpo para novos preenchimentos. Não expõe registros de outros clientes."""
    return render_template("form.html", sub=None, is_edit=False)

@app.route("/edit/<token>")
def edit_view(token):
    """Página de edição/complementação acessível somente via edit_token."""
    ip = request.remote_addr or "unknown"
    if is_rate_limited(ip):
        return render_template("error.html", title="Muitas tentativas", message="Limite de tentativas excedido. Aguarde 1 minuto."), 429
    if not is_safe_token(token):
        record_failed_lookup(ip)
        return render_template("error.html", title="Link inválido", message="O link de edição acessado é inválido."), 400

    sub = database.get_by_edit_token(token)
    if not sub:
        record_failed_lookup(ip)
        return render_template(
            "error.html", 
            title="Registro de edição não encontrado", 
            message="O link de edição acessado é inválido ou expirou."
        ), 404
    return render_template("form.html", sub=sub, is_edit=True)

@app.route("/view/<token>")
def view_only(token):
    """Página de consulta em modo somente leitura acessível via view_token."""
    ip = request.remote_addr or "unknown"
    if is_rate_limited(ip):
        return render_template("error.html", title="Muitas tentativas", message="Limite de tentativas excedido. Aguarde 1 minuto."), 429
    if not is_safe_token(token):
        record_failed_lookup(ip)
        return render_template("error.html", title="Link inválido", message="O link de consulta informado é inválido."), 400

    sub = database.get_by_view_token(token)
    if not sub:
        record_failed_lookup(ip)
        return render_template(
            "error.html", 
            title="Registro de consulta não encontrado", 
            message="O link de consulta informado não existe ou é inválido."
        ), 404
    return render_template("view.html", sub=sub)

@app.route("/documento/<token>")
def view_documento(token):
    """Visualização do comprovante e lista cronológica de documentos com data do PC."""
    ip = request.remote_addr or "unknown"
    if is_rate_limited(ip):
        return render_template("error.html", title="Muitas tentativas", message="Limite de tentativas excedido. Aguarde 1 minuto."), 429
    if not is_safe_token(token):
        record_failed_lookup(ip)
        return render_template("error.html", title="Link inválido", message="O link para este comprovante é inválido."), 400

    sub = database.get_by_any_token(token)
    if not sub:
        record_failed_lookup(ip)
        return render_template(
            "error.html", 
            title="Comprovante de documentos não encontrado", 
            message="O link para este comprovante é inválido ou expirou."
        ), 404
    return render_template("documento.html", sub=sub)

@app.route("/manifest.json")
def serve_manifest():
    return send_from_directory(".", "manifest.json", mimetype="application/manifest+json")

@app.route("/sw.js")
def serve_sw():
    return send_from_directory(".", "sw.js", mimetype="application/javascript")

@app.route("/api/log-acesso", methods=["POST"])
def api_log_acesso():
    """
    Registra entrada e saída no Supabase com data, horário e IP do computador.
    REGRA ESTRITA: Só registra quando estiver fora do localhost (ex: Hostinger ou produção).
    Em localhost, ignora e retorna sucesso sem chamar o Supabase.
    """
    host = (request.host or "").lower()
    remote_addr = request.remote_addr or ""
    
    is_localhost = (
        "localhost" in host or
        "127.0.0.1" in host or
        remote_addr in ("127.0.0.1", "::1", "0.0.0.0") or
        host.endswith(".local")
    )
    
    if is_localhost:
        return jsonify({
            "success": True,
            "ignored": True,
            "reason": "Ambiente localhost ignorado. Logs no Supabase so sao gravados em producao/Hostinger."
        }), 200

    payload = request.get_json(silent=True) or {}
    
    # Obter IP real do visitante (inclusive atras de proxies Cloudflare/Hostinger)
    client_ip = (
        request.headers.get("CF-Connecting-IP") or
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
        request.headers.get("X-Real-IP") or
        remote_addr
    )
    
    supabase_url, supabase_key, _ = supabase_storage.get_supabase_config()
    if not supabase_url or not supabase_key:
        return jsonify({
            "success": False,
            "error": "Credenciais do Supabase nao configuradas no .env"
        }), 200

    tipo_evento = payload.get("tipo_evento", "entrada")
    horario = payload.get("horario") or datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    pagina = payload.get("pagina", "/")
    dispositivo = payload.get("dispositivo") or request.headers.get("User-Agent", "Desconhecido")
    session_id = payload.get("session_id")
    tempo_permanencia = payload.get("tempo_permanencia_segundos", 0)

    supabase_payload = {
        "tipo_evento": tipo_evento,
        "horario": horario,
        "ip": client_ip,
        "pagina": pagina,
        "dispositivo": dispositivo,
        "session_id": session_id,
        "tempo_permanencia_segundos": tempo_permanencia,
        "host": host
    }

    try:
        endpoint = f"{supabase_url}/rest/v1/acessos_logs"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        resp = requests.post(endpoint, json=supabase_payload, headers=headers, timeout=5)
        ok = resp.status_code in (200, 201)
        return jsonify({
            "success": ok,
            "logged": ok,
            "ip": client_ip,
            "horario": horario,
            "tipo_evento": tipo_evento,
            "status_code": resp.status_code
        }), (200 if ok else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    """Serve arquivos locais quando em modo fallback (sem chaves do Supabase)."""
    return send_from_directory(supabase_storage.UPLOAD_DIR, filename)

@app.route("/api/upload", methods=["POST"])
def api_upload_file():
    """Recebe um arquivo (imagem, PDF ou vídeo até 10s), data do PC e faz upload para o Supabase Storage."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"success": False, "error": "Nome de arquivo inválido"}), 400

    data_pc = request.form.get("data_pc") or request.form.get("client_date_pc") or datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    
    # Limite de segurança: 50MB
    file_bytes = file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        return jsonify({"success": False, "error": "Arquivo excede o tamanho limite permitido de 50MB"}), 400

    content_type = file.content_type or "application/octet-stream"
    tipo_declarado = request.form.get("tipo")
    if not tipo_declarado:
        if content_type.startswith("image/"):
            tipo_declarado = "Imagem"
        elif content_type.startswith("video/"):
            tipo_declarado = "Vídeo (<=10s)"
        elif "pdf" in content_type:
            tipo_declarado = "Documento PDF"
        else:
            tipo_declarado = "Documento"

    result = supabase_storage.upload_to_storage(file_bytes, file.filename, content_type=content_type)

    # Formatar tamanho legível
    tam_kb = len(file_bytes) / 1024
    tam_formatado = f"{tam_kb:.1f} KB" if tam_kb < 1024 else f"{(tam_kb/1024):.2f} MB"

    return jsonify({
        "success": True,
        "url": result["url"],
        "nome_original": file.filename,
        "filename": result["filename"],
        "storage": result["storage"],
        "tipo": tipo_declarado,
        "mime": content_type,
        "tamanho": len(file_bytes),
        "tamanho_formatado": tam_formatado,
        "data_pc": data_pc
    }), 201

@app.route("/api/draft", methods=["POST"])
def api_save_draft():
    """Salva rascunho parcial. Nome é opcional nesta rota."""
    payload = request.get_json(silent=True) or {}
    result = database.create_submission(payload, is_draft=True)
    return jsonify({
        "success": True,
        "id": result["id"],
        "view_token": result["view_token"],
        "edit_token": result["edit_token"],
        "version": result["version"],
        "status_tecnico": result["status_tecnico"],
        "message": "Informações salvas com sucesso"
    }), 201

@app.route("/api/submit", methods=["POST"])
def api_submit_form():
    """Envia formulário. Somente 'nome_preenchedor' é estritamente obrigatório."""
    payload = request.get_json(silent=True) or {}
    nome = (payload.get("nome_preenchedor") or "").strip()
    if not nome:
        return jsonify({
            "success": False,
            "error": "Informe seu nome para enviar"
        }), 400

    result = database.create_submission(payload, is_draft=False)

    # Disparo automático de e-mail se informado
    email_delivery = None
    full_sub = database.get_by_view_token(result["view_token"])
    to_email = (payload.get("email_preenchedor") or payload.get("email_cliente") or "").strip()
    if to_email and full_sub:
        try:
            base_url = request.host_url.rstrip("/")
            email_delivery = email_service.send_handoff_email(to_email, full_sub, base_url)
        except Exception as e:
            email_delivery = {"success": False, "sent": False, "error": str(e)}
            print(f"[Aviso] Falha ao disparar e-mail: {e}")

    return jsonify({
        "success": True,
        "id": result["id"],
        "view_token": result["view_token"],
        "edit_token": result["edit_token"],
        "version": result["version"],
        "status_tecnico": result["status_tecnico"],
        "email_delivery": email_delivery,
        "to_email": to_email,
        "message": "Tudo certo! Recebemos suas informações."
    }), 201

@app.route("/api/edit/<token>", methods=["POST"])
def api_update_form(token):
    """Atualiza registro existente via edit_token com validação de versão e concorrência."""
    payload = request.get_json(silent=True) or {}
    sub = database.get_by_edit_token(token)
    if not sub:
        return jsonify({
            "success": False,
            "error": "Registro não encontrado para o token fornecido."
        }), 404

    is_draft = payload.get("is_draft", False)
    
    # Se não for rascunho, exige nome de quem preenche/altera
    if not is_draft:
        nome = (payload.get("nome_preenchedor") or sub.get("nome_preenchedor") or "").strip()
        if not nome:
            return jsonify({
                "success": False,
                "error": "Informe seu nome para enviar"
            }), 400

    expected_version = payload.get("expected_version")
    if expected_version is not None:
        try:
            expected_version = int(expected_version)
        except (ValueError, TypeError):
            expected_version = None

    try:
        updated = database.update_submission(
            token, 
            payload, 
            is_draft=is_draft, 
            expected_version=expected_version
        )
    except database.VersionConflictError as vce:
        return jsonify({
            "success": False,
            "error": str(vce)
        }), 409

    # Disparo de e-mail de atualização se configurado
    email_delivery = None
    to_email = (payload.get("email_preenchedor") or payload.get("email_cliente") or sub.get("email_preenchedor") or sub.get("email_cliente") or "").strip()
    if not is_draft and to_email:
        full_sub = database.get_by_view_token(updated["view_token"])
        if full_sub:
            try:
                base_url = request.host_url.rstrip("/")
                email_delivery = email_service.send_handoff_email(to_email, full_sub, base_url)
            except Exception as e:
                email_delivery = {"success": False, "sent": False, "error": str(e)}
                print(f"[Aviso] Falha ao disparar e-mail de atualização: {e}")

    return jsonify({
        "success": True,
        "id": updated["id"],
        "view_token": updated["view_token"],
        "edit_token": updated["edit_token"],
        "version": updated["version"],
        "status_tecnico": updated["status_tecnico"],
        "email_delivery": email_delivery,
        "to_email": to_email,
        "message": "Registro atualizado com sucesso"
    }), 200

@app.route("/api/resend-email/<token>", methods=["POST", "GET"])
def api_resend_email(token):
    """Permite testar e reenviar o e-mail de confirmação para um registro existente."""
    sub = database.get_by_any_token(token)
    if not sub:
        return jsonify({"success": False, "error": "Registro não encontrado"}), 404

    to_email = (sub.get("email_preenchedor") or sub.get("email_cliente") or "").strip()
    if not to_email:
        return jsonify({"success": False, "error": "Nenhum endereço de e-mail cadastrado neste registro"}), 400

    base_url = request.host_url.rstrip("/")
    result = email_service.send_handoff_email(to_email, sub, base_url)
    return jsonify({
        "success": result.get("success", False),
        "sent": result.get("sent", False),
        "simulated": result.get("simulated", False),
        "to_email": to_email,
        "reason": result.get("reason"),
        "error": result.get("error")
    }), (200 if result.get("sent") else 200)

@app.route("/preview-email/<token>")
def preview_email(token):
    """Permite visualizar a prévia visual real do e-mail HTML gerado para o cliente."""
    sub = database.get_by_any_token(token)
    if not sub:
        return render_template("error.html", title="Registro não encontrado", message="Não foi possível encontrar este registro para prévia de e-mail."), 404

    base_url = request.host_url.rstrip("/")
    html_content = email_service.get_handoff_email_html(sub, base_url)
    return html_content, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/api/configure-email", methods=["POST"])
def api_configure_email():
    """Salva credenciais de e-mail e testa a conexão imediatamente."""
    payload = request.get_json(silent=True) or {}
    smtp_user = (payload.get("smtp_user") or "").strip()
    smtp_password = (payload.get("smtp_password") or "").strip().replace(" ", "")
    smtp_server = (payload.get("smtp_server") or "smtp.gmail.com").strip()
    smtp_port = int(payload.get("smtp_port") or 587)
    token = payload.get("token")

    if not smtp_user or not smtp_password:
        return jsonify({"success": False, "error": "Informe o e-mail e a senha de aplicativo de 16 letras."}), 400

    test_res = email_service.test_smtp_credentials(smtp_user, smtp_password, smtp_server, smtp_port)
    if not test_res["success"]:
        return jsonify({
            "success": False,
            "error": f"Falha na conexão com o Gmail: {test_res.get('error')}. Certifique-se de usar a 'Senha de App' de 16 letras gerada no painel do Google."
        }), 400

    email_service.save_email_credentials(smtp_user, smtp_password, smtp_server, smtp_port)

    sent_now = False
    if token:
        sub = database.get_by_any_token(token)
        if sub:
            to_email = (sub.get("email_preenchedor") or sub.get("email_cliente") or smtp_user).strip()
            base_url = request.host_url.rstrip("/")
            send_res = email_service.send_handoff_email(to_email, sub, base_url)
            sent_now = send_res.get("sent", False)

    return jsonify({
        "success": True,
        "sent": sent_now,
        "message": "Conectado ao Gmail com sucesso!" + (" O e-mail de confirmação foi entregue!" if sent_now else "")
    }), 200

@app.route("/api/get/<token>", methods=["GET"])
def api_get_record(token):
    """Consulta os dados do registro em formato JSON isolado."""
    ip = request.remote_addr or "unknown"
    if is_rate_limited(ip):
        return jsonify({"success": False, "error": "Limite de tentativas excedido"}), 429
    if not is_safe_token(token):
        record_failed_lookup(ip)
        return jsonify({"success": False, "error": "Token inválido"}), 400

    sub_view = database.get_by_view_token(token)
    if sub_view:
        sanitized_view = dict(sub_view)
        sanitized_view.pop("edit_token", None)
        return jsonify({"success": True, "permission": "view", "data": sanitized_view}), 200

    sub_edit = database.get_by_edit_token(token)
    if sub_edit:
        return jsonify({"success": True, "permission": "edit", "data": sub_edit}), 200

    record_failed_lookup(ip)
    return jsonify({"success": False, "error": "Registro não encontrado"}), 404

@app.route("/pdf/<token>")
def download_pdf(token):
    """Gera e retorna o PDF preenchido a partir do view_token ou edit_token."""
    ip = request.remote_addr or "unknown"
    if is_rate_limited(ip):
        return render_template("error.html", title="Muitas tentativas", message="Limite de tentativas excedido. Aguarde 1 minuto."), 429
    if not is_safe_token(token):
        record_failed_lookup(ip)
        return render_template("error.html", title="Link inválido", message="O token informado é inválido."), 400

    sub = database.get_by_any_token(token)
    if not sub:
        record_failed_lookup(ip)
        return render_template(
            "error.html", 
            title="PDF não encontrado", 
            message="Não foi possível gerar o PDF para o token informado."
        ), 404

    pdf_bytes = pdf_generator.generate_handoff_pdf(sub)
    cliente_clean = re.sub(r'[^a-zA-Z0-9_-]', '_', sub.get("cliente_razao_social") or "Registro")
    filename = f"PJzen_Handoff_{cliente_clean}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
