import os,httpx,asyncio,re
from datetime import datetime
AK=os.environ["ANTHROPIC_API_KEY"]
TB=os.environ["TELEGRAM_BOT_TOKEN"]
TC=os.environ["TELEGRAM_CHAT_ID"]
AS="Tu es un analyste trading senior. Lis ces actualites et reponds avec EXACTEMENT ces lignes:\nSENTIMENT: RISK-ON ou RISK-OFF ou NEUTRE\nSCORE: nombre entre -100 et 100\nRESUME: une phrase\nTHEME1_TITRE: titre\nTHEME1_IMPACT: FORT ou MODERE ou FAIBLE\nTHEME1_ACTIFS: actifs\nTHEME1_SYNTHESE: une phrase\nTHEME1_HYPOTHESE: hypothese de trading\nTHEME2_TITRE: titre\nTHEME2_IMPACT: FORT ou MODERE ou FAIBLE\nTHEME2_ACTIFS: actifs\nTHEME2_SYNTHESE: une phrase\nTHEME2_HYPOTHESE: hypothese de trading\nTHEME3_TITRE: titre\nTHEME3_IMPACT: FORT ou MODERE ou FAIBLE\nTHEME3_ACTIFS: actifs\nTHEME3_SYNTHESE: une phrase\nTHEME3_HYPOTHESE: hypothese de trading\nVIGIL1: point de vigilance\nVIGIL2: point de vigilance"
async def get_news():
 headlines=[]
 async with httpx.AsyncClient(timeout=15) as c:
  for url in ["https://feeds.bloomberg.com/markets/news.rss","https://feeds.reuters.com/reuters/businessNews"]:
   try:
    r=await c.get(url,headers={"User-Agent":"Mozilla/5.0"})
    titles=re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>",r.text)+re.findall(r"<title>(.*?)</title>",r.text)
    headlines+=titles[1:6]
   except:pass
 return "\n".join(headlines[:12]) if headlines else "Marches mixtes. Politique Fed incertaine. Dollar stable. Or proche des sommets. Petrole volatil."
async def analyse(news):
 b={"model":"claude-haiku-4-5-20251001","max_tokens":2000,"system":AS,"messages":[{"role":"user","content":"Nous sommes le "+datetime.now().strftime("%d %B %Y")+". Voici les dernieres actualites financieres:\n\n"+news}]}
 async with httpx.AsyncClient(timeout=60) as c:
  r=await c.post("https://api.anthropic.com/v1/messages",headers={"Content-Type":"application/json","x-api-key":AK,"anthropic-version":"2023-06-01"},json=b)
  resp=r.json()
  return "".join(x["text"] for x in resp.get("content",[]) if x["type"]=="text")
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
 news=await get_news()
 structured=await analyse(news)
 data=parse(structured)
 await send(fmt(data))
asyncio.run(main())
