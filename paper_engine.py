import json,urllib.request,datetime,os,time
from pathlib import Path
P=Path("paper_state.json")
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
def get(url):
 with urllib.request.urlopen(urllib.request.Request("https://api.kucoin.com/api/v1/"+url,headers={"User-Agent":"PaperLab/9.2"}),timeout=20) as r:\n  result=json.load(r)\n  if result.get("code")!="200000":raise RuntimeError("KuCoin API rejected request: "+str(result.get("code")))\n  return result["data"]
def event(s,msg):s["events"]=[{"time":utc(),"message":msg}]+s["events"][:79]
def equity(s,px):
 unreal=0
 for p in s["positions"]:
  price=px.get(p["symbol"],p["entry"]);p["mark"]=price
  p["unrealized_pnl"]=round(p["qty"]*(price-p["entry"])*p["direction"]-p["qty"]*price*.001-p["entry_fee"],4)
  unreal+=p["qty"]*(price-p["entry"])*p["direction"]-p["qty"]*price*.001
 s["equity"]=round(s["cash"]+sum(p["margin"] for p in s["positions"])+unreal,4)
def close(s,p,raw,reason):
 price=raw*(1-.0005*p["direction"]);gross=p["qty"]*(price-p["entry"])*p["direction"];fee=p["qty"]*price*.001
 net=gross-fee-p["entry_fee"];s["cash"]+=p["margin"]+gross-fee;s["realized_pnl"]+=net
 t=dict(p);t.update(exit=price,exit_time=utc(),exit_fee=fee,net_pnl=round(net,4),reason=reason)
 s["trades"]=[t]+s["trades"][:999];s["positions"].remove(p)
 event(s,"SIM CLOSE "+p["side"]+" "+p["symbol"]+" "+reason+" PNL "+str(round(net,2)))
def ema(a,n):
 v=a[0]
 for x in a[1:]:v=(2/(n+1))*x+(1-2/(n+1))*v
 return v
def run():
 s=json.loads(P.read_text())
 try:
  tick={x["symbol"]:x for x in get("market/allTickers")["ticker"] if x["symbol"].endswith("-USDT")}
  universe=["BTC","ETH","SOL","NEAR","LINK","XRP","ADA","DOGE","AVAX","SUI","BNB","LTC","DOT","UNI","AAVE","FIL","ICP","APT"]
  px={a+"-USDT":float(tick[a+"USDT"]["last"]) for a in universe if a+"USDT" in tick}
  if len(px)<12:raise RuntimeError("Insufficient live prices")
  s["last_market_data"]=utc();s["status"]="RUNNING";s["error"]=None
  day=utc()[:10]
  if s["day"]!=day:s["day"]=day;s["day_start_equity"]=s["equity"];s["halted"]=False
  for p in list(s["positions"]):
   raw=px.get(p["symbol"])
   if raw is None:continue
   if p["direction"]*(raw-p["stop"])<=0:close(s,p,raw,"STOP")
   elif p["direction"]*(raw-p["take"])>=0:close(s,p,raw,"TARGET")
   elif (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(p["entry_time"])).total_seconds()>172800:close(s,p,raw,"TIME EXIT")
  equity(s,px)
  if s["equity"]<=s["day_start_equity"]*.98:
   s["halted"]=True
   for p in list(s["positions"]):
    if p["symbol"] in px:close(s,p,px[p["symbol"]],"DAILY HALT")
   equity(s,px)
  candidates=[]
  if not s["halted"]:
   liquid=sorted([k for k in px if float(tick[k]["volValue"])>=20000000],key=lambda k:float(tick[k]["quoteVolume"]),reverse=True)[:12]
   for sym in liquid:
    if any(p["symbol"]==sym for p in s["positions"]):continue
    try:
     rows=sorted(get("market/candles?symbol="+sym+"&type=1hour"),key=lambda row:int(row[0]))[:-1][-54:]
     if len(rows)<35:continue
     c=[float(x[2]) for x in rows];h=[float(x[3]) for x in rows];l=[float(x[4]) for x in rows]
     mom=c[-1]/c[-4]-1;e9=ema(c,9);e21=ema(c,21)
     direction=1 if e9>e21 and mom>.008 else (-1 if e9<e21 and mom<-.008 else 0)
     atr=sum(max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(-14,0))/14
     if direction and atr>0 and atr/c[-1]<.055 and abs(mom)<.075:candidates.append((abs(mom),sym,direction,atr))
    except Exception as e:event(s,"History unavailable "+sym+" "+type(e).__name__)
   for _,sym,direction,atr in sorted(candidates,reverse=True):
    if len(s["positions"])>=3:break
    raw=px[sym];fill=raw*(1+.0005*direction);dist=max(1.7*atr,raw*.012)
    amount=min(s["equity"]*.20,s["equity"]*.005/(dist/fill),s["cash"]*.95)
    if amount<30:continue
    fee=amount*.001
    if amount+fee>s["cash"]:continue
    p={"id":str(int(time.time()*1000))+sym,"symbol":sym,"side":"LONG" if direction==1 else "SHORT","direction":direction,"qty":amount/fill,"entry":fill,"entry_time":utc(),"margin":amount,"entry_fee":fee,"stop":fill-direction*dist,"take":fill+direction*dist*2,"fill_type":"SIMULATED"}
    s["cash"]-=amount+fee;s["positions"].append(p);event(s,"SIM OPEN "+p["side"]+" "+sym+" notional "+str(round(amount,2)))
  equity(s,px);s["equity_curve"]=(s["equity_curve"]+[{"time":utc(),"equity":s["equity"]}])[-3000:]
  s["run_count"]+=1;event(s,"Cycle completed; equity "+str(s["equity"]))
 except Exception as e:s["status"]="DATA_ERROR";s["error"]=str(e);event(s,"DATA ERROR "+str(e))
 s["last_run"]=utc();P.write_text(json.dumps(s,indent=2,allow_nan=False)+"\n")
if __name__=="__main__":run()
