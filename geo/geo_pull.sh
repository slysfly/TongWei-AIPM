#!/bin/bash
SRC="/home/ubuntu/.openclaw/workspace/twzx-website"
DST="$SRC/geo"
SM="$SRC/sitemap.xml"
mkdir -p "$DST"
python3 - << 'PYEOF'
import os, json, urllib.request, urllib.parse, time, base64

API="https://api.github.com/repos/slysfly/TongWei-AIPM/contents/geo?ref=main"
DST="/home/ubuntu/.openclaw/workspace/twzx-website/geo"
SM="/home/ubuntu/.openclaw/workspace/twzx-website/sitemap.xml"

def get(url, retries=4, timeout=30):
    last=None
    for i in range(retries):
        try:
            req=urllib.request.Request(url, headers={"User-Agent":"geo-pull","Accept":"application/vnd.github+json"})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:
            last=e
            time.sleep(2*(i+1))
    raise last

try:
    items=json.loads(get(API))
except Exception as e:
    print("geo_pull list fail:", e); raise SystemExit(0)

n=0
for it in items:
    name=it.get("name","")
    if not name.endswith(".html"): continue
    file_api=it.get("url")  # API url for this file (avoids raw.githubusercontent.com timeouts)
    if not file_api: continue
    try:
        data=json.loads(get(file_api))
        b64=data.get("content","")
        raw=base64.b64decode(b64)
        with open(os.path.join(DST, name),"wb") as f: f.write(raw)
        print("pulled", name, len(raw), "bytes"); n+=1
    except Exception as e:
        print("pull fail", name, e)
print("geo_pull pulled", n, "html files")

# 自动把 geo/*.html 写入官网 sitemap（已存在则跳过）
try:
    with open(SM, encoding="utf-8") as f: txt=f.read()
    added=""
    for fn in os.listdir(DST):
        if not fn.endswith(".html"): continue
        loc="https://www.twzx.bj.cn/geo/"+urllib.parse.quote(fn)
        if loc not in txt:
            added+="  <url>\n    <loc>%s</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.6</priority>\n  </url>\n"%loc
    if added:
        txt=txt.replace("</urlset>", added+"</urlset>")
        with open(SM,"w",encoding="utf-8") as f: f.write(txt)
        print("sitemap +geo urls added")
    else:
        print("sitemap geo urls already present")
except Exception as e:
    print("sitemap update skip:", e)
PYEOF
/usr/local/bin/sync-twzx.sh
echo "geo_pull done at $(date)"
