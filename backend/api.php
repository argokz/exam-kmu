<?php
header('Content-Type: application/json; charset=utf-8');

function loadEnv($path) {
    if (!is_file($path)) return;
    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || strpos($line, '#') === 0) continue;
        if (strpos($line, '=') !== false) {
            list($key, $value) = explode('=', $line, 2);
            $key = trim($key);
            $value = trim($value, " \t\"'");
            if ($key !== '') putenv("$key=$value");
        }
    }
}

$dir = __DIR__;
loadEnv($dir . '/.env');

$token = getenv('API_TOKEN');
if ($token !== false && $token !== '') {
    $provided = isset($_GET['token']) ? $_GET['token'] : (isset($_SERVER['HTTP_X_TOKEN']) ? $_SERVER['HTTP_X_TOKEN'] : '');
    if ($provided !== $token) {
        http_response_code(403);
        echo json_encode(['error' => 'Forbidden']);
        exit;
    }
}

$api_key = getenv('OPENAI_API_KEY');
if ($api_key === false || $api_key === '') {
    http_response_code(500);
    echo json_encode(['error' => 'API key not configured']);
    exit;
}

echo json_encode(['api_key' => $api_key]);
