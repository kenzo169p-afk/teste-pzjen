import sqlite3
import json
import secrets
import re
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

DB_FILE = Path(__file__).parent / "handoff.db"

CHECKBOX_FIELDS = {
    "tipo_demanda",
    "plano_contratado",
    "faturamento_mensal_esperado",
    "tera_pro_labore",
    "simples_nacional",
    "regime_tributario",
    "tabela_apuracao_anexo",
    "frentes_acionadas",
    "status_repasse"
}

JSON_FIELDS = CHECKBOX_FIELDS | {"anexos_documentos"}

ALL_DATA_FIELDS = [
    "nome_preenchedor",
    "email_preenchedor",
    "telefone_preenchedor",
    "data_venda",
    "cliente_razao_social",
    "cnpj",
    "email_cliente",
    "telefone_cliente",
    "responsavel_comercial",
    "data_repasse",
    "tipo_demanda",
    "plano_contratado",
    "faturamento_mensal_esperado",
    "atividade_cnae_municipio",
    "atividades_secundarias",
    "tera_pro_labore",
    "simples_nacional",
    "regime_tributario",
    "tabela_apuracao_anexo",
    "regime_validado_por",
    "pontos_atencao_tecnicos",
    "frentes_acionadas",
    "demandas_acordadas",
    "documentos_pendentes",
    "prazo_combinado",
    "responsavel_onboarding",
    "responsavel_tecnico",
    "status_repasse",
    "proxima_acao_resp_data",
    "anexos_documentos"
]

@contextmanager
def get_db(db_path=None):
    path = db_path or DB_FILE
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()

