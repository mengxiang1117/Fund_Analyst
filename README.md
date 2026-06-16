# Fund Analyst - AI 基金分析助手

基于 LangChain 和 MCP 协议的智能基金分析助手，支持自然语言查询基金信息、分析业绩表现、获取投资建议。

## 功能特点

- **自然语言交互**: 用自然语言提问，AI 助手帮你分析基金
- **实时流式响应**: 打字机效果，实时显示分析结果
- **多轮对话**: 支持上下文理解，连续提问更智能
- **主题切换**: 支持亮色/暗色主题
- **对话管理**: 保存历史对话，随时回顾
- **灵活配置**: 支持自定义 LLM 和 MCP 服务

## 快速开始

### 方式一：从源码运行

#### 1. 环境要求

- Python 3.9 或更高版本
- Windows / macOS / Linux

#### 2. 安装依赖

```bash
# 克隆或下载项目
cd fund_anagement_assistant

# 安装依赖
pip install -r requirements.txt
```

#### 3. 配置

```bash
# 复制配置模板
cp config.example.yaml config.yaml

# 编辑 config.yaml，填入你的 API 密钥
```

配置说明：

```yaml
llm:
  api_key: "你的 LLM API 密钥"
  base_url: "API 地址"
  model_name: "模型名称"

mcp_servers:
  qieman:
    headers:
      x-api-key: "你的且慢 MCP API 密钥"  # 从 https://qieman.com/mcp 获取
```

#### 4. 启动

```bash
python web_app.py
```

浏览器访问: http://localhost:8000

### 方式二：使用打包版本 (exe)

从 [Releases](https://github.com/mengxiang1117/Fund_Analyst/releases) 页面下载 `Fund_Analyst.zip`，解压后：

```
Fund_Analyst/
├── FundAnalyst.exe       # 主程序
├── config.example.yaml   # 配置模板
└── config.yaml           # 首次运行自动生成，需编辑
```

**使用步骤：**

1. 双击运行 `FundAnalyst.exe`
2. 首次运行会自动生成 `config.yaml` 并提示你编辑 API 密钥
3. 编辑 `config.yaml` 填入密钥后，重新运行 `FundAnalyst.exe`
4. 浏览器自动打开 http://localhost:8000

## 配置说明

### LLM 配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `api_key` | LLM API 密钥 | `sk-...` |
| `base_url` | API 基础 URL | `https://api.openai.com/v1` |
| `model_name` | 模型名称 | `gpt-4` |

支持所有 OpenAI 兼容接口，如：
- OpenAI
- 火山引擎
- 阿里云
- 智谱 AI
- 本地部署的模型

### MCP 配置

且慢 MCP API 密钥获取地址: https://qieman.com/mcp

| 配置项 | 说明 |
|--------|------|
| `transport` | 传输方式: `streamable_http` 或 `stdio` |
| `url` | MCP 服务地址 |
| `headers` | 请求头 (如 API Key) |

## 使用示例

### 基金查询

- "沪深300指数基金推荐"
- "医药主题基金有哪些"
- "国投瑞银白银期货A怎么样"
- "000001 基金最新净值"

### 基金分析

- "分析一下易方达蓝筹精选的持仓结构"
- "对比华夏沪深300和华泰柏瑞沪深300的业绩"
- "评估一下新能源板块的投资价值"

## 开发

### 项目结构

```
fund_anagement_assistant/
├── web_app.py              # FastAPI 主应用
├── qieman_mcp.py            # Qieman MCP Agent 封装
├── config.yaml             # 配置文件 (用户创建)
├── config.example.yaml     # 配置模板
├── requirements.txt        # Python 依赖
├── build.py                # PyInstaller 打包脚本
├── static/
│   └── index.html          # 前端页面
└── conversations/          # 对话存储目录
```

### 打包为 exe

```bash
# 安装打包工具
pip install pyinstaller

# 运行打包脚本
python build.py
```

打包产物在 `dist/FundAnalyst/` 目录下，将整个文件夹压缩即可分发。

## 常见问题

### Q: 启动报错 "ModuleNotFoundError"

```bash
pip install -r requirements.txt
```

### Q: 连接 MCP 服务失败

检查 `config.yaml` 中的 MCP 配置，确保：
- URL 正确
- API Key 有效
- 网络连接正常

### Q: 如何更换 LLM？

编辑 `config.yaml` 中的 `llm` 部分，填入新的 API 地址和密钥。

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交 Issue。
