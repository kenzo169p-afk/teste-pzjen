<?php
/**
 * PJzen Universal Entry Point para Hospedagens PHP
 */
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if (strpos($uri, '/api/') === 0) {
    require __DIR__ . '/api.php';
    exit;
}

if (preg_match('#^/(view|edit|documento)/([a-zA-Z0-9_\-]+)#', $uri, $matches)) {
    $mode = $matches[1];
    $token = $matches[2];
    $param = ($mode === 'documento') ? 'doc' : $mode;
    header("Location: /index.html?{$param}={$token}");
    exit;
}

// Serve a página index.html
if (file_exists(__DIR__ . '/index.html')) {
    include __DIR__ . '/index.html';
    exit;
}
