from aiohttp import web, ClientSession, WSMsgType
import asyncio

BACKENDS = {
    "database": "http://127.0.0.1:8829",
    "webide": "http://127.0.0.1:8831",
    "vscode": "http://127.0.0.1:8840",
    "ai": "http://127.0.0.1:8099",
}

async def home(request):
    return web.Response(text="""<!doctype html>
<html lang="uz"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BigServer</title>
<style>
body{font:17px Arial;background:#101827;color:white;padding:35px}
h1{color:#67e8f9}
a{display:block;padding:18px;margin:12px 0;background:#1e293b;
color:white;text-decoration:none;border-radius:12px}
a:hover{background:#334155}
</style>
<h1>BIGSERVER</h1><p>Barcha xizmatlar bitta portda</p>
<a href="/database/">Database</a>
<a href="/webide/">Web IDE</a>
<a href="/vscode/">VS Code</a>
<a href="/ai/">Qwen AI</a>
</html>""", content_type="text/html")

async def proxy(request, name):
    backend = BACKENDS[name]
    tail = request.match_info.get("tail", "")
    target = backend + "/" + tail
    if request.query_string:
        target += "?" + request.query_string

    session = request.app["session"]

    if request.headers.get("Upgrade", "").lower() == "websocket":
        ws_client = web.WebSocketResponse()
        await ws_client.prepare(request)
        try:
            async with session.ws_connect(
                target, headers={"Origin": backend}
            ) as ws_server:
                async def forward(source, dest):
                    async for msg in source:
                        if msg.type == WSMsgType.TEXT:
                            await dest.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            await dest.send_bytes(msg.data)
                        elif msg.type == WSMsgType.CLOSE:
                            await dest.close()
                            break
                await asyncio.gather(
                    forward(ws_client, ws_server),
                    forward(ws_server, ws_client)
                )
        except Exception as e:
            print("WebSocket xatosi:", e)
        return ws_client

    headers = dict(request.headers)
    for h in ("Host", "Connection", "Upgrade", "Content-Length"):
        headers.pop(h, None)

    try:
        async with session.request(
            request.method, target,
            headers=headers,
            data=await request.read(),
            allow_redirects=False
        ) as response:
            body = await response.read()
            out_headers = dict(response.headers)

            # HTML ichidagi mutlaq yo'llarni xizmat prefiksiga moslash
            ctype = response.headers.get("Content-Type", "")
            if name in ("database", "webide") and (
                "text/html" in ctype or "javascript" in ctype
            ):
                text = body.decode("utf-8", errors="replace")
                text = text.replace('"/video"', f'"/{name}/video"')
                text = text.replace("'/video'", f"'/{name}/video'")
                text = text.replace('"/api/', f'"/{name}/api/')
                text = text.replace("'/api/", f"'/{name}/api/")
                body = text.encode("utf-8")

            # Backend qaytargan redirect manzillarini ham moslash
            location = out_headers.get("Location")
            if location and location.startswith("/"):
                out_headers["Location"] = f"/{name}" + location

            for h in ("Transfer-Encoding", "Connection", "Content-Length"):
                out_headers.pop(h, None)

            return web.Response(
                body=body,
                status=response.status,
                headers=out_headers
            )
    except Exception as e:
        return web.Response(
            text=f"{name} xizmati bilan aloqa yo‘q: {e}",
            status=502
        )

async def start_session(app):
    app["session"] = ClientSession()

async def close_session(app):
    await app["session"].close()

app = web.Application()
app.on_startup.append(start_session)
app.on_cleanup.append(close_session)
app.router.add_get("/", home)

for name in BACKENDS:
    async def handler(request, service=name):
        return await proxy(request, service)
    app.router.add_route("*", f"/{name}", handler)
    app.router.add_route("*", f"/{name}/{{tail:.*}}", handler)

web.run_app(app, host="0.0.0.0", port=9000)
