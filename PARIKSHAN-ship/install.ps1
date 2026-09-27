<#
.SYNOPSIS
    One-shot installer for PARIKSHAN. Creates the virtualenv, installs every
    dependency, regenerates the full data/model/artifact pipeline from
    scratch, and runs the test suite - everything a fresh checkout needs to
    go from "just cloned" to "dashboard works" with real numbers, since
    data/ and artifacts/ are gitignored and regenerated locally (see
    .gitignore and README.md).

.DESCRIPTION
    Core install (always runs):
      1. Check for Python 3.11+; install it via winget if missing.
      2. Create the virtualenv at -VenvPath (default C:\dev\paimana-venv),
         deliberately OUTSIDE this project folder - if this folder is inside
         a cloud-sync directory (Google Drive/OneDrive/Dropbox), the sync
         daemon can lock files and corrupt site-packages mid-install.
         Warns if it detects that.
      3. Install requirements.txt.
      4. Run the full pipeline in dependency order: generate -> validate ->
         features -> split-check -> baselines -> ML bake-off -> risk
         scoring -> alert backtest -> dashboard precompute.
      5. Run the test suite (skip with -SkipTests).

    Optional LLM Assistant extras (-WithAssistant):
      6. Install requirements-assistant.txt, then force the CPU-only torch
         build (the default PyPI wheel conflicts with numpy/pandas on some
         Windows machines - see LICENSES.md and HANDOFF.md Phase 7).
      7. Install Ollama via winget if missing, start its background
         service, and pull qwen2.5:7b-instruct (~4.7GB download).
      8. Build the project-narrative search index.

    Every step is verified before moving on (not assumed) and prints its
    real output. A failure in the optional Assistant extras does not fail
    the core install - the dashboard and every metric work fully without
    it; the Assistant screen just falls back to a deterministic template.

.PARAMETER WithAssistant
    Also install the offline LLM Assistant (Ollama + Qwen2.5-7B-Instruct +
    MiniLM embeddings). Skippable - everything else works without it.

.PARAMETER VenvPath
    Where to create the virtualenv. Default: C:\dev\paimana-venv.

.PARAMETER SkipTests
    Skip the full pytest run at the end (it takes ~10-15 minutes).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1 -WithAssistant
#>

param(
    [switch]$WithAssistant,
    [string]$VenvPath = "C:\dev\paimana-venv",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "    OK: $Message" -ForegroundColor Green
}

function Write-Warn2 {
    param([string]$Message)
    Write-Host "    WARNING: $Message" -ForegroundColor Yellow
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-OllamaExe {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $candidate) { return $candidate }
    return $null
}

# --------------------------------------------------------------------------
# 0. Sanity: are we in the right place?
# --------------------------------------------------------------------------
Write-Step "PARIKSHAN installer starting"
Write-Host "    Project root: $ProjectRoot"

if (-not (Test-Path (Join-Path $ProjectRoot "requirements.txt"))) {
    Write-Host "requirements.txt not found next to install.ps1 - run this script from inside the cloned project." -ForegroundColor Red
    exit 1
}

if ($ProjectRoot -match "Google Drive|OneDrive|Dropbox|iCloudDrive") {
    Write-Warn2 "This project folder looks like it's inside a cloud-sync directory."
    Write-Warn2 "The virtualenv will be created OUTSIDE it at '$VenvPath' to avoid sync-lock corruption."
}

# --------------------------------------------------------------------------
# 1. Python
# --------------------------------------------------------------------------
Write-Step "Checking for Python"

if (-not (Test-CommandExists "python")) {
    Write-Warn2 "Python not found."
    if (Test-CommandExists "winget") {
        Write-Host "    Installing Python via winget..."
        winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        Write-Warn2 "Python was just installed. PowerShell needs a fresh session to see it on PATH."
        Write-Warn2 "Close this window, open a new PowerShell, and re-run install.ps1."
        exit 1
    } else {
        Write-Host "winget is not available and Python is missing. Install Python 3.11+ from https://python.org, then re-run this script." -ForegroundColor Red
        exit 1
    }
}
$pyVersion = & python --version 2>&1
Write-Ok "$pyVersion found"

