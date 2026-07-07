param(
    [string]$OutputPath = "diagramas\ia_agent_framework_8_pasos_actualizado.png"
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
        [float]$StrokeWidth = 1.5
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
    if ($Align -eq "Center") { $sf.Alignment = [System.Drawing.StringAlignment]::Center }
    elseif ($Align -eq "Far") { $sf.Alignment = [System.Drawing.StringAlignment]::Far }
    else { $sf.Alignment = [System.Drawing.StringAlignment]::Near }
    if ($VAlign -eq "Center") { $sf.LineAlignment = [System.Drawing.StringAlignment]::Center }
    elseif ($VAlign -eq "Far") { $sf.LineAlignment = [System.Drawing.StringAlignment]::Far }
    else { $sf.LineAlignment = [System.Drawing.StringAlignment]::Near }
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
        [string]$Color = "#1E40AF"
    )
    $pen = New-Pen $Color 3
    $cap = [System.Drawing.Drawing2D.AdjustableArrowCap]::new(7, 8, $true)
    $pen.CustomEndCap = $cap
    $Graphics.DrawLine($pen, $X1, $Y1, $X2, $Y2)
    $cap.Dispose()
    $pen.Dispose()
}

function Draw-CircleNumber {
    param(
        [System.Drawing.Graphics]$Graphics,
        [int]$Number,
        [float]$X,
        [float]$Y,
        [string]$Fill,
        [System.Drawing.Font]$Font
    )
    $brush = New-Brush $Fill
    $pen = New-Pen "#FFFFFF" 3
    $Graphics.FillEllipse($brush, $X, $Y, 43, 43)
    $Graphics.DrawEllipse($pen, $X, $Y, 43, 43)
    Draw-Text $Graphics ([string]$Number) $Font "#FFFFFF" $X ($Y + 2) 43 38 "Center" "Center"
    $brush.Dispose()
    $pen.Dispose()
}

function Draw-MiniIcon {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Icon,
        [float]$X,
        [float]$Y,
        [string]$Color,
        [System.Drawing.Font]$Font
    )
    $pen = New-Pen $Color 2.5
    $brush = New-Brush $Color
    switch ($Icon) {
        "target" {
            $Graphics.DrawEllipse($pen, $X + 4, $Y + 4, 24, 24)
            $Graphics.DrawEllipse($pen, $X + 11, $Y + 11, 10, 10)
            $Graphics.DrawLine($pen, $X + 16, $Y + 16, $X + 30, $Y + 2)
        }
        "chat" {
            $Graphics.DrawEllipse($pen, $X + 3, $Y + 6, 27, 20)
            $Graphics.DrawLine($pen, $X + 10, $Y + 25, $X + 6, $Y + 31)
        }
        "list" {
            for ($i = 0; $i -lt 3; $i++) {
                $yy = $Y + 6 + ($i * 9)
                $Graphics.FillEllipse($brush, $X + 4, $yy, 4, 4)
                $Graphics.DrawLine($pen, $X + 13, $yy + 2, $X + 31, $yy + 2)
            }
        }
        "tools" {
            $Graphics.DrawLine($pen, $X + 5, $Y + 5, $X + 28, $Y + 28)
            $Graphics.DrawLine($pen, $X + 28, $Y + 5, $X + 5, $Y + 28)
        }
        "db" {
            $Graphics.DrawEllipse($pen, $X + 4, $Y + 4, 26, 8)
            $Graphics.DrawLine($pen, $X + 4, $Y + 8, $X + 4, $Y + 27)
            $Graphics.DrawLine($pen, $X + 30, $Y + 8, $X + 30, $Y + 27)
            $Graphics.DrawEllipse($pen, $X + 4, $Y + 22, 26, 8)
        }
        "doc" {
            $Graphics.DrawRectangle($pen, $X + 7, $Y + 4, 21, 28)
            $Graphics.DrawLine($pen, $X + 12, $Y + 14, $X + 24, $Y + 14)
            $Graphics.DrawLine($pen, $X + 12, $Y + 22, $X + 24, $Y + 22)
        }
        "plug" {
            $Graphics.DrawRectangle($pen, $X + 8, $Y + 9, 18, 16)
            $Graphics.DrawLine($pen, $X + 12, $Y + 4, $X + 12, $Y + 10)
            $Graphics.DrawLine($pen, $X + 22, $Y + 4, $X + 22, $Y + 10)
            $Graphics.DrawLine($pen, $X + 17, $Y + 25, $X + 17, $Y + 32)
        }
        "globe" {
            $Graphics.DrawEllipse($pen, $X + 4, $Y + 4, 26, 26)
            $Graphics.DrawLine($pen, $X + 4, $Y + 17, $X + 30, $Y + 17)
            $Graphics.DrawArc($pen, $X + 10, $Y + 4, 14, 26, 90, 180)
            $Graphics.DrawArc($pen, $X + 10, $Y + 4, 14, 26, -90, 180)
        }
        "brain" {
            Draw-Text $Graphics "AI" $Font $Color $X ($Y + 6) 34 22 "Center" "Center"
        }
        "folder" {
            $Graphics.DrawRectangle($pen, $X + 4, $Y + 10, 28, 20)
            $Graphics.DrawLine($pen, $X + 4, $Y + 10, $X + 13, $Y + 5)
            $Graphics.DrawLine($pen, $X + 13, $Y + 5, $X + 22, $Y + 10)
        }
        "code" {
            Draw-Text $Graphics "</>" $Font $Color $X ($Y + 6) 34 22 "Center" "Center"
        }
        "user" {
            $Graphics.DrawEllipse($pen, $X + 12, $Y + 4, 10, 10)
            $Graphics.DrawArc($pen, $X + 6, $Y + 15, 22, 17, 200, 140)
        }
        "warn" {
            $points = @(
                [System.Drawing.PointF]::new($X + 17, $Y + 3),
                [System.Drawing.PointF]::new($X + 31, $Y + 30),
                [System.Drawing.PointF]::new($X + 3, $Y + 30)
            )
            $Graphics.DrawPolygon($pen, $points)
            $Graphics.DrawLine($pen, $X + 17, $Y + 12, $X + 17, $Y + 21)
            $Graphics.FillEllipse($brush, $X + 15, $Y + 25, 4, 4)
        }
        default {
            $Graphics.FillEllipse($brush, $X + 10, $Y + 10, 14, 14)
        }
    }
    $pen.Dispose()
    $brush.Dispose()
}

