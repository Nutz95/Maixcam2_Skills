param(
    [string]$DeviceHost = "10.17.43.1",
    [string]$User = "root",
    [int]$Port = 22,
    [string]$RemoteSkillDir = "/root/.picoclaw/workspace/skills/vlm-daemon",
    [string]$TestImagePath = "/maixapp/share/picture/2024.1.1/ssd_car.jpg"
)

$ErrorActionPreference = "Stop"

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Assert-Command -Name "ssh"

$remotePy = @"
import json
import subprocess
import sys
import time
import urllib.request

BASE = 'http://127.0.0.1:18080'
IMG = '__TEST_IMAGE_PATH__'
MODELS = ['qwen3vl', 'internvl', 'smolvlm']


def emit(kind, **data):
    payload = {'kind': kind}
    payload.update(data)
    print('__VLM_JSON__' + json.dumps(payload, ensure_ascii=False), flush=True)


def run(cmd):
    r = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode('utf-8'))


def stop_daemon_with_log():
    emit('phase', message='Stopping daemon (end of test)')
    src, sout, serr = run('cd __REMOTE_SKILL_DIR__; ./stop_daemon.sh >/dev/null 2>&1 || true')
    emit('daemon_stop', rc=src, out=sout, err=serr)


emit('phase', message='Stopping daemon')
run('cd __REMOTE_SKILL_DIR__; ./stop_daemon.sh >/dev/null 2>&1 || true')
emit('phase', message='Starting daemon')
rc, out, err = run('cd __REMOTE_SKILL_DIR__; ./start_daemon.sh')
emit('daemon_start', rc=rc, out=out, err=err)

