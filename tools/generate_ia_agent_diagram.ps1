param(
    [string]$OutputPath = "diagramas\ia_agent_framework_actualizado.png"
)

Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

function Get-Color {
    param([string]$Hex)

    $value = $Hex.TrimStart("#")
    return [System.Drawing.Color]::FromArgb(
        [Convert]::ToInt32($value.Substring(0, 2), 16),
        [Convert]::ToInt32($value.Substring(2, 2), 16),
        [Convert]::ToInt32($value.Substring(4, 2), 16)
    )
}

function New-Brush {
    param([string]$Hex)
    return [System.Drawing.SolidBrush]::new((Get-Color $Hex))
}

function New-Pen {
    param([string]$Hex, [float]$Width = 1.0)
    return [System.Drawing.Pen]::new((Get-Color $Hex), $Width)
}

function New-RoundRectPath {
    param([float]$X, [float]$Y, [float]$W, [float]$H, [float]$R)

    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $d = $R * 2
    $path.AddArc($X, $Y, $d, $d, 180, 90)
    $path.AddArc($X + $W - $d, $Y, $d, $d, 270, 90)
    $path.AddArc($X + $W - $d, $Y + $H - $d, $d, $d, 0, 90)
    $path.AddArc($X, $Y + $H - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    return $path
}

function Fill-RoundRect {
    param(
        [System.Drawing.Graphics]$Graphics,
        [float]$X,
        [float]$Y,
        [float]$W,
        [float]$H,
        [float]$R,
        [string]$Fill,
        [string]$Stroke,
        [float]$StrokeWidth = 2.0
    )

    $path = New-RoundRectPath $X $Y $W $H $R
    $brush = New-Brush $Fill
    $pen = New-Pen $Stroke $StrokeWidth
    $Graphics.FillPath($brush, $path)
    $Graphics.DrawPath($pen, $path)
    $brush.Dispose()
    $pen.Dispose()
    $path.Dispose()
}

function Draw-Text {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [string]$Color,
        [float]$X,
        [float]$Y,
        [float]$W,
        [float]$H,
        [string]$Align = "Near",
        [string]$VAlign = "Near"
    )

    $brush = New-Brush $Color
    $sf = [System.Drawing.StringFormat]::new()
    $sf.Trimming = [System.Drawing.StringTrimming]::EllipsisWord
    $sf.FormatFlags = [System.Drawing.StringFormatFlags]::LineLimit

    if ($Align -eq "Center") {
        $sf.Alignment = [System.Drawing.StringAlignment]::Center
    } elseif ($Align -eq "Far") {
        $sf.Alignment = [System.Drawing.StringAlignment]::Far
    } else {
        $sf.Alignment = [System.Drawing.StringAlignment]::Near
    }

    if ($VAlign -eq "Center") {
        $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
    } elseif ($VAlign -eq "Far") {
        $sf.LineAlignment = [System.Drawing.StringAlignment]::Far
    } else {
        $sf.LineAlignment = [System.Drawing.StringAlignment]::Near
    }

    $rect = [System.Drawing.RectangleF]::new($X, $Y, $W, $H)
    $Graphics.DrawString($Text, $Font, $brush, $rect, $sf)
    $brush.Dispose()
    $sf.Dispose()
}

function Draw-Arrow {
    param(
        [System.Drawing.Graphics]$Graphics,
        [float]$X1,
        [float]$Y1,
        [float]$X2,
        [float]$Y2,
        [string]$Color = "#64748B",
        [float]$Width = 3.0
    )

    $pen = New-Pen $Color $Width
    $cap = [System.Drawing.Drawing2D.AdjustableArrowCap]::new(6, 8, $true)
    $pen.CustomEndCap = $cap
    $Graphics.DrawLine($pen, $X1, $Y1, $X2, $Y2)
    $cap.Dispose()
    $pen.Dispose()
}

