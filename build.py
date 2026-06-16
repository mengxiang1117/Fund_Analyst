"""
PyInstaller 打包脚本 (单文件模式)
用法: python build.py
产物: dist/FundAnalyst.exe + dist/config.example.yaml
"""

import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "FundAnalyst"
ENTRY = "web_app.py"
ROOT = Path(__file__).parent
DIST_DIR = ROOT / "dist"

HIDDEN_IMPORTS = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "tiktoken_ext.openai_public",
    "tiktoken_ext",
    "yaml",
    "pydantic",
    "httptools",
    "websockets",
    "langchain_openai",
    "langchain_mcp_adapters",
    "langchain_core",
    "langchain.agents",
    "langchain_core.messages",
    "langgraph",
    "langgraph.prebuilt",
    "langgraph.prebuilt.tool_node",
    "langgraph.prebuilt.chat_agent_executor",
    "langgraph.runtime",
    "langgraph.checkpoint",
    "langgraph.checkpoint.memory",
    "langgraph.graph",
    "langgraph_sdk",
    "langchain",
    "mcp",
    "httpx",
]

DATA_FILES = [
    ("static", "static"),
    ("config.example.yaml", "."),
]

EXCLUDE_MODULES = [
    "numpy",
    "pandas",
    "scipy",
    "matplotlib",
    "PIL",
    "torch",
    "torchvision",
    "torchaudio",
    "transformers",
    "sklearn",
    "notebook",
    "jupyter",
    "IPython",
    "pytest",
    "setuptools",
    "wheel",
    "pip",
    "tkinter",
]


def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--console",
        "--noconfirm",
        "--clean",
    ]

    for mod in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", mod]

    for mod in EXCLUDE_MODULES:
        cmd += ["--exclude-module", mod]

    sep = ";" if sys.platform == "win32" else ":"
    for src, dst in DATA_FILES:
        cmd += ["--add-data", f"{src}{sep}{dst}"]

    cmd.append(ENTRY)

    print(f"Running: {' '.join(cmd)}\n")
    subprocess.check_call(cmd, cwd=str(ROOT))

    example_src = ROOT / "config.example.yaml"
    example_dst = DIST_DIR / "config.example.yaml"
    if example_src.exists() and DIST_DIR.exists():
        shutil.copy2(example_src, example_dst)

    print("\n" + "=" * 50)
    print("打包完成!")
    print(f"  可执行文件: {DIST_DIR / f'{APP_NAME}.exe'}")
    print(f"  配置模板:   {example_dst}")
    print()
    print("分发方式: 将 dist/ 下的两个文件一起发给用户")
    print("使用方式: 双击 FundAnalyst.exe，首次运行自动生成 config.yaml")
    print("=" * 50)


if __name__ == "__main__":
    build()
