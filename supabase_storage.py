import os
import re
import uuid
from pathlib import Path
import requests

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

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
                    if key not in os.environ:
                        os.environ[key] = val

_load_env()

def get_supabase_config():
    _load_env()
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "").strip()
    bucket = os.environ.get("SUPABASE_BUCKET", "pjzen-docs").strip()
    return url, key, bucket

def upload_to_storage(file_bytes, original_filename, content_type="application/octet-stream"):
    """
    Realiza o upload do arquivo para o Supabase Storage.
    Caso as credenciais não estejam configuradas, utiliza fallback local automático.
    """
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', original_filename)
    unique_filename = f"{uuid.uuid4().hex[:8]}_{clean_name}"
    
    supabase_url, supabase_key, bucket = get_supabase_config()

    if supabase_url and supabase_key:
        try:
            endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{unique_filename}"
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": content_type
            }
            resp = requests.post(endpoint, data=file_bytes, headers=headers, timeout=20)
            if resp.status_code in (200, 201):
                public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{unique_filename}"
                return {
                    "success": True,
                    "storage": "supabase",
                    "filename": unique_filename,
                    "url": public_url
                }
            else:
                print(f"[Supabase Storage Error] Status {resp.status_code}: {resp.text}. Ativando fallback local.")
        except Exception as e:
            print(f"[Supabase Storage Exception] {e}. Ativando fallback local.")

    # Fallback local
    local_path = UPLOAD_DIR / unique_filename
    with open(local_path, "wb") as f:
        f.write(file_bytes)

    return {
        "success": True,
        "storage": "local",
        "filename": unique_filename,
        "url": f"/uploads/{unique_filename}"
    }
