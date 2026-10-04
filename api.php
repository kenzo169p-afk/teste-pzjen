<?php
/**
 * PJzen Universal PHP API & Backend
 * Compatível com qualquer hospedagem PHP (Hostinger, cPanel, Locaweb, Apache, Nginx).
 * Funciona com PHP 7.4, 8.0, 8.1, 8.2, 8.3+.
 * Utiliza SQLite nativo (ou JSON fallback) com zero bibliotecas externas necessárias.
 */

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$dbFile = __DIR__ . '/handoff.db';
$uploadDir = __DIR__ . '/uploads';
if (!file_exists($uploadDir)) {
    @mkdir($uploadDir, 0755, true);
}

// Inicialização do Banco SQLite
function getDatabase() {
    global $dbFile;
    try {
        $pdo = new PDO("sqlite:" . $dbFile);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->exec("
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                view_token TEXT UNIQUE NOT NULL,
                edit_token TEXT UNIQUE NOT NULL,
                version INTEGER DEFAULT 1,
                status_tecnico TEXT DEFAULT 'rascunho',
                nome_preenchedor TEXT,
                email_preenchedor TEXT,
                data_venda TEXT,
                cliente_razao_social TEXT,
                cnpj TEXT,
                email_cliente TEXT,
                telefone_cliente TEXT,
                data_repasse TEXT,
                tipo_demanda TEXT,
                plano_contratado TEXT,
                faturamento_mensal_esperado TEXT,
                atividade_cnae_municipio TEXT,
                atividades_secundarias TEXT,
                tera_pro_labore TEXT,
                regime_tributario TEXT,
                tabela_apuracao_anexo TEXT,
                pontos_atencao_tecnicos TEXT,
                frentes_acionadas TEXT,
                demandas_acordadas TEXT,
                documentos_pendentes TEXT,
                anexos_documentos TEXT,
                prazo_combinado TEXT,
                responsavel_onboarding TEXT,
                responsavel_tecnico TEXT,
                status_repasse TEXT,
                proxima_acao_resp_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                submitted_at TEXT
            )
        ");
        return $pdo;
    } catch (Exception $e) {
        return null;
    }
}

function generateToken($length = 24) {
    return bin2hex(random_bytes($length / 2));
}

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$method = $_SERVER['REQUEST_METHOD'];

// Rota de Upload de Arquivos
if (strpos($uri, '/api/upload') !== false && $method === 'POST') {
    if (!isset($_FILES['file'])) {
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Nenhum arquivo enviado']);
        exit;
    }

    $file = $_FILES['file'];
    $dataPc = $_POST['data_pc'] ?? date('d/m/Y H:i:s');
    $ext = pathinfo($file['name'], PATHINFO_EXTENSION);
    $safeName = time() . '_' . preg_replace('/[^a-zA-Z0-9_\.-]/', '_', $file['name']);
    $dest = $uploadDir . '/' . $safeName;

    if (move_uploaded_file($file['tmp_name'], $dest)) {
        $tamKb = round($file['size'] / 1024, 1);
        $tipo = 'Documento';
        $mime = $file['type'] ?? '';
        if (strpos($mime, 'image/') === 0) $tipo = 'Imagem';
        else if (strpos($mime, 'video/') === 0) $tipo = 'Vídeo';
        else if (strpos($mime, 'pdf') !== false) $tipo = 'PDF';

        $baseUrl = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? "https" : "http") . "://$_SERVER[HTTP_HOST]";
        $url = $baseUrl . '/uploads/' . $safeName;

        echo json_encode([
            'success' => true,
            'url' => $url,
            'nome_original' => $file['name'],
            'tipo' => $tipo,
            'tamanho_formatado' => "{$tamKb} KB",
            'data_pc' => $dataPc,
            'storage' => 'Hospedagem Web'
        ]);
    } else {
        http_response_code(500);
        echo json_encode(['success' => false, 'error' => 'Falha ao salvar arquivo no servidor']);
    }
    exit;
}

