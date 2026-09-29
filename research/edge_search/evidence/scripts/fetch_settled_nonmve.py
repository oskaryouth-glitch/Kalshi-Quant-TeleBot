import json, time, urllib.request, urllib.parse, sys
B="https://api.elections.kalshi.com/trade-api/v2/markets"
now=int(time.time()); out=[]; cur=None
for i in range(12):
    q={"status":"settled","mve_filter":"exclude","limit":1000,"min_close_ts":now-3*86400}
    if cur: q["cursor"]=cur
    for a in range(5):
        try:
            r=urllib.request.urlopen(B+"?"+urllib.parse.urlencode(q),timeout=60); d=json.load(r); break
        except Exception as e:
            print("retry",e,file=sys.stderr); time.sleep(2**a)
    out+=d.get("markets",[]); cur=d.get("cursor")
    print(i,len(out),file=sys.stderr); time.sleep(0.4)
    if not cur: break
json.dump(out,open("settled_nonmve.json","w"))
