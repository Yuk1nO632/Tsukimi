$ErrorActionPreference = 'Stop'
$frontendRoot = Split-Path -Parent $PSScriptRoot
$coverDirectory = Join-Path $frontendRoot 'public\covers'
[System.IO.Directory]::CreateDirectory($coverDirectory) | Out-Null
$subjectIds = @(400602, 395378, 328609, 183878, 207195, 326895)
$userAgent = 'Tsukimi/0.2 (personal fullstack study project)'
$catalog = @()

foreach ($subjectId in $subjectIds) {
    Write-Host "Reading Bangumi subject $subjectId ..."
    $subject = Invoke-RestMethod -Uri "https://api.bgm.tv/v0/subjects/$subjectId" -UserAgent $userAgent -TimeoutSec 30
    if (-not $subject.id -or $subject.type -ne 2) { throw "Invalid anime subject: $subjectId" }
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

$catalogJson = ConvertTo-Json -InputObject @($catalog) -Depth 10
$meta = [ordered]@{ source = 'Bangumi Open API'; syncedAt = [DateTimeOffset]::Now.ToString('o'); mode = 'local snapshot'; count = $catalog.Count }
$metaJson = ConvertTo-Json -InputObject $meta -Depth 4
$output = "// Generated from Bangumi public API. Refresh with npm.cmd run sync:catalog.`nexport const bangumiCatalog = $catalogJson;`nexport const catalogMeta = $metaJson;`n"
[System.IO.File]::WriteAllText((Join-Path $frontendRoot 'lib\catalog.generated.js'), $output, [System.Text.UTF8Encoding]::new($false))
Write-Host "Catalog updated: $($catalog.Count) anime. Video sources are not included."
