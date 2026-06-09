import os,httpx,asyncio
from datetime import datetime
AK=os.environ["ANTHROPIC_API_KEY"]
TB=os.environ["TELEGRAM_BOT_TOKEN"]
TC=os.environ["TELEGRAM_CHAT_ID"]
SS="You are a financial news researcher. Use the web_search tool to search for: financial markets news today. Then write a detailed summary of what you found including specific market moves, central bank news, economic data, and trading themes. Write at least 200 words."
AS="You are a senior trading analyst. Read this news summary and respond with EXACTLY these lines, nothing else:\nSENTIMENT: RISK-ON or RISK-OFF or NEUTRE\nSCORE: number between -100 and 100\nRESUME: one sentence summary\nTHEME1_TITRE: short title\nTHEME1_IMPACT: FORT or MODERE or FAIBLE\nTHEME1_ACTIFS: USD,Gold,SP500\nTHEME1_SYNTHESE: one sentence\nTHEME1_HYPOTHESE: trading hypothesis\nTHEME2_TITRE: short title\nTHEME2_IMPACT: FORT or MODERE or FAIBLE\nTHEME2_ACTIFS: assets\nTHEME2_SYNTHESE: one sentence\nTHEME2_HYPOTHESE: trading hypothesis\nTHEME3_TITRE: short title\nTHEME3_IMPACT: FORT or MODERE or FAIBLE\nTHEME3_ACTIFS: assets\nTHEME3_SYNTHESE: one sentence\nTHEME3_HYPOTHESE: trading hypothesis\nVIGIL1: first watch point\nVIGIL2: second watch point"
async def claude(sys,msg,ws=False):
 b={"model":"claude-sonnet-4-20250514","max_tokens":1000,"system":sys,"messages":[{"role":"user","content":msg}]}
 if ws:b["tools"]=[{"type":"web_search_20250305","name":"web_search"}]
 async with httpx.AsyncClient(timeout=60) as c:
  r=await c.post("https://api.anthropic.com/v1/messages",headers={"Content-Type":"application/json","x-api-key":AK,"anthropic-version":"2023-06-01"},json=b)
  return "".join(x["text"] for x in r.json().get("content",[]) if x["type"]=="text")
def parse(text):
 m={}
 for l in text.splitlines():
  if ":" in l:
   k,v=l.split(":",1);m[k.strip().upper()]=v.strip()
 def t(n):
  x=m.get("THEME"+str(n)+"_TITRE")
  if not x:return None
  return {"titre":x,"impact":m.get("THEME"+str(n)+"_IMPACT","MODERE"),"actifs":m.get("THEME"+str(n)+"_ACTIFS",""),"synthese":m.get("THEME"+str(n)+"_SYNTHESE",""),"hypothese":m.get("THEME"+str(n)+"_HYPOTHESE","")}
 return {"sentiment":m.get("SENTIMENT","NEUTRE"),"score":m.get("SCORE","0"),"resume":m.get("RESUME",""),"themes":[x for x in(t(1),t(2),t(3))if x],"vigilance":[v for v in(m.get("VIGIL1"),m.get("VIGIL2"))if v]}
def fmt(d):
 try:sc=int(d["score"])
 except:sc=0
 sg="+" if sc>0 else ""
 msg="*FJ Intelligence* "+datetime.now().strftime("%d/%m/%Y %H:%M")+"\n\n"
 msg+="*"+d["sentiment"]+"* | Score: "+sg+str(sc)+"/100\n\n"
 msg+="_"+d["resume"]+"_\n\n--- THEMES ---\n\n"
 for t in d["themes"]:msg+="["+t["impact"]+"] *"+t["titre"]+"* "+t["actifs"]+"\n"+t["synthese"]+"\n>> "+t["hypothese"]+"\n\n"
 if d["vigilance"]:msg+="--- VIGILANCE ---\n"+"".join("- "+v+"\n" for v in d["vigilance"])
 return msg+"_Analyse IA - pas un conseil en investissement_"
async def send(msg):
 async with httpx.AsyncClient(timeout=30) as c:
  await c.post("https://api.telegram.org/bot"+TB+"/sendMessage",json={"chat_id":TC,"text":msg,"parse_mode":"Markdown"})
async def main():
 news=await claude(SS,"Today is "+datetime.now().strftime("%B %d %Y")+". Search and summarize the latest financial markets news.",True)
 structured=await claude(AS,"Here is todays financial news summary:\n\n"+news)
 data=parse(structured)
 await send(fmt(data))
asyncio.run(main())
