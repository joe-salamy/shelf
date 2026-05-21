$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $repo

$activate = Join-Path $repo "venv\Scripts\Activate.ps1"
if (-not (Test-Path -LiteralPath $activate)) {
    throw "Could not find venv activation script at $activate"
}

. $activate

$dataDir = "C:\Users\joesa\Documents\law-school-python\law-essay-gen\docs\data"
$books = @(
    (Get-ChildItem -LiteralPath $dataDir -Filter "Point Made - How to Write Like the Nation*Top Advocates (2nd) -- Ross Guberman.epub" | Select-Object -First 1).FullName,
    (Join-Path $dataDir "On Writing Well - The Classic Guide to Writing Nonfiction -- William Zinsser.epub")
)

foreach ($book in $books) {
    if (-not (Test-Path -LiteralPath $book)) {
        throw "Input file not found: $book"
    }

    $name = Split-Path -Leaf $book
    Write-Host "[$(Get-Date -Format o)] Starting $name"

    shelf $book --summarize --log --yes
    if ($LASTEXITCODE -ne 0) {
        throw "shelf failed for $name with exit code $LASTEXITCODE"
    }

    Write-Host "[$(Get-Date -Format o)] Finished $name"
}

Write-Host "[$(Get-Date -Format o)] All books finished."
