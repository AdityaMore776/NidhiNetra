# Render DRISHTI_SIH26102_v2.pptx through PowerPoint itself (real fonts), to a PDF
# and one PNG per slide in .\preview. Usage:  powershell -File render.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$deck = Join-Path $here "DRISHTI_SIH26102_v2.pptx"
$pdf = Join-Path $here "DRISHTI_SIH26102_v2.pdf"
$out = Join-Path $here "preview"
if (-not (Test-Path $out)) { New-Item -ItemType Directory $out | Out-Null }
Get-ChildItem $out -Filter "slide-*.png" -ErrorAction SilentlyContinue | Remove-Item
$pp = New-Object -ComObject PowerPoint.Application
$p = $pp.Presentations.Open($deck, $true, $false, $false)
$p.SaveAs($pdf, 32)   # ppSaveAsPDF
for ($i = 1; $i -le $p.Slides.Count; $i++) {
    $p.Slides($i).Export((Join-Path $out ("slide-{0}.png" -f $i)), "PNG", 2400, 1350)
}
$p.Close()
if ($pp.Presentations.Count -eq 0) { $pp.Quit() }
"rendered {0} slides" -f (Get-ChildItem $out -Filter "slide-*.png").Count
