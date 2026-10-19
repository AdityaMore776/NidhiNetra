# Build → quality gate → export PPTX → render through PowerPoint (PDF + preview PNGs).
# Usage: powershell -File export.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
& "C:\Program Files\Git\bin\bash.exe" ./check.sh
if (Test-Path exports) { Remove-Item -Recurse -Force exports }
python3 "C:\Users\abhim\.claude\skills\ppt-master\scripts\svg_to_pptx.py" . --roundtrip --primary-language en-IN
$deck = Get-ChildItem "$here\exports\*.pptx" | Select-Object -First 1
$out = Join-Path $here "preview"
if (-not (Test-Path $out)) { New-Item -ItemType Directory $out | Out-Null }
Get-ChildItem $out -Filter "slide-*.png" -ErrorAction SilentlyContinue | Remove-Item
$pp = New-Object -ComObject PowerPoint.Application
$p = $pp.Presentations.Open($deck.FullName, $true, $false, $false)
$p.SaveAs([System.IO.Path]::ChangeExtension($deck.FullName, ".pdf"), 32)
for ($i = 1; $i -le $p.Slides.Count; $i++) {
    $p.Slides($i).Export((Join-Path $out ("slide-{0}.png" -f $i)), "PNG", 1920, 1080)
}
$p.Close()
if ($pp.Presentations.Count -eq 0) { $pp.Quit() }
"exported {0}; rendered {1} slides" -f $deck.Name, (Get-ChildItem $out -Filter "slide-*.png").Count
