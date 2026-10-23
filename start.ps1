param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 5173
)

$experimentDirectory = Join-Path $PSScriptRoot 'experiments\01-browser-basics'
Write-Host "Tsukimi: http://127.0.0.1:$Port"
Write-Host 'Press Ctrl+C to stop.'
python -m http.server $Port --bind 127.0.0.1 --directory $experimentDirectory
