param(
    [Parameter(Mandatory = $true)]
    [string]$FfmpegPath
)

$ErrorActionPreference = 'Stop'
$fixtureDir = Join-Path $PSScriptRoot 'fixtures\golden'
$audio = Join-Path $fixtureDir 'golden-audio-anchor.wav'
$video = Join-Path $fixtureDir 'golden-video-anchor.mp4'

Add-Type -AssemblyName System.Speech
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $speaker.Rate = -1
    $speaker.SetOutputToWaveFile($audio)
    $speaker.Speak('Learning evidence anchor')
} finally {
    $speaker.Dispose()
}

& $FfmpegPath -y -f lavfi -i 'color=c=#102a43:s=960x540:r=24' -i $audio -shortest -c:v mpeg4 -c:a aac $video -loglevel error
if (-not (Test-Path -LiteralPath $audio) -or -not (Test-Path -LiteralPath $video)) {
    throw 'golden media fixture generation did not produce both files'
}
