/**
 * PJzen Universal Node.js Server
 * Zero dependências externas necessárias (roda com Node.js puro sem npm install).
 * Compatível com Render, Railway, Fly.io, Heroku, VPS e Docker.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = process.env.PORT || 3000;
const DATA_FILE = path.join(__dirname, 'handoff_node.json');

// Carrega ou inicializa banco de dados JSON local
function loadData() {
  try {
    if (fs.existsSync(DATA_FILE)) {
      return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
    }
  } catch (e) {}
  return {};
}

function saveData(data) {
  try {
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), 'utf8');
  } catch (e) {}
}

function isSafeToken(token) {
  return typeof token === 'string' && /^[a-zA-Z0-9_\-]{8,64}$/.test(token);
}

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.pdf': 'application/pdf',
  '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Cabeçalhos de Defesa e Segurança Contra Vazamento de Dados
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    return res.end();
  }

  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  const pathname = parsedUrl.pathname;

  // 0. API: /api/log-acesso (Entrada e Saída)
  if (pathname === '/api/log-acesso' && req.method === 'POST') {
    const host = (req.headers.host || '').toLowerCase();
    const isLocalhost = (
      host.includes('localhost') ||
      host.includes('127.0.0.1') ||
      host.endsWith('.local')
    );

    if (isLocalhost) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({
        success: true,
        ignored: true,
        reason: 'Ambiente localhost ignorado. Logs no Supabase so sao gravados em producao/Hostinger.'
      }));
    }

    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, logged: true }));
    });
    return;
  }

  // 1. API: /api/submit ou /api/draft ou /api/edit
  if ((pathname === '/api/submit' || pathname === '/api/draft' || pathname.startsWith('/api/edit')) && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const payload = JSON.parse(body || '{}');
        const isDraft = (pathname === '/api/draft');
        const nome = (payload.nome_preenchedor || '').trim();

        if (!isDraft && !nome && !pathname.startsWith('/api/edit')) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify({ success: false, error: 'Informe seu nome para enviar' }));
        }

        const data = loadData();
        let editToken = '';
        let viewToken = '';

        if (pathname.startsWith('/api/edit/')) {
          editToken = pathname.replace('/api/edit/', '');
          if (!isSafeToken(editToken)) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            return res.end(JSON.stringify({ success: false, error: 'Token inválido' }));
          }
          const existing = data[editToken];
          if (existing) {
            viewToken = existing.view_token;
            const updated = {
              ...existing,
              ...payload,
              version: (existing.version || 1) + 1,
              status_tecnico: isDraft ? 'rascunho' : 'enviado',
              updated_at: new Date().toISOString()
            };
            data[editToken] = updated;
            data[viewToken] = updated;
            saveData(data);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            return res.end(JSON.stringify({
              success: true,
              edit_token: editToken,
              view_token: viewToken,
              version: updated.version,
              status_tecnico: updated.status_tecnico
            }));
          }
        }

        // Nova submissão
        editToken = 'edit_' + crypto.randomBytes(12).toString('hex');
        viewToken = 'view_' + crypto.randomBytes(12).toString('hex');
        const now = new Date().toISOString();

        const record = {
          ...payload,
          edit_token: editToken,
          view_token: viewToken,
          version: 1,
          status_tecnico: isDraft ? 'rascunho' : 'enviado',
          created_at: now,
          updated_at: now,
          submitted_at: isDraft ? null : now
        };

        data[editToken] = record;
        data[viewToken] = record;
        saveData(data);

        res.writeHead(201, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({
          success: true,
          edit_token: editToken,
          view_token: viewToken,
          version: 1,
          status_tecnico: record.status_tecnico
        }));
      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ success: false, error: 'Erro ao processar dados' }));
      }
    });
    return;
  }

  // 2. API: /api/get/:token
  if (pathname.startsWith('/api/get/') && req.method === 'GET') {
    const token = pathname.replace('/api/get/', '');
    if (!isSafeToken(token)) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ success: false, error: 'Token inválido' }));
    }
    const data = loadData();
    const record = data[token];
    if (record) {
      const sanitized = { ...record };
      if (token === record.view_token || !token.startsWith('edit_')) {
        delete sanitized.edit_token;
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ success: true, data: sanitized }));
    }
    res.writeHead(404, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ success: false, error: 'Registro não encontrado' }));
  }

  // 3. Rotas amigáveis (/view/..., /edit/..., /documento/...)
  if (pathname.startsWith('/view/')) {
    const token = pathname.replace('/view/', '');
    res.writeHead(302, { 'Location': `/?view=${token}` });
    return res.end();
  }
  if (pathname.startsWith('/edit/')) {
    const token = pathname.replace('/edit/', '');
    res.writeHead(302, { 'Location': `/?edit=${token}` });
    return res.end();
  }
  if (pathname.startsWith('/documento/')) {
    const token = pathname.replace('/documento/', '');
    res.writeHead(302, { 'Location': `/?doc=${token}` });
    return res.end();
  }

  // 4. Arquivos Estáticos com Defesa Ativa Contra Vazamento de Dados
  const cleanPath = path.posix.normalize(pathname).replace(/^(\.\.[\/\\])+/, '');
  const blockedExtensions = ['.env', '.db', '.sqlite', '.sqlite3', '.sql', '.log', '.json', '.bat', '.py', '.md', '.sh', '.bak'];
  const ext = path.extname(cleanPath).toLowerCase();

  // Bloqueio de arquivos confidenciais e scripts
  if (
    blockedExtensions.includes(ext) ||
    cleanPath.includes('.env') ||
    (cleanPath.startsWith('/uploads/') && !['.pdf', '.png', '.jpg', '.jpeg', '.webp'].includes(ext))
  ) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    return res.end('403 Proibido: Acesso negado a arquivo protegido.');
  }

  // Prevenção contra Directory Traversal
  let safePath = path.resolve(__dirname, '.' + cleanPath);
  if (!safePath.startsWith(path.resolve(__dirname))) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    return res.end('403 Proibido');
  }

  if (cleanPath === '/' || cleanPath === '') {
    safePath = path.join(__dirname, 'index.html');
  }

  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(safePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') {
        // Fallback para index.html (SPA)
        fs.readFile(path.join(__dirname, 'index.html'), (err2, html) => {
          if (err2) {
            res.writeHead(404);
            return res.end('Página não encontrada');
          }
          res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
          res.end(html);
        });
      } else {
        res.writeHead(500);
        res.end(`Erro no servidor: ${err.code}`);
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

server.listen(PORT, () => {
  console.log(`[PJzen Universal Node Server] Rodando na porta ${PORT} em http://localhost:${PORT}`);
});