function Draw-Icon {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Kind,
        [float]$X,
        [float]$Y,
        [float]$Size,
        [string]$Accent
    )

    $bg = New-Brush "#FFFFFF"
    $pen = New-Pen $Accent 3
    $thin = New-Pen $Accent 2
    $Graphics.FillEllipse($bg, $X, $Y, $Size, $Size)
    $Graphics.DrawEllipse($pen, $X, $Y, $Size, $Size)

    $cx = $X + ($Size / 2)
    $cy = $Y + ($Size / 2)

    switch ($Kind) {
        "dataset" {
            $Graphics.DrawRectangle($thin, $X + 14, $Y + 16, $Size - 28, $Size - 30)
            $Graphics.DrawLine($thin, $X + 14, $Y + 28, $X + $Size - 14, $Y + 28)
            $Graphics.DrawLine($thin, $X + 14, $Y + 40, $X + $Size - 14, $Y + 40)
            $Graphics.DrawLine($thin, $X + 31, $Y + 16, $X + 31, $Y + $Size - 14)
            $Graphics.DrawLine($thin, $X + 48, $Y + 16, $X + 48, $Y + $Size - 14)
        }
        "config" {
            $Graphics.DrawEllipse($thin, $cx - 10, $cy - 10, 20, 20)
            for ($i = 0; $i -lt 8; $i++) {
                $angle = ($i * 45) * [Math]::PI / 180
                $x1 = $cx + [Math]::Cos($angle) * 16
                $y1 = $cy + [Math]::Sin($angle) * 16
                $x2 = $cx + [Math]::Cos($angle) * 23
                $y2 = $cy + [Math]::Sin($angle) * 23
                $Graphics.DrawLine($thin, $x1, $y1, $x2, $y2)
            }
        }
        "scenario" {
            $points = @(
                [System.Drawing.PointF]::new($X + 20, $Y + 13),
                [System.Drawing.PointF]::new($X + 48, $Y + 13),
                [System.Drawing.PointF]::new($X + 56, $Y + 21),
                [System.Drawing.PointF]::new($X + 56, $Y + 55),
                [System.Drawing.PointF]::new($X + 20, $Y + 55)
            )
            $Graphics.DrawPolygon($thin, $points)
            $Graphics.DrawLine($thin, $X + 28, $Y + 31, $X + 49, $Y + 31)
            $Graphics.DrawLine($thin, $X + 28, $Y + 42, $X + 49, $Y + 42)
        }
        "adapter" {
            $Graphics.DrawLine($thin, $X + 20, $cy, $X + 36, $cy)
            $Graphics.DrawRectangle($thin, $X + 36, $Y + 24, 19, 24)
            $Graphics.DrawLine($thin, $X + 55, $Y + 30, $X + 63, $Y + 30)
            $Graphics.DrawLine($thin, $X + 55, $Y + 42, $X + 63, $Y + 42)
            $Graphics.DrawLine($thin, $X + 22, $Y + 25, $X + 22, $Y + 47)
        }
        "phoenix" {
            $Graphics.DrawEllipse($thin, $cx - 13, $Y + 15, 26, 18)
            $Graphics.DrawLine($thin, $cx - 4, $Y + 34, $cx - 12, $Y + 45)
            $Graphics.DrawLine($thin, $cx + 4, $Y + 34, $cx + 12, $Y + 45)
            $Graphics.DrawArc($thin, $X + 20, $Y + 37, 38, 20, 15, 150)
        }
        "api" {
            Draw-Text $Graphics "API" ([System.Drawing.Font]::new("Segoe UI", 13, [System.Drawing.FontStyle]::Bold)) $Accent ($X + 10) ($Y + 22) ($Size - 20) 22 "Center" "Center"
            $Graphics.DrawLine($thin, $X + 17, $Y + 47, $X + $Size - 17, $Y + 47)
            $Graphics.DrawEllipse($thin, $X + 17, $Y + 43, 8, 8)
            $Graphics.DrawEllipse($thin, $X + $Size - 25, $Y + 43, 8, 8)
        }
        "runner" {
            $points = @(
                [System.Drawing.PointF]::new($X + 27, $Y + 19),
                [System.Drawing.PointF]::new($X + 27, $Y + 55),
                [System.Drawing.PointF]::new($X + 55, $Y + 37)
            )
            $Graphics.DrawPolygon($pen, $points)
        }
        "eval" {
            $Graphics.DrawEllipse($thin, $X + 18, $Y + 18, $Size - 36, $Size - 36)
            $Graphics.DrawLine($pen, $X + 28, $Y + 39, $X + 36, $Y + 48)
            $Graphics.DrawLine($pen, $X + 36, $Y + 48, $X + 54, $Y + 27)
        }
        "report" {
            $Graphics.DrawRectangle($thin, $X + 18, $Y + 16, $Size - 36, $Size - 30)
            $Graphics.FillRectangle((New-Brush $Accent), $X + 28, $Y + 43, 7, 13)
            $Graphics.FillRectangle((New-Brush $Accent), $X + 40, $Y + 34, 7, 22)
            $Graphics.FillRectangle((New-Brush $Accent), $X + 52, $Y + 26, 7, 30)
        }
        "shield" {
            $points = @(
                [System.Drawing.PointF]::new($cx, $Y + 14),
                [System.Drawing.PointF]::new($X + 55, $Y + 24),
                [System.Drawing.PointF]::new($X + 50, $Y + 52),
                [System.Drawing.PointF]::new($cx, $Y + 61),
                [System.Drawing.PointF]::new($X + 22, $Y + 52),
                [System.Drawing.PointF]::new($X + 17, $Y + 24)
            )
            $Graphics.DrawPolygon($thin, $points)
            $Graphics.DrawLine($pen, $X + 30, $Y + 38, $X + 38, $Y + 46)
            $Graphics.DrawLine($pen, $X + 38, $Y + 46, $X + 52, $Y + 30)
        }
    }

    $bg.Dispose()
    $pen.Dispose()
    $thin.Dispose()
}

