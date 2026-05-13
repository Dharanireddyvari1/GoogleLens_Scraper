[CmdletBinding()]
param(
  [string]$ApiBase = "https://cognition-negate-amnesty.ngrok-free.dev/google-lens-visual",
  [string]$CsvPath = ".\image_urls.csv",
  [string]$OutputDir = ".\visual_match_html",
  [int]$Limit = 100,
  [int]$StartAt = 1
)

if (-not (Test-Path $CsvPath)) {
  throw "CSV file not found: $CsvPath"
}

$rows = Import-Csv $CsvPath
$rows = @($rows | Where-Object { $_.image_url -and $_.image_url.Trim() -ne "" })
if ($StartAt -lt 1) {
  throw "StartAt must be 1 or greater"
}
$rows = $rows | Select-Object -Skip ($StartAt - 1) -First $Limit
$logs = @()
$logPath = ".\test_logs.json"

if (-not (Test-Path $OutputDir)) {
  New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$i = $StartAt
$success = 0
$totalTime = 0.0

foreach ($row in $rows) {
  $img = $row.image_url
  $htmlFile = Join-Path $OutputDir ("visual_match_{0:D3}.html" -f $i)
  if (Test-Path $htmlFile) {
    Remove-Item -LiteralPath $htmlFile -Force
  }
  $status = 0
  $time = 0.0
  $size = 0
  $exitCode = 0
  $errorText = ""

  $encoded = [uri]::EscapeDataString($img)
  $url = "${ApiBase}?imageUrl=$encoded"

  $curlLines = curl.exe -sS -o "$htmlFile" -w "METRICS:%{http_code},%{time_total},%{size_download}" "$url" 2>&1
  $exitCode = $LASTEXITCODE

  $metricsLine = ($curlLines | Where-Object { $_ -like "METRICS:*" } | Select-Object -Last 1)
  $errorText = (($curlLines | Where-Object { $_ -notlike "METRICS:*" }) -join " ").Trim()
  $output = if ($metricsLine) { $metricsLine.Substring(8) } else { "0,0,0" }
  $parts = $output -split ","

  if ($parts.Count -ge 3 -and [int]::TryParse($parts[0], [ref]$status) -and [double]::TryParse($parts[1], [ref]$time) -and [int64]::TryParse($parts[2], [ref]$size)) {
    # Parsed curl metrics successfully.
  }

  $totalTime += $time

  if ($status -eq 200) {
    $success++
  }

  $completed = $i - $StartAt + 1
  $avgLatency = [math]::Round($totalTime / $completed, 2)
  $successRate = [math]::Round(($success / $completed) * 100, 2)

  $log = [pscustomobject]@{
    id = $i
    image_url = $img
    status = $status
    time_seconds = $time
    size_bytes = $size
    html_file = $htmlFile
    mode = "visual_match"
    exit_code = $exitCode
    error = $errorText
    avg_latency_so_far = $avgLatency
    success_rate_so_far = $successRate
  }

  $logs += $log
  $logs | ConvertTo-Json -Depth 5 | Set-Content $logPath

  Write-Host "ID=$i STATUS=$status TIME=$time SIZE=$size EXIT=$exitCode FILE=$htmlFile AVG_LATENCY=$avgLatency SUCCESS_RATE=$successRate%"
  if ($errorText) {
    Write-Host "  ERROR=$errorText"
  }

  $i++
}

Write-Host "Saved HTML files to $OutputDir"
Write-Host "Saved logs to $logPath"
