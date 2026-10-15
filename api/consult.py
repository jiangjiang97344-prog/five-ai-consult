# -*- coding: utf-8 -*-
"""
五方会诊 · 云端版（Vercel Python Serverless）
- 仅依赖 Python 标准库（urllib），无需 requirements.txt
- 环境变量：SITE_PASSWORD, MOONSHOT_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY,
  ARK_API_KEY, DASHSCOPE_API_KEY（可选 MOONSHOT_MODEL / OPENAI_MODEL /
  GEMINI_MODEL / ARK_MODEL / DASHSCOPE_MODEL 指定型号）

用法：POST /api/consult
  请求体：{"password": "访问密码", "question": "你的问题"}
  响应：  {"question": ..., "answers": {...}, "errors": {...}, "consensus": "..."}
"""
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler

TIMEOUT = 100      # 单次请求超时（秒）
MAX_RETRY = 2      # 瞬时错误（限流/高峰/超时）重试次数
RETRY_WAIT = 5     # 重试间隔（秒）


# ---------- HTTP 工具 ----------
def post_json(url, payload, headers=None, timeout=TIMEOUT):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:200]
        raise RuntimeError(f"HTTP {e.code}: {body}")


def with_retry(fn):
    last = None
    for attempt in range(MAX_RETRY + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            msg = str(e)
            transient = any(s in msg for s in (
                "503", "429", "500", "502", "timed out", "timeout",
                "Temporary failure", "Service Unavailable",
            ))
            if attempt < MAX_RETRY and transient:
                time.sleep(RETRY_WAIT)
                continue
            raise last


# ---------- 各家模型 ----------
def ask_openai_compat(url, key, model, prompt, temperature=None):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if temperature is not None:
        payload["temperature"] = temperature
    data = post_json(url, payload, {"Authorization": f"Bearer {key}"})
    return data["choices"][0]["message"]["content"]


def ask_kimi(prompt):
    # 注意：kimi-k3 只允许 temperature=1，故不传该参数
    return ask_openai_compat(
        "https://api.moonshot.cn/v1/chat/completions",
        os.environ["MOONSHOT_API_KEY"],
        os.environ.get("MOONSHOT_MODEL", "kimi-k3"),
        prompt,
    )


def ask_gpt(prompt):
    return ask_openai_compat(
        "https://api.openai.com/v1/chat/completions",
        os.environ["OPENAI_API_KEY"],
        os.environ.get("OPENAI_MODEL", "gpt-4o"),
        prompt, 0.6,
    )


def ask_doubao(prompt):
    return ask_openai_compat(
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        os.environ["ARK_API_KEY"],
        os.environ.get("ARK_MODEL", "doubao-seed-2-1-pro-260915"),
        prompt, 0.6,
    )


def ask_qwen(prompt):
    return ask_openai_compat(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        os.environ["DASHSCOPE_API_KEY"],
        os.environ.get("DASHSCOPE_MODEL", "qwen-plus"),
        prompt, 0.6,
    )


def ask_gemini(prompt):
    model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
           f":generateContent?key={os.environ['GEMINI_API_KEY']}")
    data = post_json(url, {"contents": [{"parts": [{"text": prompt}]}]})
    return "".join(p["text"] for p in data["candidates"][0]["content"]["parts"])


MODELS = [
    ("Kimi", ask_kimi),
    ("GPT", ask_gpt),
    ("Gemini", ask_gemini),
    ("豆包", ask_doubao),
    ("千问", ask_qwen),
]


SYNTHESIS_TEMPLATE = """你是一场"五方会诊"的总协调人。请根据五家AI对同一问题的回答，给出会诊结论。

【用户问题】
{question}

【五家回答】
{answers}

请严格按以下结构输出：
✅ 五方共识答案：综合各家观点、去掉冗余后的一段话（若五家实质一致，给出合并版答案）。
⚠️ 分歧点：如有分歧，注明哪家与哪家在哪些点上不同；如无实质分歧，明确写"五方无实质分歧"。
💡 各家特点：一句话概括每家的表达风格。

要求：客观，不要编造任何一家没说过的观点；总篇幅控制在300字以内。"""


def consult(question):
    results, errors = {}, {}

    def run_one(name, fn):
        return name, with_retry(lambda: fn(question))

    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(run_one, name, fn): name for name, fn in MODELS}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                _, answer = fut.result()
                results[name] = answer
            except Exception as e:
                errors[name] = str(e)[:300]

    # 由 Kimi 担任总协调人做综合（Kimi 缺席或失败则跳过，前端只展示各家原话）
    consensus = None
    if results:
        answers_block = "\n\n".join(f"【{n}】{a}" for n, a in results.items())
        synth_prompt = SYNTHESIS_TEMPLATE.format(question=question, answers=answers_block)
        try:
            consensus = with_retry(lambda: ask_kimi(synth_prompt))
        except Exception:
            consensus = None

    return {
        "question": question,
        "answers": results,
        "errors": errors,
        "consensus": consensus,
    }


# ---------- Vercel 入口 ----------
class handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, {"ok": True, "service": "five-ai-consult"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            self._send(400, {"error": "请求体不是合法 JSON"})
            return

        password = str(body.get("password", ""))
        expect = os.environ.get("SITE_PASSWORD", "")
        if expect and password != expect:
            self._send(401, {"error": "访问密码错误"})
            return

        question = str(body.get("question", "")).strip()
        if not question:
            self._send(400, {"error": "问题不能为空"})
            return
        if len(question) > 4000:
            self._send(400, {"error": "问题太长了（限4000字）"})
            return

        try:
            self._send(200, consult(question))
        except Exception as e:
            self._send(500, {"error": f"服务内部错误: {str(e)[:200]}"})