function Draw-Card {
    param(
        [System.Drawing.Graphics]$Graphics,
        [float]$X,
        [float]$Y,
        [float]$W,
        [float]$H,
        [string]$Title,
        [string[]]$Items,
        [string]$Accent,
        [string]$Icon,
        [System.Drawing.Font]$TitleFont,
        [System.Drawing.Font]$BodyFont,
        [string]$Fill = "#FFFFFF"
    )

    Fill-RoundRect $Graphics $X $Y $W $H 18 $Fill "#CBD5E1" 2
    $bar = New-Brush $Accent
    $Graphics.FillRectangle($bar, $X, $Y, 8, $H)
    $bar.Dispose()

    Draw-Icon $Graphics $Icon ($X + 22) ($Y + 22) 58 $Accent
    Draw-Text $Graphics $Title $TitleFont "#111827" ($X + 96) ($Y + 23) ($W - 118) 42

    $body = ($Items | ForEach-Object { "- $_" }) -join "`n"
    Draw-Text $Graphics $body $BodyFont "#374151" ($X + 34) ($Y + 82) ($W - 60) ($H - 92)
}

function Draw-Badge {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [float]$X,
        [float]$Y,
        [float]$W,
        [string]$Fill,
        [string]$Stroke,
        [System.Drawing.Font]$Font
    )

    Fill-RoundRect $Graphics $X $Y $W 34 17 $Fill $Stroke 1.5
    Draw-Text $Graphics $Text $Font "#111827" $X ($Y + 6) $W 22 "Center" "Center"
}

