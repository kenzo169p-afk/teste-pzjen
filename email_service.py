import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

def _load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    os.environ[key] = val

_load_env()

def send_handoff_email(to_email, submission, base_url):
    """
    Envia e-mail formatado em HTML com as informações de handoff e links do documento.
    Verifica credenciais e conexões reais via SMTP.
    """
    if not to_email or "@" not in to_email:
        return {"success": False, "sent": False, "reason": "E-mail inválido ou ausente"}

    _load_env()
    smtp_server = (os.environ.get("SMTP_SERVER") or os.environ.get("SMTP_HOST") or "").strip()
    smtp_port_str = os.environ.get("SMTP_PORT", "587").strip()
    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        smtp_port = 587
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_password = (os.environ.get("SMTP_PASSWORD") or os.environ.get("SMTP_PASS") or "").strip()
    smtp_sender = (os.environ.get("SMTP_SENDER") or smtp_user or "nao-responda@pjzen.com.br").strip()
    use_tls = os.environ.get("SMTP_USE_TLS", "True").lower() in ("true", "1")

def get_handoff_email_html(submission, base_url):
    """Gera o HTML visual do e-mail com a identidade visual PJzen e links."""
    nome = submission.get("nome_preenchedor") or "Cliente"
    cliente = submission.get("cliente_razao_social") or "Novo Cliente PJzen"
    view_token = submission.get("view_token", "")
    anexos = submission.get("anexos_documentos", [])
    if isinstance(anexos, str):
        import json
        try:
            anexos = json.loads(anexos)
        except Exception:
            anexos = []

    view_link = f"{base_url}/view/{view_token}"
    doc_link = f"{base_url}/documento/{view_token}"

    anexos_html = ""
    if anexos:
        anexos_html = "<h4 style='color: #003383; margin-top: 20px;'>Documentos e Mídias Anexados:</h4><ul style='padding-left: 20px;'>"
        for a in anexos:
            data_pc = a.get("data_pc") or a.get("created_at_pc") or "Data do PC registrada"
            anexos_html += f"<li style='margin-bottom: 6px;'><strong>{a.get('nome_original', 'Arquivo')}</strong> ({a.get('tipo', 'arquivo')}) — <span style='color: #64748B;'>Anexado em: {data_pc}</span></li>"
        anexos_html += "</ul>"
    else:
        anexos_html = "<p style='color: #64748B;'>Nenhum arquivo anexado no momento do envio.</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Confirmação de Handoff PJzen</title>
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #F5F3F1; margin: 0; padding: 24px; color: #1C1B1F;">
      <table align="center" width="100%" style="max-width: 600px; background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0; overflow: hidden; border-spacing: 0;">
        <tr>
          <td style="background-color: #FFD100; padding: 24px; border-bottom: 4px solid #003383;">
            <h1 style="margin: 0; font-size: 22px; color: #1C1B1F; font-weight: bold;">PJzen | Sua vida PJ mais zen</h1>
            <p style="margin: 4px 0 0 0; font-size: 14px; color: #1C1B1F;">Handoff Comercial → Onboarding & Operação</p>
          </td>
        </tr>
        <tr>
          <td style="padding: 28px;">
            <h2 style="color: #003383; margin-top: 0; font-size: 18px;">Tudo certo! Recebemos suas informações.</h2>
            <p style="font-size: 15px; line-height: 1.5; color: #2C222D;">
              Olá, <strong>{nome}</strong>! O registro de handoff para <strong>{cliente}</strong> foi gravado com sucesso.
            </p>
            
            <div style="background-color: #F2EFE9; padding: 18px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #FFD100;">
              <p style="margin: 0 0 8px 0; font-size: 14px;"><strong>Links de Acesso ao seu Registro:</strong></p>
              <p style="margin: 6px 0;">👉 <a href="{view_link}" style="color: #0047B9; font-weight: bold; text-decoration: underline;">Visualizar Handoff Completo (Somente Leitura)</a></p>
              <p style="margin: 6px 0;">👉 <a href="{doc_link}" style="color: #0047B9; font-weight: bold; text-decoration: underline;">Acessar Documento de Comprovante e Anexos</a></p>
            </div>

            {anexos_html}

            <p style="font-size: 13px; color: #64748B; margin-top: 24px; border-top: 1px solid #E2E8F0; padding-top: 16px;">
              Regra de passagem: o onboarding confirma o recebimento e devolve dúvidas ao comercial antes de iniciar a execução.<br>
              Este é um e-mail automático gerado pelo sistema PJzen.
            </p>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