// Rotas de Submissão, Rascunho e Edição
$pdo = getDatabase();

if (strpos($uri, '/api/submit') !== false || strpos($uri, '/api/draft') !== false || strpos($uri, '/api/edit') !== false) {
    $isDraft = (strpos($uri, '/api/draft') !== false);
    $input = json_decode(file_get_contents('php://input'), true) ?: $_POST;

    // Se é edição, pega token da URL
    $editToken = null;
    if (preg_match('#/api/edit/([^/]+)#', $uri, $m)) {
        $editToken = $m[1];
    }

    $nome = trim($input['nome_preenchedor'] ?? '');
    if (!$isDraft && empty($nome) && !$editToken) {
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Informe seu nome para enviar']);
        exit;
    }

    $now = date('Y-m-d H:i:s');
    $status = $isDraft ? 'rascunho' : 'enviado';

    if ($pdo) {
        if ($editToken) {
            // Atualização
            $stmt = $pdo->prepare("SELECT * FROM submissions WHERE edit_token = ?");
            $stmt->execute([$editToken]);
            $existing = $stmt->fetch(PDO::FETCH_ASSOC);

            if ($existing) {
                $version = ((int)$existing['version']) + 1;
                $update = $pdo->prepare("
                    UPDATE submissions SET
                        version = ?, status_tecnico = ?, nome_preenchedor = ?, email_preenchedor = ?, data_venda = ?,
                        cliente_razao_social = ?, cnpj = ?, email_cliente = ?, telefone_cliente = ?, data_repasse = ?,
                        tipo_demanda = ?, plano_contratado = ?, faturamento_mensal_esperado = ?, atividade_cnae_municipio = ?,
                        atividades_secundarias = ?, tera_pro_labore = ?, regime_tributario = ?, tabela_apuracao_anexo = ?,
                        pontos_atencao_tecnicos = ?, frentes_acionadas = ?, demandas_acordadas = ?, documentos_pendentes = ?,
                        anexos_documentos = ?, prazo_combinado = ?, responsavel_onboarding = ?, responsavel_tecnico = ?,
                        status_repasse = ?, proxima_acao_resp_data = ?, updated_at = ?
                    WHERE edit_token = ?
                ");
                $update->execute([
                    $version,
                    $status,
                    $input['nome_preenchedor'] ?? '',
                    $input['email_preenchedor'] ?? '',
                    $input['data_venda'] ?? '',
                    $input['cliente_razao_social'] ?? '',
                    $input['cnpj'] ?? '',
                    $input['email_cliente'] ?? '',
                    $input['telefone_cliente'] ?? '',
                    $input['data_repasse'] ?? '',
                    json_encode($input['tipo_demanda'] ?? []),
                    json_encode($input['plano_contratado'] ?? []),
                    json_encode($input['faturamento_mensal_esperado'] ?? []),
                    $input['atividade_cnae_municipio'] ?? '',
                    $input['atividades_secundarias'] ?? '',
                    json_encode($input['tera_pro_labore'] ?? []),
                    json_encode($input['regime_tributario'] ?? []),
                    json_encode($input['tabela_apuracao_anexo'] ?? []),
                    $input['pontos_atencao_tecnicos'] ?? '',
                    json_encode($input['frentes_acionadas'] ?? []),
                    $input['demandas_acordadas'] ?? '',
                    $input['documentos_pendentes'] ?? '',
                    json_encode($input['anexos_documentos'] ?? []),
                    $input['prazo_combinado'] ?? '',
                    $input['responsavel_onboarding'] ?? '',
                    $input['responsavel_tecnico'] ?? '',
                    json_encode($input['status_repasse'] ?? []),
                    $input['proxima_acao_resp_data'] ?? '',
                    $now,
                    $editToken
                ]);

                echo json_encode([
                    'success' => true,
                    'view_token' => $existing['view_token'],
                    'edit_token' => $editToken,
                    'version' => $version,
                    'status_tecnico' => $status,
                    'message' => 'Registro atualizado com sucesso'
                ]);
                exit;
            }
        }

        // Nova Inserção
        $newViewToken = generateToken(24);
        $newEditToken = generateToken(24);
        $stmt = $pdo->prepare("
            INSERT INTO submissions (
                view_token, edit_token, version, status_tecnico,
                nome_preenchedor, email_preenchedor, data_venda, cliente_razao_social, cnpj,
                email_cliente, telefone_cliente, data_repasse, tipo_demanda, plano_contratado,
                faturamento_mensal_esperado, atividade_cnae_municipio, atividades_secundarias,
                tera_pro_labore, regime_tributario, tabela_apuracao_anexo, pontos_atencao_tecnicos,
                frentes_acionadas, demandas_acordadas, documentos_pendentes, anexos_documentos,
                prazo_combinado, responsavel_onboarding, responsavel_tecnico, status_repasse,
                proxima_acao_resp_data, created_at, updated_at, submitted_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->execute([
            $newViewToken,
            $newEditToken,
            $status,
            $input['nome_preenchedor'] ?? '',
            $input['email_preenchedor'] ?? '',
            $input['data_venda'] ?? '',
            $input['cliente_razao_social'] ?? '',
            $input['cnpj'] ?? '',
            $input['email_cliente'] ?? '',
            $input['telefone_cliente'] ?? '',
            $input['data_repasse'] ?? '',
            json_encode($input['tipo_demanda'] ?? []),
            json_encode($input['plano_contratado'] ?? []),
            json_encode($input['faturamento_mensal_esperado'] ?? []),
            $input['atividade_cnae_municipio'] ?? '',
            $input['atividades_secundarias'] ?? '',
            json_encode($input['tera_pro_labore'] ?? []),
            json_encode($input['regime_tributario'] ?? []),
            json_encode($input['tabela_apuracao_anexo'] ?? []),
            $input['pontos_atencao_tecnicos'] ?? '',
            json_encode($input['frentes_acionadas'] ?? []),
            $input['demandas_acordadas'] ?? '',
            $input['documentos_pendentes'] ?? '',
            json_encode($input['anexos_documentos'] ?? []),
            $input['prazo_combinado'] ?? '',
            $input['responsavel_onboarding'] ?? '',
            $input['responsavel_tecnico'] ?? '',
            json_encode($input['status_repasse'] ?? []),
            $input['proxima_acao_resp_data'] ?? '',
            $now,
            $now,
            $isDraft ? null : $now
        ]);

        http_response_code(201);
        echo json_encode([
            'success' => true,
            'view_token' => $newViewToken,
            'edit_token' => $newEditToken,
            'version' => 1,
            'status_tecnico' => $status,
            'message' => 'Formulário gravado com sucesso'
        ]);
        exit;
    }
}

// Rota de Consulta de Dados
if (preg_match('#/api/get/([^/]+)#', $uri, $m)) {
    $token = $m[1];
    if ($pdo) {
        $stmt = $pdo->prepare("SELECT * FROM submissions WHERE view_token = ? OR edit_token = ? LIMIT 1");
        $stmt->execute([$token, $token]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        if ($row) {
            // Decodifica JSONs
            foreach (['tipo_demanda', 'plano_contratado', 'faturamento_mensal_esperado', 'tera_pro_labore', 'regime_tributario', 'tabela_apuracao_anexo', 'frentes_acionadas', 'status_repasse', 'anexos_documentos'] as $col) {
                $row[$col] = json_decode($row[$col] ?? '[]', true) ?: [];
            }
            echo json_encode(['success' => true, 'data' => $row]);
            exit;
        }
    }
    http_response_code(404);
    echo json_encode(['success' => false, 'error' => 'Registro não encontrado']);
    exit;
}

// Se nenhuma rota de API bateu, serve a página index.html
if (file_exists(__DIR__ . '/index.html')) {
    include __DIR__ . '/index.html';
    exit;
}