$width = 1800
$height = 1400
$bitmap = [System.Drawing.Bitmap]::new($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

$bg = New-Brush "#F6F8FB"
$graphics.FillRectangle($bg, 0, 0, $width, $height)
$bg.Dispose()

$fontTitle = [System.Drawing.Font]::new("Segoe UI", 38, [System.Drawing.FontStyle]::Bold)
$fontSubtitle = [System.Drawing.Font]::new("Segoe UI", 17, [System.Drawing.FontStyle]::Regular)
$fontSection = [System.Drawing.Font]::new("Segoe UI", 20, [System.Drawing.FontStyle]::Bold)
$fontCardTitle = [System.Drawing.Font]::new("Segoe UI", 17, [System.Drawing.FontStyle]::Bold)
$fontBody = [System.Drawing.Font]::new("Segoe UI", 12, [System.Drawing.FontStyle]::Regular)
$fontSmall = [System.Drawing.Font]::new("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$fontFooter = [System.Drawing.Font]::new("Segoe UI", 10, [System.Drawing.FontStyle]::Regular)

Draw-Text $graphics "IA-AGENT" $fontTitle "#0F172A" 70 34 500 58
Draw-Text $graphics "Framework actualizado para agentes con IA Agentica" $fontSubtitle "#475569" 73 92 780 32
Draw-Badge $graphics "TIPO_AGENTE=agentico" 1240 45 220 "#E0F2FE" "#0284C7" $fontSmall
Draw-Badge $graphics "IA-GEN fuera de esta base" 1480 45 250 "#FEF3C7" "#D97706" $fontSmall

$sectionBrush = New-Brush "#E2E8F0"
$graphics.FillRectangle($sectionBrush, 70, 143, 1660, 3)
$graphics.FillRectangle($sectionBrush, 70, 440, 1660, 3)
$graphics.FillRectangle($sectionBrush, 70, 815, 1660, 3)
$graphics.FillRectangle($sectionBrush, 70, 1065, 1660, 3)
$sectionBrush.Dispose()

Draw-Text $graphics "1. Entrada y configuracion" $fontSection "#1E293B" 70 155 500 34
Draw-Text $graphics "2. Seleccion de adapter IA-AGENT" $fontSection "#1E293B" 70 452 600 34
Draw-Text $graphics "3. Orquestacion de ejecucion" $fontSection "#1E293B" 70 827 600 34
Draw-Text $graphics "4. Evaluacion y salida" $fontSection "#1E293B" 70 1077 500 34

Draw-Card $graphics 80 205 350 190 "Dataset CSV" @(
    "data/casos_de_prueba_desa.csv",
    "data/agentes_agenticos.csv",
    "mensaje_inicio + secuencia",
    "reglas_juez y caso_de_prueba"
) "#2563EB" "dataset" $fontCardTitle $fontBody "#FFFFFF"

Draw-Card $graphics 515 205 350 190 "Configuracion" @(
    ".env.desa / .env.<ambiente>",
    "AGENT_ADAPTER",
    "TIPO_AGENTE=agentico",
    "EVAL_PROFILE"
) "#7C3AED" "config" $fontCardTitle $fontBody "#FFFFFF"

Draw-Card $graphics 950 205 350 190 "Escenario" @(
    "core/scenario.py",
    "normaliza columnas del CSV",
    "arma metadata del caso",
    "entrega contrato base"
) "#059669" "scenario" $fontCardTitle $fontBody "#FFFFFF"

Draw-Card $graphics 1385 205 330 190 "Factory" @(
    "adapters/factory.py",
    "build_agent_client()",
    "phoenix",
    "agentico_rest"
) "#EA580C" "adapter" $fontCardTitle $fontBody "#FFFFFF"

Draw-Arrow $graphics 430 282 515 282
Draw-Arrow $graphics 865 282 950 282
Draw-Arrow $graphics 1300 282 1385 282

Draw-Card $graphics 110 520 735 250 "Adapter Phoenix" @(
    "AGENT_ADAPTER=phoenix",
    "payload.py + client.py + customer proc",
    "prompts AR/I/R exclusivos de Phoenix",
    "user_simulator exclusivo de Phoenix",
    "EVAL_PROFILE=phoenix_cobranzas"
) "#DC2626" "phoenix" $fontCardTitle $fontBody "#FFF7F7"

Draw-Card $graphics 955 520 735 250 "Adapter Agentico REST" @(
    "AGENT_ADAPTER=agentico_rest",
    "AGENTICO_REST_URL y AGENTICO_REST_*",
    "endpoint REST de agente IA-AGENT",
    "flujo sin user_simulator",
    "EVAL_PROFILE=agentico_default"
) "#0891B2" "api" $fontCardTitle $fontBody "#F0FDFA"

Draw-Arrow $graphics 1550 395 475 520 "#94A3B8" 2.5
Draw-Arrow $graphics 1550 395 1320 520 "#94A3B8" 2.5

Draw-Card $graphics 455 885 890 150 "Runner IA-AGENT" @(
    "core/runner.py ejecuta mensaje inicial y secuencia del CSV",
    "si el adapter implementa simulate_user, continua la conversacion",
    "si no lo implementa, termina el flujo definido y evalua la conversacion"
) "#16A34A" "runner" $fontCardTitle $fontBody "#F0FDF4"

Draw-Arrow $graphics 475 770 820 885 "#94A3B8" 2.5
Draw-Arrow $graphics 1320 770 985 885 "#94A3B8" 2.5

Draw-Card $graphics 110 1135 510 195 "Evaluacion LLM" @(
    "evaluation/juez.py resuelve pipeline",
    "juez_funcionalidades solo para Phoenix",
    "juez_respuesta para agentico_default",
    "juez_metricas para todos los adapters"
) "#4F46E5" "eval" $fontCardTitle $fontBody "#EEF2FF"

Draw-Card $graphics 700 1135 410 195 "Reportes" @(
    "reporting/report.py",
    "HTML y CSV",
    "OUTPUT_DIR=./resultados",
    "evidencia por escenario"
) "#BE123C" "report" $fontCardTitle $fontBody "#FFF1F2"

Draw-Card $graphics 1190 1135 500 195 "Seguridad y alcance" @(
    ".env.* no se versiona",
    "tokens fuera del repositorio",
    "IA-AGENT solo agentico",
    "IA-GEN se implementa aparte"
) "#475569" "shield" $fontCardTitle $fontBody "#F8FAFC"

Draw-Arrow $graphics 900 1035 365 1135
Draw-Arrow $graphics 620 1232 700 1232
Draw-Arrow $graphics 1110 1232 1190 1232

$noteBrush = New-Brush "#F8FAFC"
$notePen = New-Pen "#CBD5E1" 1.5
$graphics.FillRectangle($noteBrush, 80, 1352, 1640, 1)
$noteBrush.Dispose()
$notePen.Dispose()
Draw-Text $graphics "Generado desde tools/generate_ia_agent_diagram.ps1 - refleja la arquitectura actual: Phoenix con simulador propio y agentico_rest como adapter IA-AGENT generico." $fontFooter "#64748B" 80 1360 1640 22 "Center" "Center"

$outputFullPath = Join-Path (Get-Location) $OutputPath
$outputDir = Split-Path -Parent $outputFullPath
if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

$bitmap.Save($outputFullPath, [System.Drawing.Imaging.ImageFormat]::Png)

$fontTitle.Dispose()
$fontSubtitle.Dispose()
$fontSection.Dispose()
$fontCardTitle.Dispose()
$fontBody.Dispose()
$fontSmall.Dispose()
$fontFooter.Dispose()
$graphics.Dispose()
$bitmap.Dispose()

Write-Output $outputFullPath
