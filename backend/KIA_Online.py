"""
K.IA - Konect Intelligence Artefact
Compatible Anthropic API (claude-sonnet-4-6) ET OpenRouter (modeles gratuits).

Dans le .env, configure selon ton fournisseur :

  # Anthropic (avec credits)
  PROVIDER=anthropic
  ANTHROPIC_API_KEY=sk-ant-...

  # OpenRouter (gratuit pour tester)
  PROVIDER=openrouter
  OPENROUTER_API_KEY=sk-or-...
  OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free
"""

import os
import json
import traceback
import aiohttp
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

PROVIDER           = os.getenv("PROVIDER", "anthropic").lower()
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-8b-instruct:free")
MAPS_API_KEY       = os.getenv("MAPS_API_KEY", "")

SYSTEM_PROMPT = """Tu es K.IA (Konect Intelligence Artefact), un assistant vocal personnel
francophone, amical et concis. Tes reponses seront lues a voix haute :
- Reponds en francais naturel, en phrases courtes.
- Pas de markdown ni de listes sauf si demande explicitement."""


# ---------------------------------------------------------------------------
# Couche d'abstraction LLM : Anthropic ou OpenRouter
# ---------------------------------------------------------------------------

async def _call_anthropic_stream(messages: list, socketio, tools: list):
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    full_text = ""
    tool_calls = []
    stop_reason = "end_turn"

    async with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    ) as stream:
        async for event in stream:
            if hasattr(event, "type") and event.type == "content_block_delta":
                if hasattr(event.delta, "text"):
                    chunk = event.delta.text
                    socketio.emit("receive_text_chunk", {"text": chunk})
                    print(chunk, end="", flush=True)
                    full_text += chunk
        final = await stream.get_final_message()

    for block in final.content:
        if block.type == "tool_use":
            tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
    stop_reason = final.stop_reason

    print()
    return full_text, tool_calls, stop_reason


async def _call_openrouter_stream(messages: list, socketio):
    """Appel OpenRouter (API compatible OpenAI, streaming SSE). Sans outils pour simplifier."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kia-assistant.local",
        "X-Title": "K.IA",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "stream": True,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + [
            {"role": m["role"], "content": (
                m["content"] if isinstance(m["content"], str)
                else next((b["text"] for b in m["content"] if b["type"] == "text"), "")
            )}
            for m in messages
        ],
    }

    full_text = ""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise Exception(f"OpenRouter {resp.status}: {body}")
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    chunk = obj["choices"][0]["delta"].get("content", "")
                    if chunk:
                        socketio.emit("receive_text_chunk", {"text": chunk})
                        print(chunk, end="", flush=True)
                        full_text += chunk
                except Exception:
                    pass

    print()
    return full_text, [], "end_turn"  # OpenRouter : pas d'outils pour l'instant


# ---------------------------------------------------------------------------
# Classe principale K.IA
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_weather",
        "description": "Obtenir la meteo actuelle pour une ville donnee.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
    {
        "name": "get_search_results",
        "description": "Rechercher des informations recentes sur le web.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


class KIA:
    def __init__(self, socketio):
        self.socketio = socketio
        self.messages = []
        self.latest_frame = None
        print(f"[K.IA] Fournisseur : {PROVIDER.upper()}")
        if PROVIDER == "openrouter":
            print(f"[K.IA] Modele : {OPENROUTER_MODEL}")
        else:
            print("[K.IA] Modele : claude-sonnet-4-6")

    def set_video_frame(self, data_url: str):
        try:
            self.latest_frame = data_url.split(",", 1)[1]
        except (IndexError, AttributeError):
            self.latest_frame = None

    async def process_input(self, user_text: str, use_camera: bool = False):
        try:
            content = []
            if use_camera and self.latest_frame and PROVIDER == "anthropic":
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": self.latest_frame},
                })
            content.append({"type": "text", "text": user_text})
            self.messages.append({"role": "user", "content": content})

            self.socketio.emit("status", {"message": "thinking"})
            await self._run_agent_loop()
            self.socketio.emit("status", {"message": "idle"})

        except Exception as e:
            print(f"[K.IA][ERREUR] {e}")
            traceback.print_exc()
            self.socketio.emit("status", {"message": "error"})
            self.socketio.emit("receive_text_chunk", {"text": f"[Erreur K.IA : {e}]"})

    async def _run_agent_loop(self):
        while True:
            if PROVIDER == "openrouter":
                full_text, tool_calls, stop_reason = await _call_openrouter_stream(
                    self.messages, self.socketio
                )
            else:
                full_text, tool_calls, stop_reason = await _call_anthropic_stream(
                    self.messages, self.socketio, TOOLS
                )

            assistant_content = [{"type": "text", "text": full_text}]
            for tc in tool_calls:
                assistant_content.append({"type": "tool_use", **tc})
            self.messages.append({"role": "assistant", "content": assistant_content})

            if stop_reason != "tool_use" or not tool_calls:
                break

            tool_results = []
            for call in tool_calls:
                print(f"[K.IA] Outil : {call['name']}({call['input']})")
                result = await self._execute_tool(call["name"], call["input"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })
            self.messages.append({"role": "user", "content": tool_results})

    async def _execute_tool(self, name: str, args: dict):
        try:
            if name == "get_weather":
                return await self._get_weather(args["city"])
            if name == "get_search_results":
                return await self._get_search_results(args["query"])
            return {"error": f"Outil inconnu: {name}"}
        except Exception as e:
            return {"error": str(e)}

    async def _get_weather(self, city: str):
        try:
            import python_weather
            async with python_weather.Client(unit=python_weather.METRIC) as wc:
                w = await wc.get(city)
                data = {"city": city, "temperature": w.temperature, "description": w.description}
                self.socketio.emit("weather_update", data)
                return data
        except Exception as e:
            return {"error": str(e)}

    async def _get_search_results(self, query: str):
        try:
            from googlesearch import search as google_search
            from bs4 import BeautifulSoup
            urls = list(google_search(query, num_results=3))
            results = []
            async with aiohttp.ClientSession() as session:
                for url in urls:
                    try:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                            html = await resp.text()
                            soup = BeautifulSoup(html, "lxml")
                            title = soup.title.string.strip() if soup.title else url
                            p = soup.find("p")
                            snippet = p.get_text(strip=True)[:300] if p else ""
                            results.append({"url": url, "title": title, "snippet": snippet})
                    except Exception:
                        results.append({"url": url, "title": url, "snippet": "(inaccessible)"})
            self.socketio.emit("search_results_update", {"query": query, "results": results})
            return results
        except Exception as e:
            return {"error": str(e)}