function Draw-Item {
    param(
        [System.Drawing.Graphics]$Graphics,
        [float]$X,
        [float]$Y,
        [float]$W,
        [float]$H,
        [string]$Text,
        [string]$Icon,
        [string]$Accent,
        [System.Drawing.Font]$Font,
        [System.Drawing.Font]$IconFont,
        [string]$Fill = "#FFFFFF"
    )
    Fill-RoundRect $Graphics $X $Y $W $H 8 $Fill "#BFD2EA" 1.2
    Draw-MiniIcon $Graphics $Icon ($X + 8) ($Y + (($H - 34) / 2)) $Accent $IconFont
    Draw-Text $Graphics $Text $Font "#0F2A5F" ($X + 43) ($Y + 9) ($W - 49) ($H - 14)
}

function Draw-StepCard {
    param(
        [System.Drawing.Graphics]$Graphics,
        [int]$Number,
        [float]$X,
        [float]$Y,
        [float]$W,
        [float]$H,
        [string]$Title,
        [object[]]$Items,
        [string]$Accent,
        [string]$Fill,
        [System.Drawing.Font]$TitleFont,
        [System.Drawing.Font]$ItemFont,
        [System.Drawing.Font]$IconFont,
        [System.Drawing.Font]$NumberFont
    )
    Draw-CircleNumber $Graphics $Number ($X + ($W / 2) - 21.5) ($Y - 51) $Accent $NumberFont
    Fill-RoundRect $Graphics $X $Y $W $H 12 $Fill $Accent 1.6
    Draw-Text $Graphics $Title $TitleFont $Accent ($X + 13) ($Y + 14) ($W - 26) 56 "Center" "Center"
    Fill-RoundRect $Graphics ($X + 8) ($Y + 78) ($W - 16) ($H - 88) 8 "#FFFFFF" "#CADCF2" 1.2

    $itemY = $Y + 93
    foreach ($item in $Items) {
        Draw-Item $Graphics ($X + 15) $itemY ($W - 30) $item.H $item.Text $item.Icon $Accent $ItemFont $IconFont $item.Fill
        $itemY += $item.H + 10
    }
}

function New-ItemDef {
    param([string]$Text, [string]$Icon, [float]$H = 48, [string]$Fill = "#FFFFFF")
    return [PSCustomObject]@{ Text = $Text; Icon = $Icon; H = $H; Fill = $Fill }
}

