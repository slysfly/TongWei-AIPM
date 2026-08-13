#!/bin/bash
SRC="/home/ubuntu/.openclaw/workspace/twzx-website"
DST="$SRC/geo"
SM="$SRC/sitemap.xml"
mkdir -p "$DST"
python3 - << 'PY'
import os, json, urllib.request, urllib.parse
API="https://api.github.com/repos/slysfly/TongWei-AIPM/contents/geo?ref=main"
dst="/home/ubuntu/.openclaw/workspace/twzx-website/geo"
sm="/home/ubuntu/.openclaw/workspace/twzx-website/sitemap.xml"
os.makedirs(dst, exist_ok=True)
req=urllib.request.Request(API, headers={"User-Agent":"geo-pull"})
try:
    items=json.load(urllib.request.urlopen(req, timeout=30))
except Exception as e:
    print("geo_pull list fail:", e); raise SystemExit(0)
n=0
for it in items:
    name=it.get("name","")
    if not name.endswith(".html"): continue
    path=it.get("path","")
    raw="https://raw.githubusercontent.com/slysfly/TongWei-AIPM/main/"+urllib.parse.quote(path)
    fn=os.path.basename(path)
    try:
        r=urllib.request.urlopen(urllib.request.Request(raw, headers={"User-Agent":"geo-pull"}), timeout=30)
        data=r.read()
        with open(os.path.join(dst, fn), "wb") as f: f.write(data)
        print("pulled", fn, len(data), "bytes"); n+=1
    except Exception as e:
        print("pull fail", fn, e)
print("geo_pull pulled", n, "html files")
# 把 geo/*.html 自动补进官网 sitemap（已存在则跳过），让 Bing/IndexNow 也能收录官网镜像
try:
    with open(sm, encoding="utf-8") as f: txt=f.read()
    added=""
    for fn in os.listdir(dst):
        if not fn.endswith(".html"): continue
        loc="https://www.twzx.bj.cn/geo/"+urllib.parse.quote(fn)
        if loc not in txt:
            added+="  <url>\n    <loc>%s</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.6</priority>\n  </url>\n"%loc
    if added:
        txt=txt.replace("</urlset>", added+"</urlset>")
        with open(sm,"w",encoding="utf-8") as f: f.write(txt)
        print("sitemap +geo urls added")
    else:
        print("sitemap geo urls already present")
except Exception as e:
    print("sitemap update skip:", e)
PY
/usr/local/bin/sync-twzx.sh
echo "geo_pull done at $(date)"
