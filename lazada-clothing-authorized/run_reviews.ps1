param([double]$PageWait = 15, [double]$ReviewWait = 8, [int]$ManualTimeout = 600)
$python = Join-Path $PSScriptRoot "../lazada-football-boots/.venv/Scripts/python.exe"
$script = Join-Path $PSScriptRoot "../crawl_clothing_reviews.py"
& $python -u $script --shop "lazada-clothing-authorized" --page-wait $PageWait --review-wait $ReviewWait --manual-timeout $ManualTimeout
exit $LASTEXITCODE
