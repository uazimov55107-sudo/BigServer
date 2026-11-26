from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
import json
import os
import secrets
import shlex
import subprocess
import threading
import html

BASE = (Path.home() / "BigServer" / "storage" / "hammasi").resolve()
HOST = "0.0.0.0"
PORT = 8831
VIDEO_FILE = 'Tурецкий клубняк.mp4'
PASSWORD_FILE = Path.home() / "BigServer" / ".web_password"
TOKEN = secrets.token_urlsafe(32)
PASSWORD = secrets.token_urlsafe(12)

if not PASSWORD_FILE.exists():
    PASSWORD_FILE.write_text(PASSWORD, encoding="utf-8")
    PASSWORD_FILE.chmod(0o600)
else:
    PASSWORD = PASSWORD_FILE.read_text(encoding="utf-8").strip()

PAGE = r"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BigServer Web IDE</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#1e1e1e;color:#ddd;font:14px Arial}
header{background:#252526;padding:14px 18px;border-bottom:1px solid #444}
header b{color:#4fc1ff;font-size:18px}.layout{display:grid;grid-template-columns:250px 1fr;height:calc(100vh - 52px)}
aside{background:#252526;border-right:1px solid #444;overflow:auto;padding:12px}
main{display:flex;flex-direction:column;min-width:0}
h3{font-size:12px;color:#aaa;margin:5px 0 12px}
button{background:#0e639c;color:white;border:0;padding:9px 12px;cursor:pointer;border-radius:3px}
button:hover{background:#1177bb}input{background:#333;color:#fff;border:1px solid #555;padding:9px}
#files button{display:block;width:100%;text-align:left;background:transparent;color:#ddd;padding:7px;overflow-wrap:anywhere}
#files button:hover{background:#37373d}#path{color:#9cdcfe;padding:12px;border-bottom:1px solid #444}
#viewer{display:block;width:100%;flex:1;min-height:220px;resize:none;padding:15px;background:#1e1e1e;color:#d4d4d4;border:0;outline:none;white-space:pre;overflow:auto;font:13px/1.6 monospace;tab-size:4}#editbar{display:flex;gap:8px;flex-wrap:wrap;padding:8px;background:#252526;border-bottom:1px solid #444}#editbar input{flex:1;min-width:100px}
#terminal{height:230px;display:flex;flex-direction:column;background:#111;border-top:1px solid #555}
#termout{flex:1;overflow:auto;padding:10px;white-space:pre-wrap;font:13px/1.5 monospace;color:#d4d4d4}
#termform{display:flex;gap:8px;padding:8px}#cmd{flex:1;min-width:0}
#login{position:fixed;inset:0;background:#111e;display:flex;align-items:center;justify-content:center}
#loginbox{background:#252526;padding:25px;border:1px solid #555;width:min(360px,90vw)}
#loginbox input{width:100%;margin:10px 0}#msg{color:#f48771}
@media(max-width:650px){.layout{grid-template-columns:135px 1fr}#terminal{height:200px}aside{padding:6px}}
@keyframes introZoom{from{transform:scale(1.08)}to{transform:scale(1)}}@keyframes introTitle{from{opacity:.55}to{opacity:1;text-shadow:0 0 18px #0e639c}}@keyframes introFade{from{opacity:0}to{opacity:1}}</style></head>
<body>
<header><b>BigServer</b> / Web IDE <button onclick="openBotPanel()" style="float:right">🎵 MusiQ AI</button><span style="float:right;color:#aaa;padding:8px">LAN · 8831</span></header>

<section id="first-video" style="position:fixed;inset:0;z-index:9999;display:flex;flex-direction:column;justify-content:center;padding:20px;background:#050505;animation:introFade .8s ease">
<h2 style="margin:0 0 16px;text-align:center;color:#4fc1ff;animation:introTitle 1.5s infinite alternate">1-VIDEO</h2>
<video controls autoplay muted playsinline preload="auto"
style="display:block;width:100%;height:75vh;object-fit:contain;background:#000;border-radius:12px;animation:introZoom 15s ease">
<source src="/video" type="video/mp4">
Brauzeringiz videoni qo‘llamaydi.
</video>
</section>
<div class="layout" id="ide-layout" style="display:none">
<aside><h3>EXPLORER — HAMMASI</h3><button onclick="loadFiles('')">⟳ Yangilash</button><div id="files"></div></aside>
<main><div id="path">Fayl tanlang...</div><div id="editbar"><button onclick="newFile()">＋ Yangi fayl</button><button onclick="saveFile()">💾 Saqlash</button><button onclick="runPython()">▶ Python Run</button><span id="saveinfo" style="padding:8px;color:#9cdcfe"></span></div><textarea id="viewer" spellcheck="false" autocapitalize="off" autocomplete="off" placeholder="Kod yozishni boshlang..."></textarea>
<div id="terminal"><div style="padding:8px;color:#aaa;border-bottom:1px solid #333">TERMINAL — faqat xavfsiz, o‘qish buyruqlari</div>
<div id="termout">BigServer Web IDE tayyor.
Buyruqlar: pwd, ls, cat, head, tail, wc, du, file
Misol: ls -la</div>
<form id="termform"><span style="padding:8px 0;color:#4fc1ff">&gt;</span><input id="cmd" autocomplete="off" placeholder="Buyruq kiriting: ls -la"><button>Run</button></form>
</div></main></div>
<div id="login"><div id="loginbox"><h2>BigServer kirish</h2><p>Sayt terminaliga kirish uchun parolni kiriting.</p>
<form id="loginform"><input id="pw" type="password" placeholder="Parol" required><button>Kirish</button></form><p id="msg"></p></div></div>

<div id="botpanel" style="display:none;position:fixed;inset:5%;z-index:10000;background:#151b28;color:white;border:1px solid #4fc1ff;border-radius:14px;padding:20px;overflow:auto">
  <button onclick="closeBotPanel()" style="float:right">✕ Yopish</button>
  <h2>🎵 MusiQ AI boshqaruvi</h2>
  <p>Bot holati: <b id="botstatus">Tekshirilmoqda...</b></p>
  <button onclick="refreshBot()">⟳ Holatni yangilash</button>
  <button onclick="restartBot()" style="background:#a15c13">↻ Botni qayta ishga tushirish</button>
  <h3>Oxirgi loglar</h3>
  <pre id="botlogs" style="white-space:pre-wrap;overflow-wrap:anywhere;background:#080d16;padding:12px;border-radius:8px;max-height:55vh;overflow:auto">Loglar yuklanmoqda...</pre>
  <p id="botmessage"></p>
</div>
<script>
let current=''; let openedFile='';
async function api(url,opts={}) {
 let r=await fetch(url,opts);
 if(r.status===401){document.getElementById('login').style.display='flex';throw Error('Qayta kiring');}
 if(!r.ok)throw Error(await r.text());
 return r.json();
}
document.getElementById('loginform').onsubmit=async e=>{
 e.preventDefault();
 try{await api('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:document.getElementById('pw').value})});
 document.getElementById('login').style.display='none';loadFiles('');}
 catch(err){document.getElementById('msg').textContent='Parol xato yoki ulanishda muammo.';}
};
async function loadFiles(path){
 try{
 let d=await api('/api/files?path='+encodeURIComponent(path));current=path;
 document.getElementById('files').innerHTML='';
 if(path){let b=document.createElement('button');b.textContent='📁 ..';b.onclick=()=>loadFiles(path.split('/').slice(0,-1).join('/'));document.getElementById('files').append(b);}
 d.items.forEach(x=>{let b=document.createElement('button');b.textContent=(x.dir?'📁 ':'📄 ')+x.name;b.onclick=()=>x.dir?loadFiles(x.path):readFile(x.path);document.getElementById('files').append(b);});
 document.getElementById('path').textContent='/storage/hammasi/'+path;
 }catch(e){termout(e.message);}
}
async function readFile(path){
 try{let d=await api('/api/read?path='+encodeURIComponent(path));openedFile=path;document.getElementById('path').textContent=path;document.getElementById('viewer').value=d.content;document.getElementById('saveinfo').textContent='';}
 catch(e){termout(e.message);}
}
function termout(s){let o=document.getElementById('termout');o.textContent+='\n'+s;o.scrollTop=o.scrollHeight;}
async function saveFile(){
 if(!openedFile){newFile();return;}
 try{
  await api('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:openedFile,content:document.getElementById('viewer').value})});
  document.getElementById('saveinfo').textContent='Saqlandi ✓';
  loadFiles(current);
 }catch(e){termout('Saqlash xatosi: '+e.message);}
}
async function newFile(){
 let name=prompt('Fayl nomi (masalan main.py yoki index.html):');
 if(!name)return;
 name=name.trim();
 if(!name||name.includes('..')||name.startsWith('/')||name.includes('\\')){alert('Fayl nomini tekshiring.');return;}
 openedFile=current?current+'/'+name:name;
 document.getElementById('path').textContent=openedFile;
 document.getElementById('viewer').value='';
 document.getElementById('saveinfo').textContent='Yangi fayl — Saqlashni bosing';
 document.getElementById('viewer').focus();
}
async function runPython(){
 if(!openedFile){alert('Avval Python faylini oching yoki yangi .py fayl yarating.');return;}
 if(!openedFile.endsWith('.py')){alert('Python Run faqat .py fayllar uchun.');return;}
 try{
  await api('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:openedFile,content:document.getElementById('viewer').value})});
  termout('\\n$ python3 '+openedFile);
  let d=await api('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:openedFile})});
  termout(d.output);
 }catch(e){termout('Ishga tushirish xatosi: '+e.message);}
}
document.getElementById('viewer').addEventListener('keydown',e=>{
 if(e.key==='Tab'){
  e.preventDefault();
  const t=e.target,a=t.selectionStart,b=t.selectionEnd;
  t.setRangeText('    ',a,b,'end');
 }
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();saveFile();}
});
document.getElementById('termform').onsubmit=async e=>{
 e.preventDefault();let c=document.getElementById('cmd'),cmd=c.value.trim();if(!cmd)return;
 termout('\n> '+cmd);c.value='';
 try{let d=await api('/api/terminal',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cmd,cwd:current})});termout(d.output);}
 catch(err){termout('Xato: '+err.message);}
};

async function openBotPanel(){
 document.getElementById('botpanel').style.display='block';
 await refreshBot();
}
function closeBotPanel(){
 document.getElementById('botpanel').style.display='none';
}
async function refreshBot(){
 const status=document.getElementById('botstatus');
 const logs=document.getElementById('botlogs');
 try{
  const d=await api('/api/bot/status');
  status.textContent=d.status;
  status.style.color=d.status==='active'?'#4ade80':'#f87171';
  logs.textContent=d.logs||'Hozircha log yo‘q.';
 }catch(e){
  status.textContent='Tekshirib bo‘lmadi';
  logs.textContent=e.message;
 }
}
async function restartBot(){
 const msg=document.getElementById('botmessage');
 if(!confirm('MusiQ AI bot qayta ishga tushirilsinmi?'))return;
 msg.textContent='Bot qayta ishga tushirilmoqda...';
 try{
  await api('/api/bot/restart',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  msg.textContent='Qayta ishga tushirish buyrug‘i bajarildi.';
  setTimeout(refreshBot,2000);
 }catch(e){msg.textContent='Xato: '+e.message;}
}
setTimeout(() => {
  const intro = document.getElementById('first-video');
  const ide = document.getElementById('ide-layout');
  if (intro) {
    intro.style.position = 'relative';
    intro.style.inset = 'auto';
    intro.style.zIndex = '1';
    intro.style.animation = 'none';
  }
  if (ide) ide.style.display = 'grid';
}, 15000);
</script></body></html>"""

def safe_path(rel):
    p = (BASE / rel).resolve()
    if p != BASE and BASE not in p.parents:
        raise ValueError("Bu papkadan tashqariga chiqish mumkin emas")
    return p

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.client_address[0], fmt % args))

    def send_data(self, data, status=200, content_type="application/json; charset=utf-8", cookie=None):
        raw = data if isinstance(data, bytes) else data.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'")
        if cookie:
            self.send_header("Set-Cookie", "bigserver="+TOKEN+"; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        return ("bigserver="+TOKEN) in self.headers.get("Cookie", "")

    def body(self):
        n = int(self.headers.get("Content-Length", "0"))
        if n > 600000:
            raise ValueError("So'rov juda katta")
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self.send_data(PAGE, content_type="text/html; charset=utf-8")
        if u.path == "/video":
            f = (BASE / VIDEO_FILE).resolve()
            if f.parent != BASE or not f.is_file():
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(f.stat().st_size))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            with f.open("rb") as src:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            return
        if u.path == "/health":
            return self.send_data('{"status":"ok"}')
        if not self.authorized():
            return self.send_data('{"error":"Kirish talab qilinadi"}', 401)
        if u.path == "/api/bot/status":
            status = subprocess.run(
                ["systemctl", "--user", "is-active", "musiq-ai.service"],
                capture_output=True, text=True, timeout=8
            ).stdout.strip()
            logs = subprocess.run(
                ["journalctl", "--user", "-u", "musiq-ai.service",
                 "-n", "30", "--no-pager", "-o", "cat"],
                capture_output=True, text=True, timeout=8
            ).stdout[-9000:]
            return self.send_data(json.dumps(
                {"status": status or "unknown", "logs": logs},
                ensure_ascii=False
            ))
        from urllib.parse import parse_qs
        rel = parse_qs(u.query).get("path", [""])[0]
        try:
            p = safe_path(rel)
            if u.path == "/api/files":
                if not p.is_dir():
                    raise ValueError("Bu papka emas")
                items = []
                for x in sorted(p.iterdir(), key=lambda z: (not z.is_dir(), z.name.lower())):
                    if x.is_symlink():
                        continue
                    items.append({"name": x.name, "dir": x.is_dir(),
                                  "path": str(x.relative_to(BASE))})
                return self.send_data(json.dumps({"items": items}, ensure_ascii=False))
            if u.path == "/api/read":
                if not p.is_file() or p.stat().st_size > 500000:
                    raise ValueError("Fayl mavjud emas yoki 500 KB dan katta")
                data = p.read_bytes()
                try:
                    content = data.decode("utf-8")
                except UnicodeDecodeError:
                    content = "[Bu matnli UTF-8 fayl emas. Hajmi: %d bayt]" % len(data)
                return self.send_data(json.dumps({"content": content}, ensure_ascii=False))
            return self.send_data('{"error":"Topilmadi"}', 404)
        except Exception as e:
            return self.send_data(json.dumps({"error": str(e)}, ensure_ascii=False), 400)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            data = self.body()
            if u.path == "/api/login":
                if secrets.compare_digest(str(data.get("password", "")), PASSWORD):
                    return self.send_data('{"ok":true}', cookie=True)
                return self.send_data('{"error":"Parol xato"}', 401)
            if not self.authorized():
                return self.send_data('{"error":"Kirish talab qilinadi"}', 401)
            if u.path == "/api/bot/restart":
                result = subprocess.run(
                    ["systemctl", "--user", "restart", "musiq-ai.service"],
                    capture_output=True, text=True, timeout=25
                )
                if result.returncode:
                    return self.send_data(json.dumps(
                        {"error": result.stderr or "Botni qayta ishga tushirib bo'lmadi"},
                        ensure_ascii=False
                    ), 500)
                return self.send_data('{"ok":true}')
            if u.path == "/api/save":
                rel = str(data.get("path", ""))
                content = data.get("content", "")
                if not isinstance(content, str) or len(content.encode("utf-8")) > 500000:
                    raise ValueError("Matn 500 KB dan oshmasligi kerak")
                p = safe_path(rel)
                if not p.name or not p.parent.is_dir():
                    raise ValueError("Fayl nomi yoki papka noto'g'ri")
                if p.exists() and (not p.is_file() or p.is_symlink()):
                    raise ValueError("Bu oddiy fayl emas")
                p.write_text(content, encoding="utf-8")
                return self.send_data('{"ok":true}')

            if u.path == "/api/run":
                p = safe_path(str(data.get("path", "")))
                if p.suffix != ".py" or not p.is_file() or p.is_symlink():
                    raise ValueError("Mavjud .py faylni tanlang")
                result = subprocess.run(
                    ["python3", str(p)], cwd=p.parent,
                    capture_output=True, text=True, timeout=15,
                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                         "HOME": str(BASE)}
                )
                out = (result.stdout + result.stderr)[:12000]
                return self.send_data(json.dumps(
                    {"output": out or "(natija yo'q)", "returncode": result.returncode},
                    ensure_ascii=False
                ))

            if u.path != "/api/terminal":
                return self.send_data('{"error":"Topilmadi"}', 404)

            parts = shlex.split(str(data.get("cmd", "")))
            if not parts:
                return self.send_data('{"output":""}')
            allowed = {"pwd", "ls", "cat", "head", "tail", "wc", "du", "file", "python3", "python"}
            if parts[0] not in allowed:
                raise ValueError("Faqat pwd, ls, cat, head, tail, wc, du, file buyruqlari mumkin")
            if parts[0] not in {"python3", "python"} and any(x in str(data.get("cmd", "")) for x in (";", "|", "&", "$", "`", ">", "<")):
                raise ValueError("Bir vaqtda bir nechta buyruq yoki shell operatorlari taqiqlangan")
            cwd = safe_path(str(data.get("cwd", "")))
            if not cwd.is_dir():
                cwd = BASE
            if parts[0] in {"python3", "python"}:
                result = subprocess.run(
                    parts, cwd=cwd, capture_output=True, text=True,
                    timeout=10,
                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                         "HOME": str(BASE)}
                )
                out = (result.stdout + result.stderr)[:12000]
                return self.send_data(json.dumps(
                    {"output": out or "(natija yo'q)"}, ensure_ascii=False
                ))

            args = []
            for a in parts[1:]:
                if a.startswith("-") or a.isdigit():
                    args.append(a)
                    continue
                if ".." in Path(a).parts or Path(a).is_absolute():
                    raise ValueError("Faqat loyiha ichidagi nisbiy yo'llardan foydalaning")
                q = (cwd / a).resolve()
                if q != BASE and BASE not in q.parents:
                    raise ValueError("Loyiha papkasidan tashqariga chiqish mumkin emas")
                args.append(str(q))
            result = subprocess.run(parts[:1] + args, cwd=cwd, capture_output=True,
                                    text=True, timeout=5, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                                                               "HOME": str(BASE)})
            out = (result.stdout + result.stderr)[:12000]
            return self.send_data(json.dumps({"output": out or "(natija yo'q)"}, ensure_ascii=False))
        except subprocess.TimeoutExpired:
            return self.send_data('{"output":"Buyruq vaqt chegarasidan oshdi"}', 400)
        except Exception as e:
            return self.send_data(json.dumps({"output":"Xato: "+str(e)}, ensure_ascii=False), 400)

if __name__ == "__main__":
    BASE.mkdir(parents=True, exist_ok=True)
    print("BigServer Web IDE ishga tushmoqda")
    print("Papka:", BASE)
    print("Brauzer: http://192.168.100.239:8831")
    print("Faqat ishonchli, o'zingiz boshqaradigan tarmoqda ishlating.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
