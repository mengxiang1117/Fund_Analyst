import sys
import json
from pathlib import Path
from typing import AsyncGenerator

import yaml
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import InMemorySaver
import asyncio

if getattr(sys, "frozen", False):
    _RUNTIME_DIR = Path(sys.executable).parent
else:
    _RUNTIME_DIR = Path(__file__).parent

CONFIG_PATH = _RUNTIME_DIR / "config.yaml"
CONV_DIR = _RUNTIME_DIR / "conversations"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_conversation(user_id: str) -> list[dict]:
    p = CONV_DIR / f"{user_id}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("messages", [])
    return []


class FundAssistantAgent:
    def __init__(self, config: dict):
        self.config = config
        self.memory = InMemorySaver()
        self.client = None
        self.tools = None
        self.agent = None
        self._restored_threads: set[str] = set()

    async def initialize(self):
        """初始化 MCP 客户端、工具和代理"""
        if self.client is None:
            server_cfg = self.config["mcp_servers"]["qieman"]
            self.client = MultiServerMCPClient(
                {
                    "qieman_mcp": {
                        "transport": server_cfg["transport"],
                        "url": server_cfg["url"],
                        "headers": server_cfg.get("headers", {}),
                    }
                }
            )
            try:
                self.tools = await self.client.get_tools()
            except Exception as e:
                print(f"[ERROR] MCP 工具加载失败: {e}")
                raise

        if self.agent is None:
            llm_cfg = self.config["llm"]
            model = ChatOpenAI(
                base_url=llm_cfg["base_url"],
                api_key=llm_cfg["api_key"],
                model=llm_cfg["model_name"],
            )
            self.agent = create_agent(
                model=model,
                tools=self.tools,
                system_prompt=(
                    "你是一个专业的基金分析助手。请结合对话历史理解用户意图"
                    "（如'它'、'该基金'指代上文提到的基金），"
                    "并使用工具查询基金的规模、持有人结构、业绩表现等信息。\n"
                    "工具使用规则：\n"
                    "- 使用SearchFunds搜索基金时，优先用keyword参数按名称搜索，"
                    "不要同时使用category参数。category只接受工具定义中列出的固定枚举值，"
                    "不要传入自己猜测的分类名称。\n"
                    "- 如果工具调用返回错误，分析错误信息并换一种参数组合重试。\n"
                    "当你从用户问题和对话历史中无法获取基金信息时，"
                    "提醒输入正确的基金代码或者基金名称。"
                    "输出要求：Markdown格式"
                ),
                checkpointer=self.memory,
            )

    async def _restore_memory(self, user_id: str):
        """从持久化的对话文件中恢复记忆到 checkpointer"""
        if user_id in self._restored_threads:
            return
        messages = _load_conversation(user_id)
        if len(messages) < 2:
            self._restored_threads.add(user_id)
            return

        config = {"configurable": {"thread_id": user_id}}
        lc_messages = []
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["text"]))
            else:
                lc_messages.append(AIMessage(content=msg["text"]))
        self.agent.update_state(config, {"messages": lc_messages})
        self._restored_threads.add(user_id)

    async def ask_stream(self, question: str, user_id: str) -> AsyncGenerator[str, None]:
        """流式生成回答文本，供 web SSE 使用"""
        await self.initialize()
        await self._restore_memory(user_id)
        config = {"configurable": {"thread_id": user_id}}
        async for event in self.agent.astream(
            {"messages": [("user", question)]},
            config=config,
            stream_mode="messages",
        ):
            token, metadata = event
            if metadata.get("langgraph_node") != "model":
                continue
            text = token.content
            if isinstance(text, str) and text:
                yield text

    async def ask(self, question: str, user_id: str, stream: bool = True):
        """向代理提问，支持流式或非流式输出"""
        await self.initialize()
        await self._restore_memory(user_id)
        config = {"configurable": {"thread_id": user_id}}
        print("\n" + "=" * 30 + "问题" + "=" * 30)
        print(question)

        if stream:
            last_content = ""
            async for event in self.agent.astream(
                {"messages": [("user", question)]},
                config=config,
                stream_mode="messages",
            ):
                token, metadata = event
                if metadata.get("langgraph_node") != "model":
                    continue
                text = token.content
                if isinstance(text, str) and text:
                    print(text, end="", flush=True)
                    last_content += text
            print("\n" + "=" * 30 + "结果" + "=" * 30)
            return last_content
        else:
            response = await self.agent.ainvoke(
                {"messages": [("user", question)]}, config=config
            )
            final_response = response["messages"][-1].content
            print("\n" + "=" * 30 + "结果" + "=" * 30)
            return final_response


async def main():
    config = load_config()
    assistant = FundAssistantAgent(config=config)
    await assistant.ask(
        question="cpo相关基金推荐？",
        user_id="user_123",
        stream=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
