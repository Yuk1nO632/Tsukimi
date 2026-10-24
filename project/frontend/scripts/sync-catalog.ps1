$ErrorActionPreference = 'Stop'
$frontendRoot = Split-Path -Parent $PSScriptRoot
$coverDirectory = Join-Path $frontendRoot 'public\covers'
[System.IO.Directory]::CreateDirectory($coverDirectory) | Out-Null
# Curated 2026 autumn picks; change these IDs and the season together next quarter.
$featuredIds = @(568244, 548156, 567896)
$featuredSeason = [ordered]@{ label = '2026 年 10 月 · 秋季新番'; start = '2026-10-01'; end = '2027-01-01' }
$subjectIds = @($featuredIds) + @(400602, 395378, 328609, 183878, 207195, 326895)
$userAgent = 'Tsukimi/0.2 (personal fullstack study project)'
$catalog = @()

foreach ($subjectId in $subjectIds) {
    Write-Host "Reading Bangumi subject $subjectId ..."
    # Windows PowerShell 5.1 may infer a legacy charset when JSON omits charset.
    $response = Invoke-WebRequest -UseBasicParsing -Uri "https://api.bgm.tv/v0/subjects/$subjectId" -UserAgent $userAgent -TimeoutSec 30
    $subject = [System.Text.Encoding]::UTF8.GetString($response.RawContentStream.ToArray()) | ConvertFrom-Json
    if (-not $subject.id -or $subject.type -ne 2) { throw "Invalid anime subject: $subjectId" }
    if ($subjectId -in $featuredIds) {
        if ([string]::IsNullOrWhiteSpace($subject.date) -or $subject.date -lt $featuredSeason.start -or $subject.date -ge $featuredSeason.end) {
            throw "Featured subject $subjectId is outside the selected season. Update the curated IDs and season together."
        }
    }
    $title = $subject.name_cn
    if ([string]::IsNullOrWhiteSpace($title)) { $title = $subject.name }
    $coverUrl = $subject.images.large
    if ([string]::IsNullOrWhiteSpace($coverUrl)) { throw "No cover image: $subjectId" }
    $extension = [System.IO.Path]::GetExtension(([uri]$coverUrl).AbsolutePath)
    if ($extension -notin @('.jpg', '.jpeg', '.png', '.webp')) { $extension = '.jpg' }
    $coverName = "bgm-$subjectId$extension"
    Invoke-WebRequest -Uri $coverUrl -UserAgent $userAgent -OutFile (Join-Path $coverDirectory $coverName) -TimeoutSec 30 | Out-Null
    $preferredTags = @('奇幻', '冒险', '治愈', '音乐', '日常', '旅行', '青春', '悬疑', '科幻', '恋爱', '美食', '露营')
    $tags = @($subject.tags | Where-Object { $_.name -in $preferredTags } | Select-Object -First 3 -ExpandProperty name)
    if ($tags.Count -eq 0) { $tags = @('动画') }
    $episodeCount = [int]$subject.eps
    if ($episodeCount -le 0) { $episodeCount = [int]$subject.total_episodes }
    $summary = [string]$subject.summary
    $summary = $summary -replace '\[/?[a-zA-Z][^\]]*\]', ''
    $description = ($summary -split "`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -First 1)
    if ([string]::IsNullOrWhiteSpace($description)) { $description = '在故事里，遇见下一份喜欢。' }
    $releaseWeekday = 0
    $year = ''
    if (-not [string]::IsNullOrWhiteSpace($subject.date)) {
        $releaseDate = [datetime]::Parse($subject.date)
        $releaseWeekday = [int]$releaseDate.DayOfWeek
        if ($releaseWeekday -eq 0) { $releaseWeekday = 7 }
        $year = $releaseDate.Year.ToString()
    }
    $catalog += [ordered]@{
        id = "bgm-$subjectId"
        bangumiId = [int]$subjectId
        title = $title
        originalTitle = $subject.name
        category = ($tags -join ' / ')
        tags = $tags
        episodes = $episodeCount
        description = $description.Trim()
        synopsis = $summary.Trim()
        cover = "/covers/$coverName"
        coverSource = $coverUrl
        sourceUrl = "https://bgm.tv/subject/$subjectId"
        sourceName = 'Bangumi'
        releaseDate = $subject.date
        releaseWeekday = $releaseWeekday
        year = $year
        score = [double]$subject.rating.score
        ratingCount = [int]$subject.rating.total
        isDemo = $false
    }
    Write-Host "Saved: $title ($episodeCount episodes)"
}

$meta = [ordered]@{ source = 'Bangumi Open API'; syncedAt = [DateTimeOffset]::Now.ToString('o'); mode = 'local snapshot'; count = $catalog.Count; featuredIds = @($featuredIds | ForEach-Object { "bgm-$_" }); featuredSeason = $featuredSeason }
# One JSON catalog is shared by the Next.js UI and FastAPI validation.
$sharedDirectory = Join-Path (Split-Path -Parent $frontendRoot) 'catalog'
[System.IO.Directory]::CreateDirectory($sharedDirectory) | Out-Null
$output = ConvertTo-Json -InputObject ([ordered]@{ anime = @($catalog); meta = $meta }) -Depth 12
[System.IO.File]::WriteAllText((Join-Path $sharedDirectory 'catalog.json'), $output + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Host "Catalog updated: $($catalog.Count) anime. Restart the backend after syncing. Video sources are not included."