$width = 1900
$height = 1080
$bitmap = [System.Drawing.Bitmap]::new($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

$bg = New-Brush "#F8FAFC"
$graphics.FillRectangle($bg, 0, 0, $width, $height)
$bg.Dispose()

$fontTitle = [System.Drawing.Font]::new("Segoe UI", 37, [System.Drawing.FontStyle]::Bold)
$fontSubtitle = [System.Drawing.Font]::new("Segoe UI", 16, [System.Drawing.FontStyle]::Regular)
$fontStepTitle = [System.Drawing.Font]::new("Segoe UI", 13, [System.Drawing.FontStyle]::Bold)
$fontItem = [System.Drawing.Font]::new("Segoe UI", 9.2, [System.Drawing.FontStyle]::Regular)
$fontIcon = [System.Drawing.Font]::new("Segoe UI", 10.5, [System.Drawing.FontStyle]::Bold)
$fontNumber = [System.Drawing.Font]::new("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
$fontTechTitle = [System.Drawing.Font]::new("Segoe UI", 22, [System.Drawing.FontStyle]::Bold)
$fontTech = [System.Drawing.Font]::new("Segoe UI", 13, [System.Drawing.FontStyle]::Bold)
$fontLegend = [System.Drawing.Font]::new("Segoe UI", 10.5, [System.Drawing.FontStyle]::Regular)
$fontFooter = [System.Drawing.Font]::new("Segoe UI", 9, [System.Drawing.FontStyle]::Regular)

Draw-Text $graphics "IA-AGENT: Framework para Agentes con IA Agentica" $fontTitle "#0B1F4D" 80 24 ($width - 160) 58 "Center" "Center"
Draw-Text $graphics "Evaluar comportamiento, herramientas, estado, planificacion, conversacion y respuesta final" $fontSubtitle "#475569" 80 84 ($width - 160) 30 "Center" "Center"

$y = 205
$cardH = 560
$w = 190
$gap = 20
$x0 = 30
$xs = @()
for ($i = 0; $i -lt 8; $i++) { $xs += $x0 + ($i * ($w + $gap)) }

$blue = "#1D4ED8"
$teal = "#0F766E"
$purple = "#7E22CE"

$steps = @(
    @{
        Title = "Disenar Dataset de Evaluacion"
        Accent = $blue
        Fill = "#F8FBFF"
        Items = @(
            (New-ItemDef "Objetivo" "target" 46),
            (New-ItemDef "Mensaje inicial" "chat" 46),
            (New-ItemDef "Secuencia opcional" "list" 52),
            (New-ItemDef "Herramientas" "tools" 46),
            (New-ItemDef "Estado esperado" "db" 50),
            (New-ItemDef "Reglas del juez" "doc" 52)
        )
    },
    @{
        Title = "Cargar Configuracion"
        Accent = $blue
        Fill = "#F8FBFF"
        Items = @(
            (New-ItemDef ".env" "doc" 46),
            (New-ItemDef "ADAPTER" "plug" 46),
            (New-ItemDef "TIPO=agentico" "chat" 48),
            (New-ItemDef "EVAL_PROFILE" "user" 46),
            (New-ItemDef "Endpoints / URLs" "globe" 50),
            (New-ItemDef "Azure OpenAI" "brain" 52)
        )
    },
    @{
        Title = "Preparar Escenario"
        Accent = $blue
        Fill = "#F8FBFF"
        Items = @(
            (New-ItemDef "Scenario Loader" "folder" 54),
            (New-ItemDef "Metadata" "doc" 54),
            (New-ItemDef "Estado inicial" "db" 54),
            (New-ItemDef "Payload adapter" "code" 58)
        )
    },
    @{
        Title = "Invocar Adapter"
        Accent = $teal
        Fill = "#F0FDFA"
        Items = @(
            (New-ItemDef "factory.py" "plug" 50 "#F8FFFE"),
            (New-ItemDef "Phoenix Adapter" "target" 48 "#F8FFFE"),
            (New-ItemDef "Agentico REST Adapter" "globe" 52 "#F8FFFE"),
            (New-ItemDef "Contrato -> API" "code" 56 "#F8FFFE")
        )
    },
    @{
        Title = "Ejecucion Agentica"
        Accent = $blue
        Fill = "#F8FBFF"
        Items = @(
            (New-ItemDef "Planificacion" "list" 48),
            (New-ItemDef "Razonamiento visible" "brain" 54),
            (New-ItemDef "Tool calls" "tools" 54),
            (New-ItemDef "Memoria y estado" "db" 48),
            (New-ItemDef "Respuesta final" "chat" 54)
        )
    },
    @{
        Title = "Conducir Conversacion"
        Accent = $blue
        Fill = "#F8FBFF"
        Items = @(
            (New-ItemDef "csv_sequence" "list" 54),
            (New-ItemDef "simulador Phoenix" "user" 56 "#EFF6FF"),
            (New-ItemDef "REST sin simulador" "chat" 56),
            (New-ItemDef "MAX_TURNS_SAFE" "warn" 54)
        )
    },
    @{
        Title = "Construir Traza"
        Accent = $blue
        Fill = "#F8FBFF"
        Items = @(
            (New-ItemDef "Mensajes E/S" "chat" 48),
            (New-ItemDef "Payload" "code" 48),
            (New-ItemDef "Estado inicial/final" "db" 50),
            (New-ItemDef "Errores" "warn" 50),
            (New-ItemDef "Latencias/raw" "doc" 54)
        )
    },
    @{
        Title = "Evaluar y Reportar"
        Accent = $purple
        Fill = "#FBF7FF"
        Items = @(
            (New-ItemDef "Juez funcional Phoenix" "tools" 50 "#FFFBFF"),
            (New-ItemDef "Juez respuesta" "chat" 56 "#FFFBFF"),
            (New-ItemDef "Juez metricas" "list" 50 "#FFFBFF"),
            (New-ItemDef "Reporte HTML y CSV" "doc" 50 "#FFFBFF"),
            (New-ItemDef "Evidencias JSON" "folder" 52 "#FFFBFF")
        )
    }
)

for ($i = 0; $i -lt 8; $i++) {
    Draw-StepCard $graphics ($i + 1) $xs[$i] $y $w $cardH $steps[$i].Title $steps[$i].Items $steps[$i].Accent $steps[$i].Fill $fontStepTitle $fontItem $fontIcon $fontNumber
    if ($i -lt 7) {
        Draw-Arrow $graphics ($xs[$i] + $w + 4) ($y + 285) ($xs[$i + 1] - 4) ($y + 285)
    }
}

$techY = 820
Draw-Text $graphics "Tecnologias Base" $fontTechTitle "#0B1F4D" 0 778 $width 38 "Center" "Center"
Fill-RoundRect $graphics 200 $techY 1500 88 10 "#FFFFFF" "#64748B" 1.3

$techs = @(
    @("Python", "PY", "#2563EB"),
    @("Pandas", "PD", "#334155"),
    @("Requests", "HTTP", "#0F766E"),
    @("Azure OpenAI", "AZ", "#0078D4"),
    @("dotenv", "ENV", "#64748B"),
    @("unittest", "UT", "#1D4ED8"),
    @("Git / GitHub", "GIT", "#F97316")
)

$tx = 245
foreach ($tech in $techs) {
    Draw-Text $graphics $tech[1] $fontTech $tech[2] $tx ($techY + 26) 62 30 "Center" "Center"
    Draw-Text $graphics $tech[0] $fontTech "#0F172A" ($tx + 70) ($techY + 27) 150 30
    $sepPen = New-Pen "#CBD5E1" 1
    $graphics.DrawLine($sepPen, $tx + 238, $techY + 22, $tx + 238, $techY + 66)
    $sepPen.Dispose()
    $tx += 205
}

$legendY = 950
Fill-RoundRect $graphics 515 $legendY 870 54 8 "#FFFFFF" "#CBD5E1" 1
Draw-Text $graphics "Leyenda:" $fontLegend "#0F172A" 545 ($legendY + 18) 80 20
Fill-RoundRect $graphics 655 ($legendY + 14) 36 26 5 "#F8FBFF" $blue 1
Draw-Text $graphics "Core generico" $fontLegend "#0F172A" 704 ($legendY + 18) 140 20
Fill-RoundRect $graphics 860 ($legendY + 14) 36 26 5 "#F0FDFA" $teal 1
Draw-Text $graphics "Adapter especifico" $fontLegend "#0F172A" 909 ($legendY + 18) 160 20
Fill-RoundRect $graphics 1090 ($legendY + 14) 36 26 5 "#FBF7FF" $purple 1
Draw-Text $graphics "Evaluacion reusable" $fontLegend "#0F172A" 1139 ($legendY + 18) 170 20

Draw-Text $graphics "IA-GEN queda fuera de esta base. Este diagrama refleja el framework actual: phoenix y agentico_rest dentro de IA-AGENT." $fontFooter "#64748B" 0 1030 $width 24 "Center" "Center"

$outputFullPath = Join-Path (Get-Location) $OutputPath
$outputDir = Split-Path -Parent $outputFullPath
if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

$bitmap.Save($outputFullPath, [System.Drawing.Imaging.ImageFormat]::Png)

$fontTitle.Dispose()
$fontSubtitle.Dispose()
$fontStepTitle.Dispose()
$fontItem.Dispose()
$fontIcon.Dispose()
$fontNumber.Dispose()
$fontTechTitle.Dispose()
$fontTech.Dispose()
$fontLegend.Dispose()
$fontFooter.Dispose()
$graphics.Dispose()
$bitmap.Dispose()

Write-Output $outputFullPath