# --------------------------------------------------------------------------
# 2. Virtualenv
# --------------------------------------------------------------------------
Write-Step "Setting up the virtualenv at $VenvPath"

if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
    if (-not (Test-Path $VenvPath)) {
        Write-Host "Failed to create the virtualenv at $VenvPath." -ForegroundColor Red
        exit 1
    }
    Write-Ok "Created"
} else {
    Write-Ok "Already exists - reusing"
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$VenvPip = Join-Path $VenvPath "Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtualenv at $VenvPath looks broken (no python.exe inside). Delete it and re-run this script." -ForegroundColor Red
    exit 1
}

# --------------------------------------------------------------------------
# 3. Core dependencies
# --------------------------------------------------------------------------
Write-Step "Installing core dependencies (requirements.txt)"
# Upgrading pip via "pip install --upgrade pip" fails on Windows -- pip.exe
# can't overwrite its own running executable in place. Found by actually
# running this script end-to-end against a fresh venv (it printed "ERROR:
# To modify pip, please run ... python -m pip install --upgrade pip" and
# limped on non-fatally). Invoking through python -m pip avoids that.
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPip install -r (Join-Path $ProjectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip install -r requirements.txt failed - see output above." -ForegroundColor Red
    exit 1
}
Write-Ok "Core dependencies installed"

# --------------------------------------------------------------------------
# 4. Full pipeline, in dependency order (data/ and artifacts/ are
#    gitignored - a fresh checkout has none of this and must regenerate it)
# --------------------------------------------------------------------------
$PipelineSteps = @(
    @{ Script = "run_generate.py";       Label = "Generating the synthetic panel dataset" }
    @{ Script = "run_validate.py";       Label = "Validating against calibration anchors" }
    @{ Script = "run_features.py";       Label = "Building leakage-safe features" }
    @{ Script = "run_split_check.py";    Label = "Checking train/test splits for leakage" }
    @{ Script = "run_baselines.py";      Label = "Fitting conventional statistical baselines" }
    @{ Script = "run_models.py";         Label = "Training ML models + bake-off + SHAP (this one takes a while)" }
    @{ Script = "run_risk.py";           Label = "Computing risk scores and alerts" }
    @{ Script = "run_alert_backtest.py"; Label = "Running the early-warning lead-time backtest" }
    @{ Script = "run_dashboard_data.py"; Label = "Precomputing dashboard artifacts (quantiles, PR curves)" }
)

Write-Step "Running the full data/model pipeline ($($PipelineSteps.Count) steps - some take several minutes)"
foreach ($step in $PipelineSteps) {
    $scriptPath = Join-Path $ProjectRoot "scripts\$($step.Script)"
    if (-not (Test-Path $scriptPath)) {
        Write-Host "Expected script not found: $scriptPath" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
    Write-Host "    -> $($step.Label) [$($step.Script)]" -ForegroundColor DarkCyan
    & $VenvPython $scriptPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "$($step.Script) failed (exit code $LASTEXITCODE) - see output above. Fix the issue and re-run install.ps1 (already-completed steps are cheap to redo)." -ForegroundColor Red
        exit 1
    }
}
Write-Ok "Full pipeline completed"

# --------------------------------------------------------------------------
# 5. Test suite
# --------------------------------------------------------------------------
if (-not $SkipTests) {
    Write-Step "Running the test suite (python -m pytest -q) - this takes roughly 10-15 minutes"
    & $VenvPython -m pytest -q (Join-Path $ProjectRoot "tests")
    if ($LASTEXITCODE -ne 0) {
        Write-Warn2 "Some tests failed (exit code $LASTEXITCODE) - see output above. The dashboard may still work; investigate before treating the install as verified."
    } else {
        Write-Ok "Full test suite passed"
    }
} else {
    Write-Warn2 "Skipped tests (-SkipTests was passed)"
}

Write-Step "Core install complete"
Write-Host "    Launch the dashboard with:"
Write-Host "        & `"$VenvPython`" -m streamlit run `"$ProjectRoot\src\paimana\app\Home.py`"" -ForegroundColor White

