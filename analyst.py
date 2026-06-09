import os
import httpx
import asyncio
from datetime import datetime

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SEARCH_SYSTEM = "  SEARCH_SYSTEM ="You are a financial news assistant. Use web_search to find financial markets news today, forex news, central bank news. Summarize in plain text."
ANALYSIS_SYSTEM = "Tu es un analyste senior. Reponds avec ce format exact ligne par ligne:\nSENTIMENT: RISK-ON ou RISK-OFF ou NEUTRE\nSCORE: nombre entre -100 et 100\nRESUME: une phrase\nTHEME1_TITRE: titre\nTHEME1_IMPACT: FORT ou MODERE ou FAIBLE\nTHEME1_ACTIFS: liste\nTHEME1_SYNTHESE: une phrase\nTHEME1_HYPOTHESE: hypothese\nTHEME2_TITRE: titre\nTHEME2_IMPACT: FORT ou MODERE ou FAIBLE\nTHEME2_ACTIFS: liste\nTHEME2_SYNTHESE: une phrase\nTHEME2_HYPOTHESE: hypothese\nTHEME3_TITRE: titre\nTHEME3_IMPACT: FORT ou MODERE ou FAIBLE\nTHEME3_ACTIFS: liste\nTHEME3_SYNTHESE: une phrase\nTHEME3_HYPOTHESE: hypothese\nVIGIL1: vigilance 1\nVIGIL2: vigilance 2"


async def call_claude(system, user_msg, use_web_search=False):
    body = {"model": "claude-sonnet-4-20250514", "max_tokens": 1000, "system": system, "messages": [{"role": "user", "content": user_msg}]}
    if use_web_search:
        body["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.anthropic.com/v1/messages", headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"}, json=body)
        data = r.json()
        return "".join(b["text"] for b in data.get("content", []) if b["type"] == "text")


def parse_structured(text):
    m = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        m[k.strip().upper()] = v.strip()
    def theme(n):
        t = m.get("THEME" + str(n) + "_TITRE")
        if not t:
            return None
        return {"titre": t, "impact": m.get("THEME" + str(n) + "_IMPACT", "MODERE"), "actifs": m.get("THEME" + str(n) + "_ACTIFS", ""), "synthese": m.get("THEME" + str(n) + "_SYNTHESE", ""), "hypothese": m.get("THEME" + str(n) + "_HYPOTHESE", "")}
    return {"sentiment": m.get("SENTIMENT", "NEUTRE"), "score": m.get("SCORE", "0"), "resume": m.get("RESUME", ""), "themes": [t for t in (theme(1), theme(2), theme(3)) if t], "vigilance": [v for v in (m.get("VIGIL1"), m.get("VIGIL2")) if v]}


def format_telegram(data):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        score = int(data["score"])
    except Exception:
        score = 0
    sign = "+" if score > 0 else ""
    msg = "*FJ Intelligence* -- " + now + "\n\n"
    msg += "*Sentiment: " + data["sentiment"] + "* | Score: " + sign + str(score) + "/100\n\n"
    msg += "_" + data["resume"] + "_\n\n"
    msg += "--- THEMES ---\n\n"
    for t in data["themes"]:
        msg += "[" + t["impact"] + "] *" + t["titre"] + "* (" + t["actifs"] + ")\n"
        msg += t["synthese"] + "\n"
        msg += ">> " + t["hypothese"] + "\n\n"
    if data["vigilance"]:
        msg += "--- VIGILANCE ---\n"
        for v in data["vigilance"]:
            msg += "- " + v + "\n"
    msg += "\n_Analyse IA - pas un conseil en investissement_"
    return msg


async def send_telegram(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})


async def main():
    date_str = datetime.now().strftime("%A %d %B %Y")
    news = await call_claude(SEARCH_SYSTEM, "Date: " + date_str + ". Cherche les dernieres actualites financieres.", use_web_search=True)
    structured = await call_claude(ANALYSIS_SYSTEM, "Actualites du jour:\n\n" + news)
    data = parse_structured(structured)
    message = format_telegram(data)
    await send_telegram(message)


if __name__ == "__main__":
    asyncio.run(main())
