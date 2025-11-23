import subprocess, json, requests, os

def http_get(base, path):
    r = requests.get(base.rstrip("/") + path, timeout=10)
    return r.status_code, r.headers, r.text

def http_post(base, path, json_body):
    r = requests.post(base.rstrip("/") + path, json=json_body, timeout=10)
    return r.status_code, r.headers, r.text

def sh(cmd: str):
    # uso restringido
    allowed = ("curl", "docker", "docker compose")
    if not cmd.split()[0] in [a.split()[0] for a in allowed]:
        raise ValueError("comando no permitido")
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr
