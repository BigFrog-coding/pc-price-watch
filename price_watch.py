import argparse, json, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent
RETAILERS = {"Amazon":("amazon",), "Best Buy":("best buy","bestbuy"), "Micro Center":("micro center","microcenter"), "Newegg":("newegg",), "Costco":("costco",), "Sam's Club":("sam's club","sams club","samsclub"), "Walmart":("walmart",), "B&H Photo Video":("b&h photo","bh photo","bhphotovideo"), "Adorama":("adorama",), "Direct PC manufacturers":("cyberpowerpc","ibuypower","lenovo","hp.com","msi.com","nzxt","maingear","origin pc","digital storm")}
USED = ("refurbished","renewed","open box","open-box","pre-owned","preowned","used -","used condition","for parts","not working")

def norm(x):
    return re.sub(r"[^a-z0-9]+"," ",str(x or "").lower()).strip()

def parse_price(item):
    x=item.get("extracted_price")
    if isinstance(x,(int,float)): return float(x)
    for x in (item.get("price"),item.get("alternative_price")):
        m=re.search(r"\$?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",str(x or ""))
        if m: return float(m.group(1).replace(",",""))
    return None

def retailer(source):
    s=norm(source)
    for name,aliases in RETAILERS.items():
        if any(norm(a) in s for a in aliases): return name
    return None

def text_of(item):
    fields=[item.get(k,"") for k in ("title","snippet","description","source","second_hand_condition","tag","badge","old_price")]
    if isinstance(item.get("extensions"),list): fields+=item["extensions"]
    return " ".join(str(x) for x in fields if x is not None)

def has_ram_32gb_ddr5(text):
    n=norm(text)
    return bool(re.search(r"\b32\s*gb\b",n) and "ddr5" in n)

def has_at_least_1tb_ssd(text):
    n=norm(text)
    if not re.search(r"\b(ssd|nvme|m 2)\b",n): return False
    if any(float(x)>=1 for x in re.findall(r"\b(\d+(?:\.\d+)?)\s*tb\b",n)): return True
    return any(int(x)>=1000 for x in re.findall(r"\b(\d{3,5})\s*gb\b",n))

def has_cpu_liquid_cooling(text):
    n=norm(text)
    return any(x in n for x in ("liquid cooled","water cooled","aio liquid","aio cooler","240mm","280mm","360mm","radiator","custom loop"))

def has_gpu_liquid_cooling(text):
    n=norm(text)
    return any(x in n for x in ("liquid cooled gpu","water cooled gpu","liquid cooled graphics","water cooled graphics","aorus waterforce","waterforce","hydro copper","hybrid gpu","custom loop","full loop"))

def has_m2_or_nvme(text):
    n=norm(text)
    return "nvme" in n or "m 2" in n

def supported_gpu(text,cfg):
    n=norm(text)
    return next((x for x in cfg.get("pc_gpu_models",[]) if norm(x) in n),None)

def evaluate(category,item,cfg):
    price=parse_price(item); shop=retailer(item.get("source","")); title=str(item.get("title","Unknown product")).strip()
    text=text_of(item); n=norm(text)
    url=next((item.get(k) for k in ("product_link","link","product_page") if isinstance(item.get(k),str) and item[k].startswith(("http://","https://"))),None)
    condition=norm(item.get("second_hand_condition",""))
    if price is None or not shop or not url: return None
    if not cfg.get("allow_used_or_refurbished",False) and ((condition and condition not in ("new","brand new")) or any(norm(x) in n for x in USED)): return None
    limit=float(cfg[{"pc":"pc_price_limit","gpu":"gpu_price_limit","ram":"ram_price_limit"}[category]])
    notes=[]; matched=supported_gpu(text,cfg)
    if category=="pc":
        if not ("7800x3d" in n or "9800x3d" in n) or not matched or not has_ram_32gb_ddr5(text) or not has_at_least_1tb_ssd(text): return None
        if any(x in n for x in ("gaming laptop","notebook","playstation","xbox")): return None
        if not has_cpu_liquid_cooling(text): notes.append("CPU liquid cooling not confirmed")
        if not has_gpu_liquid_cooling(text): notes.append("GPU liquid cooling not confirmed")
        if not has_m2_or_nvme(text): notes.append("M.2/NVMe storage not confirmed")
        if any(x in n for x in ("air cooled gpu","air cooled graphics card","air cooled graphics")): return None
    elif category=="gpu":
        if "5070 ti" not in n or any(x in n for x in ("laptop","notebook","gaming desktop","gaming pc","prebuilt pc")) or not any(x in n for x in ("graphics card","video card","gpu","geforce")): return None
    elif category=="ram":
        if not has_ram_32gb_ddr5(text) or any(x in n for x in ("laptop memory","sodimm","so dimm","laptop ram")): return None
    else: return None
    promos=[]
    if any(x in n for x in ("clearance","markdown")): promos.append("CLEARANCE")
    if any(x in n for x in ("sale","special buy","special offer","flash sale","limited time")): promos.append("SALE/SPECIAL")
    if any(x in n for x in ("coupon","promo code","promotion","instant savings","rebate","discount")): promos.append("PROMO/COUPON")
    old=parse_price({"price":item.get("old_price")})
    if old is not None and old>price: promos.append("PRICE DROP SHOWN")
    return {"key":category+"|"+shop+"|"+norm(title),"category":category,"title":title,"retailer":shop,"price":round(price,2),"threshold":limit,"below_threshold":price<limit,"url":url,"review_notes":notes,"promotion_labels":list(dict.fromkeys(promos))}