def test_smtp_credentials(smtp_user, smtp_password, smtp_server="smtp.gmail.com", smtp_port=587):
    """Testa se as credenciais de SMTP funcionam."""
    try:
        if int(smtp_port) == 465:
            server = smtplib.SMTP_SSL(smtp_server, int(smtp_port), timeout=12)
        else:
            server = smtplib.SMTP(smtp_server, int(smtp_port), timeout=12)
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.quit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def save_email_credentials(smtp_user, smtp_password, smtp_server="smtp.gmail.com", smtp_port=587, smtp_sender=None):
    """Persiste credenciais no arquivo .env e recarrega em memória."""
    env_file = Path(__file__).parent / ".env"
    sender = smtp_sender or smtp_user
    lines = [
        "# PJzen | Configurações de Ambiente",
        f"SMTP_SERVER={smtp_server}",
        f"SMTP_PORT={smtp_port}",
        f"SMTP_USER={smtp_user}",
        f"SMTP_PASSWORD={smtp_password}",
        f"SMTP_SENDER={sender}",
        "SMTP_USE_TLS=True\n"
    ]
    with open(env_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    _load_env()
    return True

def send_handoff_email(to_email, submission, base_url):
    """
    Envia e-mail formatado em HTML com as informações de handoff e links do documento.
    Verifica credenciais e conexões reais via SMTP.
    """
    if not to_email or "@" not in to_email:
        return {"success": False, "sent": False, "reason": "E-mail inválido ou ausente"}

    _load_env()
    smtp_server = (os.environ.get("SMTP_SERVER") or os.environ.get("SMTP_HOST") or "").strip()
    smtp_port_str = os.environ.get("SMTP_PORT", "587").strip()
    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        smtp_port = 587
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_password = (os.environ.get("SMTP_PASSWORD") or os.environ.get("SMTP_PASS") or "").strip()
    smtp_sender = (os.environ.get("SMTP_SENDER") or smtp_user or "nao-responda@pjzen.com.br").strip()
    use_tls = os.environ.get("SMTP_USE_TLS", "True").lower() in ("true", "1")

    cliente = submission.get("cliente_razao_social") or "Novo Cliente PJzen"
    view_token = submission.get("view_token", "")
    view_link = f"{base_url}/view/{view_token}"
    doc_link = f"{base_url}/documento/{view_token}"
    html_content = get_handoff_email_html(submission, base_url)

    if not smtp_server or not smtp_user or not smtp_password:
        print("="*60)
        print(f"[SIMULAÇÃO / AVISO DE E-MAIL] Para: {to_email}")
        print(f"Assunto: PJzen | Handoff Registrado - {cliente}")
        print(f"Link do Handoff: {view_link}")
        print(f"Link do Documento de Anexos: {doc_link}")
        print(f"Aviso: Servidor SMTP não configurado com senha no arquivo .env.")
        print("="*60)
        return {
            "success": False,
            "sent": False,
            "simulated": True,
            "reason": "Credenciais de e-mail (SMTP_USER ou SMTP_PASSWORD) não foram configuradas no arquivo .env"
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"PJzen | Handoff Registrado com Sucesso - {cliente}"
        msg["From"] = smtp_sender
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=20)
            if use_tls:
                server.starttls()

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_sender, [to_email], msg.as_string())
        server.quit()
        print(f"[Sucesso SMTP] E-mail entregue com sucesso para {to_email}!")
        return {"success": True, "sent": True, "simulated": False}
    except Exception as e:
        err_msg = str(e)
        print(f"[Erro ao disparar e-mail SMTP para {to_email}] {err_msg}")
        return {"success": False, "sent": False, "error": err_msg}
