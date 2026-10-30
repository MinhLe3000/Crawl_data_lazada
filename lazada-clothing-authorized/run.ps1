param([double]$PageWait = 12, [double]$ReviewWait = 6, [switch]$Headed)
$python = Join-Path $PSScriptRoot "../lazada-football-boots/.venv/Scripts/python.exe"
$crawlArgs = @("-u", (Join-Path $PSScriptRoot "crawl_shop.py"), "--page-wait", "$PageWait", "--review-wait", "$ReviewWait")
if ($Headed) { $crawlArgs += "--headed" }
& $python @crawlArgs
exit $LASTEXITCODE
