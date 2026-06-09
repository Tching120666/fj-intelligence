import os
import httpx
import asyncio
from datetime import datetime

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]SEARCH_SYSTEM = (
    "Tu es un assistant specialise en actualites financieres. "
    "Utilise web_search pour trouver les dernieres actualites des marches financiers du jour. "
    "Fais plusieurs recherches : actualites marches financiers, forex macro news, banques centrales taux. "
    "Resume les informations cles en paragraphes simples. "
    "Pas de JSON, pas de markdown, pas de caracteres speciaux. Utilise des tirets pour les listes."
)

ANALYSIS_SYSTEM = (
    "Tu es un analyste de marche senior. Analyse les actualites financieres et reponds avec "
    "EXACTEMENT ce format, une ligne par element, rien dautre :\n\n"
    "SENTIMENT: RISK-ON ou RISK-OFF ou NEUTRE\n"
    "SCORE: nombre entre -100 et 100\n"
    "RESUME: une phrase de resume du contexte macro\n"
    "THEME1_TITRE: titre court\n"
    "THEME1_IMPACT: FORT ou MODERE ou FAIBLE\n"
    "THEME1_ACTIFS: USD,Gold,SP500\n"
    "THEME1_SYNTHESE: une phrase de contexte\n"
    "THEME1_HYPOTHESE: hypothese de trading concrete\n"
    "THEME2_TITRE: titre court\n"
    "THEME2_IMPACT: FORT ou MODERE ou FAIBLE\n"
    "THEME2_ACTIFS: liste\n"
    "THEME2_SYNTHESE: une phrase\n"
    "THEME2_HYPOTHESE: hypothese\n"
    "THEME3_TITRE: titre court\n"
    "THEME3_IMPACT: FORT ou MODERE ou FAIBLE\n"
    "THEME3_ACTIFS: liste\n"
    "THEME3_SYNTHESE: une phrase\n"
    "THEME3_HYPOTHESE: hypothese\n"
    "VIGIL1: premier point de vigilance\n"
    "VIGIL2: deuxieme point de vigilance\n\n"
    "Reponds UNIQUEMENT avec ces lignes. Rien dautre."
)

IMPACT_LABEL = {"FORT": "[FORT]", "MODERE": "[MODERE]", "FAIBLE": "[FAIBLE]"}async def call_claude(system, user_msg, use_web_search=False):
    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "system": system,
        "messages": [{"role": "user", "content": user_msg}],
    }
    if use_web_search:
        body["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json=body,
        )
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
        return {
            "titre": t,
            "impact": m.get("THEME" + str(n) + "_IMPACT", "MODERE"),
            "actifs": m.get("THEME" + str(n) + "_ACTIFS", ""),
            "synthese": m.get("THEME" + str(n) + "_SYNTHESE", ""),
            "hypothese": m.get("THEME" + str(n) + "_HYPOTHESE", ""),
        }

    return {
        "sentiment": m.get("SENTIMENT", "NEUTRE"),
        "score": m.get("SCORE", "0"),
        "resume": m.get("RESUME", ""),
        "themes": [t for t in (theme(1), theme(2), theme(3), theme(4), theme(5)) if t],
        "vigilance": [v for v in (m.get("VIGIL1"), m.get("VIGIL2"), m.get("VIGIL3")) if v],def format_telegram(data):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    sentiment = data["sentiment"]
    try:
        score = int(data["score"])
    except Exception:
        score = 0
    bar_filled = round(abs(score) / 10)
    if score < 0:
        bar = "[-]" * bar_filled + "[ ]" * (10 - bar_filled)
    else:
        bar = "[+]" * bar_filled + "[ ]" * (10 - bar_filled)
    sign = "+" if score > 0 else ""
    lines = [
        "*FJ Intelligence* -- " + now,
        "",
        "*Sentiment : " + sentiment + "*",
        bar + " " + sign + str(score) + "/100",
        "",
        "_" + data["resume"] + "_",
        "",
        "----------------",
        "*THEMES et HYPOTHESES*",
        "",
    ]
    for t in data["themes"]:
        label = IMPACT_LABEL.get(t["impact"], "[MODERE]")
        lines += [
            label + " *" + t["titre"] + "* -- " + t["actifs"],
            t["synthese"],
            ">> " + t["hypothese"],
            "",
        ]
    if data["vigilance"]:
        lines += ["----------------", "*Points de vigilance*", ""]
        for v in data["vigilance"]:
            lines.append("- " + v)
        lines.append("")
    lines.append("_Analyse IA - pas un conseil en investissement_")
    return "\n".join(lines)


async def send_telegram(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        })


async def main():
    now = datetime.now()
    date_str = now.strftime("%A %d %B %Y a %H:%M")
    news = await call_claude(
        SEARCH_SYSTEM,
        "Date : " + date_str + ". Trouve les dernieres actualites des marches financiers.",
        use_web_search=True,
    )
    structured = await call_claude(
        ANALYSIS_SYSTEM,
        "Voici le resume des actualites du jour :\n\n" + news,
    )
    data = parse_structured(structured)
    message = format_telegram(data)
    await send_telegram(message)


if __name__ == "__main__":
    asyncio.run(main())
    }