# --------------------------------------------------------------------------
# 6. Optional: LLM Assistant extras (Phase 7 - droppable)
# --------------------------------------------------------------------------
if ($WithAssistant) {
    Write-Step "Installing LLM Assistant extras (-WithAssistant)"

    & $VenvPip install -r (Join-Path $ProjectRoot "requirements-assistant.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Warn2 "requirements-assistant.txt install failed - the Assistant screen will fall back to rule-based routing only. Core system is unaffected."
    } else {
        Write-Ok "requirements-assistant.txt installed"

        Write-Host "    Forcing the CPU-only torch build (see LICENSES.md for why this matters on Windows)..."
        & $VenvPip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps --quiet
        if ($LASTEXITCODE -ne 0) {
            Write-Warn2 "CPU-only torch install failed - semantic (MiniLM) routing may not work, but rule-based routing and the Ollama narration still will."
        } else {
            Write-Ok "torch (CPU-only build) installed"
        }
    }

    Write-Step "Checking for Ollama"
    $ollamaExe = Get-OllamaExe
    if (-not $ollamaExe) {
        if (Test-CommandExists "winget") {
            Write-Host "    Ollama not found - installing via winget..."
            winget install --id Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements
            Start-Sleep -Seconds 3
            $ollamaExe = Get-OllamaExe
        }
        if (-not $ollamaExe) {
            Write-Warn2 "Could not install or locate Ollama. Install it manually from https://ollama.com/download, then run:"
            Write-Warn2 "    ollama pull qwen2.5:7b-instruct"
            Write-Warn2 "    python scripts/run_assistant_index.py"
            Write-Warn2 "The Assistant screen works without Ollama - it just always uses the deterministic fallback template."
            $ollamaExe = $null
        } else {
            Write-Ok "Ollama installed at $ollamaExe"
        }
    } else {
        Write-Ok "Ollama found at $ollamaExe"
    }

    if ($ollamaExe) {
        Write-Step "Ensuring the Ollama background service is running"
        $ollamaUp = $false
        try {
            Invoke-WebRequest -Uri "http://localhost:11434/api/version" -TimeoutSec 2 -UseBasicParsing | Out-Null
            $ollamaUp = $true
        } catch {
            $ollamaUp = $false
        }
        if (-not $ollamaUp) {
            Write-Host "    Starting 'ollama serve' in the background..."
            Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 5
            try {
                Invoke-WebRequest -Uri "http://localhost:11434/api/version" -TimeoutSec 5 -UseBasicParsing | Out-Null
                $ollamaUp = $true
            } catch {
                $ollamaUp = $false
            }
        }

        if ($ollamaUp) {
            Write-Ok "Ollama is serving"
            Write-Step "Pulling qwen2.5:7b-instruct (Apache-2.0, ~4.7GB - this may take a while)"
            & $ollamaExe pull qwen2.5:7b-instruct
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "Model pulled"
            } else {
                Write-Warn2 "Model pull failed - the Assistant will use the deterministic fallback until you run 'ollama pull qwen2.5:7b-instruct' yourself."
            }
        } else {
            Write-Warn2 "Could not confirm Ollama is serving on localhost:11434 - skipping the model pull. Start it manually with 'ollama serve' and then run 'ollama pull qwen2.5:7b-instruct'."
        }
    }

    Write-Step "Building the project-narrative search index"
    & $VenvPython (Join-Path $ProjectRoot "scripts\run_assistant_index.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Warn2 "run_assistant_index.py failed - narrative-based project search will be unavailable, but rule-based and Ollama-narrated answers still work."
    } else {
        Write-Ok "Narrative search index built"
    }

    Write-Step "LLM Assistant extras done"
}

Write-Host ""
Write-Host "=== Install complete ===" -ForegroundColor Green
Write-Host "Run the dashboard:"
Write-Host "    & `"$VenvPython`" -m streamlit run `"$ProjectRoot\src\paimana\app\Home.py`"" -ForegroundColor White
if (-not $WithAssistant) {
    Write-Host ""
    Write-Host "To add the offline LLM Assistant later, re-run:" -ForegroundColor DarkGray
    Write-Host "    powershell -ExecutionPolicy Bypass -File install.ps1 -WithAssistant" -ForegroundColor DarkGray
}
