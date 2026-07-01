param(
    [string]$Mode = "dev"
)

$modelsDir = Join-Path $PSScriptRoot "..\models_cache"

if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
}

if ($Mode -eq "prod") {
    $url = "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
    $output = Join-Path $modelsDir "Llama-3.1-8B-Instruct-Q4_K_M.gguf"
    Write-Host "Downloading Llama 3.1 8B (Q4_K_M) ~4.9GB ..."
} else {
    $url = "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
    $output = Join-Path $modelsDir "Phi-3-mini-4k-instruct-q4.gguf"
    Write-Host "Downloading Phi-3-mini-4k-instruct (Q4) ~2.2GB ..."
}

try {
    Invoke-WebRequest -Uri $url -OutFile $output -UseBasicParsing
    Write-Host "Done! Model saved to: $output"
} catch {
    Write-Host "Download failed: $_"
    Write-Host "You can manually download from: $url"
    exit 1
}
