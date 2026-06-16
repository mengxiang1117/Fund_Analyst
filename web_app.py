import sys
import uuid
import json
import shutil
import webbrowser
import threading
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

import yaml
from qieman_mcp import FundAssistantAgent, load_config

app = FastAPI(title="基金分析助手")

if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(sys._MEIPASS)
    BASE_DIR = Path(sys.executable).parent
else:
    BUNDLE_DIR = Path(__file__).parent
    BASE_DIR = Path(__file__).parent

CONV_DIR = BASE_DIR / "conversations"
CONV_DIR.mkdir(exist_ok=True)
CONFIG_FILE = BASE_DIR / "config.yaml"
CONFIG_EXAMPLE = BUNDLE_DIR / "config.example.yaml"

# 全局 agent 单例
_agent: FundAssistantAgent | None = None


async def get_agent() -> FundAssistantAgent:
    global _agent
    if _agent is None:
        config = load_config()
        _agent = FundAssistantAgent(config=config)
    return _agent


def _conv_path(session_id: str) -> Path:
    return CONV_DIR / f"{session_id}.json"


def _save_conversation(session_id: str, data: dict):
    _conv_path(session_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_conversation(session_id: str) -> dict | None:
    p = _conv_path(session_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _list_conversations() -> list[dict]:
    """按修改时间倒序列出所有对话"""
    items = []
    for f in CONV_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items.append({
                "id": data.get("id", f.stem),
                "title": data.get("title", "未命名对话"),
                "created_at": data.get("created_at", ""),
            })
        except Exception:
            continue
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


# 挂载静态文件
app.mount("/static", StaticFiles(directory=BUNDLE_DIR / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return (BUNDLE_DIR / "static" / "index.html").read_text(encoding="utf-8")


@app.post("/api/session/new")
async def new_session():
    sid = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_conversation(sid, {"id": sid, "title": "新对话", "messages": [], "created_at": now})
    return {"session_id": sid}


@app.get("/api/sessions")
async def list_sessions():
    return _list_conversations()


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    data = _load_conversation(session_id)
    if data is None:
        return JSONResponse({"error": "对话不存在"}, status_code=404)
    return data


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    p = _conv_path(session_id)
    if p.exists():
        p.unlink()
    return {"ok": True}


@app.post("/api/session/{session_id}/rename")
async def rename_session(session_id: str, request: Request):
    body = await request.json()
    title = body.get("title", "").strip()
    data = _load_conversation(session_id)
    if data is None:
        return JSONResponse({"error": "对话不存在"}, status_code=404)
    if title:
        data["title"] = title
        _save_conversation(session_id, data)
    return {"ok": True}


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    session_id = body.get("session_id", "default")

    if not message:
        return StreamingResponse(
            iter([f'data: {json.dumps({"error": "消息不能为空"})}\n\n', "data: [DONE]\n\n"]),
            media_type="text/event-stream",
        )

    # 确保对话文件存在
    conv = _load_conversation(session_id)
    if conv is None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conv = {"id": session_id, "title": "新对话", "messages": [], "created_at": now}
        _save_conversation(session_id, conv)

    agent = await get_agent()

    async def event_generator():
        full_bot_text = ""
        try:
            async for text in agent.ask_stream(question=message, user_id=session_id):
                full_bot_text += text
                yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

        # 持久化对话
        conv = _load_conversation(session_id)
        if conv:
            if not conv["messages"]:
                conv["title"] = message[:20] + ("..." if len(message) > 20 else "")
            conv["messages"].append({"role": "user", "text": message})
            conv["messages"].append({"role": "bot", "text": full_bot_text})
            _save_conversation(session_id, conv)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/config")
async def get_config():
    config = load_config()
    return {
        "llm": config.get("llm", {}),
        "mcp": {
            "x_api_key": config.get("mcp_servers", {}).get("qieman", {}).get("headers", {}).get("x-api-key", "")
        }
    }


@app.put("/api/config")
async def update_config(request: Request):
    body = await request.json()
    config = load_config()

    # 更新 LLM 配置
    llm = body.get("llm", {})
    if "base_url" in llm:
        config["llm"]["base_url"] = llm["base_url"]
    if "api_key" in llm:
        config["llm"]["api_key"] = llm["api_key"]
    if "model_name" in llm:
        config["llm"]["model_name"] = llm["model_name"]

    # 更新 MCP x-api-key
    x_api_key = body.get("x_api_key", "")
    if x_api_key:
        config["mcp_servers"]["qieman"]["headers"]["x-api-key"] = x_api_key

    # 写入文件
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    # 重置 agent 使其重新加载配置
    global _agent
    _agent = None

    return {"ok": True}


def _ensure_config():
    """首次运行时从模板创建 config.yaml"""
    if CONFIG_FILE.exists():
        return True
    if CONFIG_EXAMPLE.exists():
        shutil.copy2(CONFIG_EXAMPLE, CONFIG_FILE)
        print("=" * 50)
        print(f"已创建配置文件: {CONFIG_FILE}")
        print("请编辑 config.yaml 填入你的 API 密钥后重新启动")
        print("=" * 50)
        return False
    print(f"[ERROR] 找不到配置模板: {CONFIG_EXAMPLE}")
    return False


if __name__ == "__main__":
    import uvicorn

    if not _ensure_config():
        if getattr(sys, "frozen", False):
            input("按回车键退出...")
        sys.exit(1)

    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8000")).start()
    print("启动服务: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
