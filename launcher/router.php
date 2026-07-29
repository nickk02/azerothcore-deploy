<?php
/*
 * Router for the launcher news server.
 *
 * Without this, PHP's built-in server falls back to index.html for ANY
 * unmatched path, so /update/Scan.dll would return HTTP 200 with HTML in it
 * and the launcher could overwrite a real client file with a web page.
 * Only the news page and background art are served; everything else 404s.
 */

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// Log every hit so we can see exactly what the launcher asks for.
@file_put_contents(
    __DIR__ . '/requests.log',
    sprintf(
        "%s  %-15s  %-6s %-40s  UA=%s\n",
        date('Y-m-d H:i:s'),
        $_SERVER['REMOTE_ADDR'] ?? '?',
        $_SERVER['REQUEST_METHOD'] ?? '?',
        $uri,
        $_SERVER['HTTP_USER_AGENT'] ?? '-'
    ),
    FILE_APPEND | LOCK_EX
);

// Root, or a locale variant like /en/ or /en-us/ (the launcher uses these).
$isNewsPage = ($uri === '/' || $uri === '/index.html')
    || preg_match('#^/[a-z]{2}(-[a-z]{2})?/?$#i', $uri);

if ($isNewsPage) {
    $page = __DIR__ . '/index.html';
    if (is_file($page)) {
        header('Content-Type: text/html; charset=utf-8');
        header('Cache-Control: no-cache');
        readfile($page);
        return true;
    }
}

// Background art: serve our image for whatever filename it asks for,
// so we don't have to guess Blizzard's original naming.
if (preg_match('#^/background/#i', $uri)) {
    $art = __DIR__ . '/background.jpg';
    if (is_file($art)) {
        header('Content-Type: image/jpeg');
        header('Content-Length: ' . filesize($art));
        readfile($art);
        return true;
    }
}

// Everything else, especially /update/*, is a hard 404 so the launcher
// never replaces a local client file with something from this server.
http_response_code(404);
header('Content-Type: text/plain');
echo "404 Not Found\n";
return true;
