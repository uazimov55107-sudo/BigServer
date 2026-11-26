#!/usr/bin/env python3
import json
import os
import platform
import shutil
import socket
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = 8829
ROOT = os.path.expanduser("~/BigServer")
VIDEO_NAME = 'Tурецкий клубняк.mp4'

PAGE = r"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BigServer | Boshqaruv markazi</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b1020;color:#e8eefc;font:16px system-ui,sans-serif}
header{padding:25px 5%;background:#121a30;border-bottom:1px solid #263653}
h1{margin:0;font-size:27px} header p{color:#9fb0d0;margin-bottom:0}
main{max-width:1100px;margin:25px auto;padding:0 18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:15px}
.card{background:#141e34;border:1px solid #2a3a59;border-radius:14px;padding:20px}
.label{color:#a8b7d4;font-size:14px}.value{font-size:25px;font-weight:700;margin-top:9px;overflow-wrap:anywhere}
.ok{color:#6ee7a2}.muted{color:#a8b7d4}
section{margin-top:20px}
code{color:#8ee8ff}footer{padding:25px;text-align:center;color:#8293b4}
</style>
</head>
<body>
<header>
<h1>BigServer</h1>
<p>Debian Linux · Shaxsiy server boshqaruv markazi</p>
</header>
<main>
<section class="grid">
<div class="card"><div class="label">Server holati</div><div class="value ok" id="state">Tekshirilmoqda...</div></div>
<div class="card"><div class="label">Operatsion tizim</div><div class="value" id="os">...</div></div>
<div class="card"><div class="label">Protsessor</div><div class="value" id="cpu">...</div></div>
<div class="card"><div class="label">RAM (taxminiy)</div><div class="value" id="ram">...</div></div>
<div class="card"><div class="label">Disk bo‘sh joyi</div><div class="value" id="disk">...</div></div>
<div class="card"><div class="label">Server vaqti</div><div class="value" id="time">...</div></div>
</section>0
<section class="card">
<h2>Server haqida</h2>
<p class="muted">Ishchi papka: <code id="root">...</code></p>
<p class="muted">Manzil: <code>http://127.0.0.1:8829</code></p>
<p id="updated" class="muted">Ma'lumotlar olinmoqda...</p>
</section>

<section class="card">
<h2>🎬 Bizning video</h2>
<video controls autoplay muted playsinline
style="width:100%;max-height:600px;border-radius:12px;background:#000">
<source src="/video" type="video/mp4">
Brauzeringiz video formatini qo‘llamaydi.
</video>
</section>
</main>
<footer>BigServer · Python standart kutubxonalari asosida</footer>
<script>
async function refresh(){
 try{
  const r=await fetch('/api/status');
  if(!r.ok)throw Error('HTTP '+r.status);
  const d=await r.json();
  for(const k of ['state','os','cpu','ram','disk','time','root'])
    document.getElementById(k).textContent=d[k];
  document.getElementById('updated').textContent='Oxirgi yangilanish: '+new Date().toLocaleTimeString();
 }catch(e){document.getElementById('state').textContent='Ulanish xatosi'}
}
refresh();setInterval(refresh,5000);
</script>
</body></html>"""

def get_status():
    mem = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mem[parts[0].rstrip(":")] = int(parts[1])
        total = mem.get("MemTotal", 0)
        available = mem.get("MemAvailable", mem.get("MemFree", 0))
        ram = f"{(total-available)/1048576:.1f} / {total/1048576:.1f} GB"
    except (OSError, ValueError):
        ram = "Ma'lumot mavjud emas"

    try:
        cpu = str(os.cpu_count() or "Noma'lum") + " yadro"
    except OSError:
        cpu = "Noma'lum"

    disk = shutil.disk_usage(ROOT)
    return {
        "state": "Ishlayapti",
        "os": platform.system() + " " + platform.release(),
        "cpu": cpu,
        "ram": ram,
        "disk": f"{disk.free / 1073741824:.1f} GB bo'sh",
        "time": datetime.now().astimezone().strftime("%H:%M:%S"),
        "root": ROOT,
    }

class Handler(BaseHTTPRequestHandler):
    def send_body(self, body, content_type):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self.send_body(PAGE, "text/html")

        elif self.path == "/video":
            video_path = os.path.join(ROOT, "storage", "hammasi", VIDEO_NAME)
            try:
                size = os.path.getsize(video_path)
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(video_path, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
            except OSError:
                self.send_error(404, "Video topilmadi")
        elif self.path == "/api/status":
            self.send_body(json.dumps(get_status(), ensure_ascii=False), "application/json")
        elif self.path == "/health":
            self.send_body('{"status":"ok"}', "application/json")
        else:
            self.send_error(404, "Sahifa topilmadi")

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

if __name__ == "__main__":
    print("BigServer ishga tushmoqda...")
    print(f"Manzil: http://{HOST}:{PORT}")
    print("To'xtatish uchun Ctrl+C bosing.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