def init_db(db_path=None):
    with get_db(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                view_token TEXT UNIQUE NOT NULL,
                edit_token TEXT UNIQUE NOT NULL,
                nome_preenchedor TEXT,
                email_preenchedor TEXT,
                telefone_preenchedor TEXT,
                data_venda TEXT,
                cliente_razao_social TEXT,
                cnpj TEXT,
                email_cliente TEXT,
                telefone_cliente TEXT,
                responsavel_comercial TEXT,
                data_repasse TEXT,
                tipo_demanda TEXT,
                plano_contratado TEXT,
                faturamento_mensal_esperado TEXT,
                atividade_cnae_municipio TEXT,
                atividades_secundarias TEXT,
                tera_pro_labore TEXT,
                simples_nacional TEXT,
                regime_tributario TEXT,
                tabela_apuracao_anexo TEXT,
                regime_validado_por TEXT,
                pontos_atencao_tecnicos TEXT,
                frentes_acionadas TEXT,
                demandas_acordadas TEXT,
                documentos_pendentes TEXT,
                prazo_combinado TEXT,
                responsavel_onboarding TEXT,
                responsavel_tecnico TEXT,
                status_repasse TEXT,
                proxima_acao_resp_data TEXT,
                anexos_documentos TEXT NOT NULL DEFAULT '[]',
                status_tecnico TEXT NOT NULL DEFAULT 'rascunho',
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                submitted_at TEXT,
                history TEXT NOT NULL DEFAULT '[]'
            );
        """)
        # Migração automática segura de colunas caso o banco já existisse
        for col, col_type in [
            ("email_preenchedor", "TEXT"),
            ("telefone_preenchedor", "TEXT"),
            ("email_cliente", "TEXT"),
            ("telefone_cliente", "TEXT"),
            ("atividades_secundarias", "TEXT"),
            ("regime_tributario", "TEXT"),
            ("data_venda", "TEXT"),
            ("anexos_documentos", "TEXT NOT NULL DEFAULT '[]'")
        ]:
            try:
                conn.execute(f"ALTER TABLE submissions ADD COLUMN {col} {col_type};")
            except Exception:
                pass
        conn.commit()

def _sanitize_data(data):
    """Normalize input data: ensure json strings for lists/checkboxes and trimmed/empty string for texts."""
    # Sincroniza regime_tributario e simples_nacional
    if not data.get("regime_tributario") and data.get("simples_nacional"):
        data["regime_tributario"] = data["simples_nacional"]
    elif not data.get("simples_nacional") and data.get("regime_tributario"):
        data["simples_nacional"] = data["regime_tributario"]

    sanitized = {}
    for field in ALL_DATA_FIELDS:
        val = data.get(field)
        if field in JSON_FIELDS:
            if isinstance(val, list):
                sanitized[field] = json.dumps(val, ensure_ascii=False)
            elif isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        sanitized[field] = json.dumps(parsed, ensure_ascii=False)
                    else:
                        sanitized[field] = json.dumps([val.strip()] if val.strip() else [], ensure_ascii=False)
                except Exception:
                    sanitized[field] = json.dumps([val.strip()] if val.strip() else [], ensure_ascii=False)
            else:
                sanitized[field] = json.dumps([], ensure_ascii=False)
        else:
            if val is None:
                sanitized[field] = ""
            else:
                sanitized[field] = str(val).strip()
    return sanitized

def _row_to_dict(row):
    if not row:
        return None
    d = dict(row)
    for field in JSON_FIELDS:
        val = d.get(field)
        if val:
            try:
                d[field] = json.loads(val)
            except Exception:
                d[field] = []
        else:
            d[field] = []
    if d.get("history"):
        try:
            d["history"] = json.loads(d["history"])
        except Exception:
            d["history"] = []
    else:
        d["history"] = []

    # Sincroniza regime_tributario e simples_nacional para leituras
    if not d.get("regime_tributario") and d.get("simples_nacional"):
        d["regime_tributario"] = d["simples_nacional"]
    elif not d.get("simples_nacional") and d.get("regime_tributario"):
        d["simples_nacional"] = d["regime_tributario"]

    return d

def create_submission(data, is_draft=False, db_path=None):
    now = datetime.now().isoformat()
    view_token = secrets.token_urlsafe(24)
    edit_token = secrets.token_urlsafe(24)
    
    sanitized = _sanitize_data(data)
    status_tecnico = "rascunho" if is_draft else "enviado"
    submitted_at = None if is_draft else now
    
    action_name = "Criação de rascunho" if is_draft else "Envio inicial do formulário"
    history = [{
        "timestamp": now,
        "action": action_name,
        "nome": sanitized.get("nome_preenchedor", "")
    }]

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cols = ["view_token", "edit_token", "status_tecnico", "version", "created_at", "updated_at", "submitted_at", "history"] + ALL_DATA_FIELDS
        placeholders = ", ".join(["?"] * len(cols))
        
        values = [
            view_token,
            edit_token,
            status_tecnico,
            1,
            now,
            now,
            submitted_at,
            json.dumps(history, ensure_ascii=False)
        ] + [sanitized[field] for field in ALL_DATA_FIELDS]
        
        cursor.execute(f"INSERT INTO submissions ({', '.join(cols)}) VALUES ({placeholders})", values)
        conn.commit()
        sub_id = cursor.lastrowid

    return {
        "id": sub_id,
        "view_token": view_token,
        "edit_token": edit_token,
        "status_tecnico": status_tecnico,
        "version": 1,
        "submitted_at": submitted_at
    }

class VersionConflictError(Exception):
    """Raised when optimistic lock detects conflicting version."""
    pass

def update_submission(edit_token, data, is_draft=False, expected_version=None, db_path=None):
    now = datetime.now().isoformat()
    existing = get_by_edit_token(edit_token, db_path=db_path)
    if not existing:
        return None

    current_version = existing["version"]
    if expected_version is not None and expected_version != current_version:
        raise VersionConflictError(
            f"Conflito de versão: o registro foi atualizado (versão atual: {current_version}, versão enviada: {expected_version})."
        )

    # Only update provided or sanitized fields; preserve existing values if field not in data
    sanitized = {}
    for field in ALL_DATA_FIELDS:
        if field in data:
            val = data[field]
            if field in JSON_FIELDS:
                if isinstance(val, list):
                    sanitized[field] = json.dumps(val, ensure_ascii=False)
                elif isinstance(val, str):
                    try:
                        p = json.loads(val)
                        if isinstance(p, list):
                            sanitized[field] = json.dumps(p, ensure_ascii=False)
                        else:
                            sanitized[field] = json.dumps([val.strip()] if val.strip() else [], ensure_ascii=False)
                    except Exception:
                        sanitized[field] = json.dumps([val.strip()] if val.strip() else [], ensure_ascii=False)
                else:
                    sanitized[field] = json.dumps([], ensure_ascii=False)
            else:
                sanitized[field] = "" if val is None else str(val).strip()
        else:
            # Preserve existing
            curr_val = existing.get(field)
            if field in JSON_FIELDS:
                sanitized[field] = json.dumps(curr_val if isinstance(curr_val, list) else [], ensure_ascii=False)
            else:
                sanitized[field] = "" if curr_val is None else str(curr_val)

    # Determine status_tecnico
    new_status = existing["status_tecnico"]
    new_submitted_at = existing["submitted_at"]
    if not is_draft and existing["status_tecnico"] == "rascunho":
        new_status = "enviado"
        new_submitted_at = now
    elif not is_draft:
        new_status = "enviado"

    new_version = current_version + 1
    
    # Append to history
    history = existing.get("history", [])
    action_desc = "Atualização de rascunho" if is_draft else ("Envio do formulário" if existing["status_tecnico"] == "rascunho" else "Complementação de informações")
    history.append({
        "timestamp": now,
        "action": action_desc,
        "nome": sanitized.get("nome_preenchedor") or existing.get("nome_preenchedor", "")
    })

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        set_clauses = [f"{field} = ?" for field in ALL_DATA_FIELDS]
        set_clauses.extend(["status_tecnico = ?", "version = ?", "updated_at = ?", "submitted_at = ?", "history = ?"])
        
        values = [sanitized[field] for field in ALL_DATA_FIELDS] + [
            new_status,
            new_version,
            now,
            new_submitted_at,
            json.dumps(history, ensure_ascii=False),
            edit_token,
            current_version
        ]
        
        cursor.execute(f"""
            UPDATE submissions 
            SET {', '.join(set_clauses)}
            WHERE edit_token = ? AND version = ?
        """, values)
        
        if cursor.rowcount == 0:
            raise VersionConflictError("Não foi possível atualizar o registro devido a concorrência.")
        conn.commit()

    return {
        "id": existing["id"],
        "view_token": existing["view_token"],
        "edit_token": edit_token,
        "status_tecnico": new_status,
        "version": new_version,
        "submitted_at": new_submitted_at
    }

TOKEN_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]{8,64}$')

def _is_safe_token(token):
    return bool(token and isinstance(token, str) and TOKEN_PATTERN.match(token))

def get_by_view_token(view_token, db_path=None):
    if not _is_safe_token(view_token):
        return None
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM submissions WHERE view_token = ?", (view_token,))
        row = cursor.fetchone()
        return _row_to_dict(row)

def get_by_edit_token(edit_token, db_path=None):
    if not _is_safe_token(edit_token):
        return None
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM submissions WHERE edit_token = ?", (edit_token,))
        row = cursor.fetchone()
        return _row_to_dict(row)

def get_by_any_token(token, db_path=None):
    """Finds submission by either edit_token or view_token."""
    if not _is_safe_token(token):
        return None
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM submissions WHERE view_token = ? OR edit_token = ?", (token, token))
        row = cursor.fetchone()
        return _row_to_dict(row)