def search(query,key):
    r=requests.get("https://serpapi.com/search.json",params={"engine":"google_shopping","q":query,"api_key":key,"gl":"us","hl":"en"},timeout=45); r.raise_for_status()
    data=r.json()
    if data.get("error"): raise RuntimeError(str(data["error"]))
    return data.get("shopping_results",[])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dry-run",action="store_true")
    ap.add_argument("--test-email",action="store_true",help="send a test email without running shopping searches")
    args=ap.parse_args()
    if args.test_email:
        api_key=os.getenv("RESEND_API_KEY","").strip()
        recipient=os.getenv("ALERT_EMAIL","").strip()
        if not api_key or not recipient:
            print("Missing RESEND_API_KEY or ALERT_EMAIL environment variable.",file=sys.stderr)
            return 1
        response=requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},
            json={"from":"PC Price Watch <onboarding@resend.dev>","to":[recipient],
                  "subject":"PC Price Watch email test",
                  "text":"Your PC Price Watch email configuration is working. This test did not run any shopping searches."},
            timeout=30,
        )
        if not response.ok:
            print("Test email failed (HTTP {}): {}".format(response.status_code,response.text[:1000]),file=sys.stderr)
            return 1
        print("Test email accepted by Resend for {}.".format(recipient))
        return 0
    key=os.getenv("SERPAPI_API_KEY","").strip()
    if not key: print("Missing SERPAPI_API_KEY; set .env or GitHub Actions secret.",file=sys.stderr); return 2
    cfg=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
    state_path=ROOT/"state.json"
    try: state=json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): state={"notified":{}}
    notified=state.setdefault("notified",{}); products=[]; errors=[]
    for cat in ("pc","gpu","ram"):
        try:
            r=search(cfg["queries"][cat],key)
            matches=[x for item in r if (x:=evaluate(cat,item,cfg)) is not None]
            products.extend(matches)
            price_matches=[p for p in matches if p["below_threshold"]]
            print("{}: {} search results; {} matched product/spec/retailer filters; {} below price threshold".format(cat,len(r),len(matches),len(price_matches)))
            for p in sorted(matches,key=lambda x:x["price"])[:10]:
                status="UNDER THRESHOLD" if p["below_threshold"] else "OVER/AT THRESHOLD"
                print("  CANDIDATE [{}] ${:.2f} (limit ${:.2f}) | {} | {} | {}".format(status,p["price"],p["threshold"],p["retailer"],p["title"][:100],p["url"]))
        except Exception as e: print("{} search failed: {}".format(cat,e),file=sys.stderr); errors.append(cat)
        time.sleep(float(cfg.get("seconds_between_searches",1)))
    unique={}
    for p in products:
        if p["key"] not in unique or p["price"]<unique[p["key"]]["price"]: unique[p["key"]]=p
    groups={"pc":[],"gpu":[],"ram":[]}
    for p in unique.values():
        old=notified.get(p["key"])
        if not p["below_threshold"]: notified.pop(p["key"],None); continue
        if old is None or (p["price"]<=float(old.get("last_alerted_price",p["price"]))-float(cfg.get("min_repeat_alert_drop",25))): groups[p["category"]].append(p)
    alerts=[]; now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    for cat,items in groups.items():
        for p in sorted(items,key=lambda x:x["price"])[:int(cfg.get("max_alerts_per_category_per_run",3))]:
            alerts.append(p); notified[p["key"]]={"last_alerted_price":p["price"],"last_alerted_at_utc":now}
    messages=[]
    for p in alerts:
        heading=("POTENTIAL PC DEAL" if p["review_notes"] else "PC PRICE WATCH") if p["category"]=="pc" else ("RTX 5070 Ti PRICE WATCH" if p["category"]=="gpu" else "32GB DDR5 PRICE WATCH")
        lines=[heading+" UNDER "+"$"+"{:,.0f}".format(p["threshold"])]
        if p["promotion_labels"]: lines.append("DEAL SIGNAL: "+", ".join(p["promotion_labels"])+" (verify at retailer)")
        lines += ["$"+"{:,.2f}".format(p["price"])+" at "+p["retailer"],p["title"][:115]]
        if p["review_notes"]: lines.append("VERIFY: "+"; ".join(p["review_notes"]))
        lines.append(p["url"]); messages.append("\n".join(lines))
    for m in messages: print("\n--- ALERT ---\n"+m+"\n-------------")
    dry=args.dry_run or os.getenv("DRY_RUN","").lower() in ("1","true","yes")
    if messages and not dry:
        api_key=os.getenv("RESEND_API_KEY","").strip()
        recipient=os.getenv("ALERT_EMAIL","").strip()
        if not api_key or not recipient:
            print("Missing RESEND_API_KEY or ALERT_EMAIL environment variable.",file=sys.stderr)
            return 1
        subject="PC Price Watch: {} new deal{}".format(len(messages),"" if len(messages)==1 else "s")
        body="New qualifying PC/component price alerts:\n\n"+"\n\n".join(messages)+"\n\nPrices and promotion signals can change; verify seller, condition, specs, and final checkout price."
        response=requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},
            json={"from":"PC Price Watch <onboarding@resend.dev>","to":[recipient],"subject":subject,"text":body},
            timeout=30,
        )
        if not response.ok:
            print("Email send failed (HTTP {}): {}".format(response.status_code,response.text[:1000]),file=sys.stderr)
            return 1
        print("Email alert sent to {}.".format(recipient))
    elif dry: print("DRY RUN: no email sent and alert history not saved.")
    else: print("No new qualifying price alerts.")
    if not dry: state_path.write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
    return 1 if len(errors)==3 else 0

if __name__=="__main__": raise SystemExit(main())