if rc != 0:
    result = {
        'ok': False,
        'error': 'daemon_start_failed',
        'models': [],
    }
    stop_daemon_with_log()
    print('__VLM_RESULT__' + json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(1)

emit('phase', message='Waiting for /health')
h = None
for _ in range(30):
    try:
        h = get('/health')
        break
    except Exception:
        emit('health_wait', attempt=_ + 1)
        time.sleep(1)

if h is None:
    result = {
        'ok': False,
        'error': 'daemon_health_not_reachable',
        'models': [],
    }
    stop_daemon_with_log()
    print('__VLM_RESULT__' + json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(1)

emit('health_ok', status=h.get('status'), autoload=h.get('autoload', {}))

results = []
overall_ok = True

for m in MODELS:
    model_start = time.time()
    emit('model_start', model=m)
    rec = {
        'model': m,
        'load_ok': False,
        'ask_ok': False,
        'ok': False,
        'backend': None,
        'answer': '',
        'error': None,
        'duration_s': 0.0,
    }

    emit('load_start', model=m)
    try:
        load = post('/models/load', {'model': m})
        rec['load_ok'] = bool(load.get('ok'))
        if not rec['load_ok']:
            rec['error'] = 'load_not_ok'
        emit('load_done', model=m, ok=rec['load_ok'])
    except Exception as e:
        rec['error'] = 'load_exception: ' + repr(e)
        emit('load_done', model=m, ok=False, error=rec['error'])

    if rec['load_ok']:
        emit('ask_start', model=m)
        try:
            ask = post('/ask', {
                'question': 'Describe the picture in one sentence.',
                'capture_new': False,
                'image_path': IMG,
            })
            ans = str(ask.get('answer', '') or '')
            rec['backend'] = ask.get('backend')
            rec['answer'] = ans
            rec['ask_ok'] = bool(ans.strip())
            if not rec['ask_ok']:
                rec['error'] = 'empty_answer'
            emit('ask_done', model=m, ok=rec['ask_ok'], backend=rec['backend'], answer_len=len(ans))
        except Exception as e:
            rec['error'] = 'ask_exception: ' + repr(e)
            emit('ask_done', model=m, ok=False, error=rec['error'])

    rec['duration_s'] = round(time.time() - model_start, 2)
    rec['ok'] = bool(rec['load_ok'] and rec['ask_ok'])
    overall_ok = overall_ok and rec['ok']
    results.append(rec)
    emit('model_done', model=m, ok=rec['ok'], duration_s=rec['duration_s'])

emit('phase', message='Fetching final /models state')
final_models = None
final_models_error = None
try:
    final_models = get('/models')
except Exception as e:
    final_models_error = repr(e)

result = {
    'ok': overall_ok,
    'health': h,
    'models': results,
    'final_models': final_models,
    'final_models_error': final_models_error,
}
stop_daemon_with_log()
print('__VLM_RESULT__' + json.dumps(result, ensure_ascii=False), flush=True)
sys.exit(0 if overall_ok else 1)
"@

$remotePy = $remotePy.Replace("__TEST_IMAGE_PATH__", $TestImagePath.Replace("'", "\\'"))
$remotePy = $remotePy.Replace("__REMOTE_SKILL_DIR__", $RemoteSkillDir.Replace("'", "\\'"))

Write-Host "Running VLM all-model switch test on $User@$DeviceHost ..."
$sshArgs = @(
    "-p", $Port,
    "-o", "StrictHostKeyChecking=accept-new",
    "$User@$DeviceHost",
    "/usr/local/bin/python3 -"
)

$resultJson = $null

$remotePy | ssh @sshArgs 2>&1 | ForEach-Object {
    $line = $_.ToString()

    if ($line.StartsWith("__VLM_JSON__")) {
        $payload = $line.Substring("__VLM_JSON__".Length)
        try {
            $evt = $payload | ConvertFrom-Json
        }
        catch {
            Write-Host $line -ForegroundColor DarkGray
            return
        }

        switch ($evt.kind) {
            "phase" {
                Write-Host ("[STEP] " + $evt.message) -ForegroundColor Cyan
            }
            "daemon_start" {
                $c = if ([int]$evt.rc -eq 0) { "Green" } else { "Red" }
                Write-Host ("[DAEMON] start rc=" + $evt.rc) -ForegroundColor $c
                if ($evt.out) { Write-Host ("[DAEMON] " + $evt.out) -ForegroundColor DarkGray }
                if ($evt.err) { Write-Host ("[DAEMON][stderr] " + $evt.err) -ForegroundColor Yellow }
            }
            "daemon_stop" {
                $c = if ([int]$evt.rc -eq 0) { "Green" } else { "Yellow" }
                Write-Host ("[DAEMON] stop rc=" + $evt.rc) -ForegroundColor $c
                if ($evt.out) { Write-Host ("[DAEMON] " + $evt.out) -ForegroundColor DarkGray }
                if ($evt.err) { Write-Host ("[DAEMON][stderr] " + $evt.err) -ForegroundColor Yellow }
            }
            "health_wait" {
                Write-Host ("[WAIT] health attempt " + $evt.attempt + "/30") -ForegroundColor Yellow
            }
            "health_ok" {
                Write-Host ("[HEALTH] status=" + $evt.status) -ForegroundColor Green
            }
            "model_start" {
                Write-Host ("[MODEL] " + $evt.model + " started") -ForegroundColor Magenta
            }
            "load_start" {
                Write-Host ("[LOAD] " + $evt.model + "...") -ForegroundColor DarkMagenta
            }
            "load_done" {
                $ok = [bool]$evt.ok
                $c = if ($ok) { "Green" } else { "Red" }
                Write-Host ("[LOAD] " + $evt.model + " => " + ($(if ($ok) { "OK" } else { "FAIL" }))) -ForegroundColor $c
                if ($evt.error) { Write-Host ("[LOAD][ERR] " + $evt.error) -ForegroundColor Red }
            }
            "ask_start" {
                Write-Host ("[ASK] " + $evt.model + "...") -ForegroundColor DarkMagenta
            }
            "ask_done" {
                $ok = [bool]$evt.ok
                $c = if ($ok) { "Green" } else { "Red" }
                $backend = if ($evt.backend) { $evt.backend } else { "-" }
                Write-Host ("[ASK] " + $evt.model + " => " + ($(if ($ok) { "OK" } else { "FAIL" })) + " (backend=" + $backend + ", len=" + $evt.answer_len + ")") -ForegroundColor $c
                if ($evt.error) { Write-Host ("[ASK][ERR] " + $evt.error) -ForegroundColor Red }
            }
            "model_done" {
                $ok = [bool]$evt.ok
                $c = if ($ok) { "Green" } else { "Red" }
                Write-Host ("[MODEL] " + $evt.model + " done in " + $evt.duration_s + "s => " + ($(if ($ok) { "PASS" } else { "FAIL" }))) -ForegroundColor $c
            }
            default {
                Write-Host $line -ForegroundColor DarkGray
            }
        }

        return
    }

    if ($line.StartsWith("__VLM_RESULT__")) {
        $resultJson = $line.Substring("__VLM_RESULT__".Length)
        return
    }

    Write-Host $line -ForegroundColor DarkGray
}

$remoteExit = $LASTEXITCODE

if (-not $resultJson) {
    throw "Remote test did not return structured report."
}

$result = $resultJson | ConvertFrom-Json

Write-Host ""
Write-Host "=== VLM FINAL REPORT ===" -ForegroundColor Cyan

if ($result.models) {
    foreach ($m in $result.models) {
        $isOk = [bool]$m.ok
        $status = if ($isOk) { "PASS" } else { "FAIL" }
        $color = if ($isOk) { "Green" } else { "Red" }
        $backend = if ($m.backend) { [string]$m.backend } else { "-" }
        $answer = if ($m.answer) { ([string]$m.answer).Trim() } else { "<empty>" }

        Write-Host (("[{0}] {1}  backend={2}  load={3}  ask={4}  duration={5}s" -f $status, $m.model, $backend, $m.load_ok, $m.ask_ok, $m.duration_s)) -ForegroundColor $color
        Write-Host ("  response: " + $answer) -ForegroundColor White
        if ($m.error) {
            Write-Host ("  error: " + $m.error) -ForegroundColor Yellow
        }
    }
}

if ($result.final_models_error) {
    Write-Host ("Final /models fetch error: " + $result.final_models_error) -ForegroundColor Yellow
}

$overallOk = [bool]$result.ok
$overallColor = if ($overallOk) { "Green" } else { "Red" }
Write-Host ""
Write-Host ("OVERALL: " + ($(if ($overallOk) { "PASS" } else { "FAIL" }))) -ForegroundColor $overallColor

if ($remoteExit -ne 0 -or -not $overallOk) {
    throw "Remote test failed."
}

Write-Host "VLM all-model switch test completed."
