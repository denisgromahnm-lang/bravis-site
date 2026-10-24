#!/usr/bin/env python3
"""Collect authorized BRAVIS restaurant imagery and approved menus.
Runs on GitHub Actions; no passwords and no AI/OCR. Requires Pillow, poppler-utils.
Only approved print files are used for menus. No new photos are assigned to dishes.
"""
import argparse, datetime, hashlib, json, re, subprocess, tempfile, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageOps, ImageStat
ROOT=Path(__file__).resolve().parents[1]
API="https://cloud-api.yandex.net/v1/disk/public/resources"
FIRST="https://disk.yandex.ru/d/9up8OtV4hsMOZg"
SECOND="https://disk.yandex.ru/d/mM7bPzFGD0o2WA"
MENU_CATEGORIES=[
 ("seasonal","Сезонное меню"),
 ("main-front","Основное меню"),
 ("main-back","Бар и напитки"),
 ("business","Бизнес-ланч"),
 ("children","Детское меню")
]
def normalize(s):
    return re.sub(r"[\s._\-\u2013\u2014]+","",unicodedata.normalize("NFKC",str(s)).lower().replace("ё","е"))
def req(share,path=None,download=False,offset=0):
    params={"public_key":share}
    if path is not None:params["path"]=path
    if not download:params.update({"limit":100,"offset":offset})
    url=API+("/download" if download else "")+"?"+urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"BRAVIS-public-media/2.0"}),timeout=35) as f:
        return json.load(f)
def scan(share):
    files=[];queue=[(None,0)];calls=0
    while queue and calls<110 and len(files)<2500:
        path,depth=queue.pop(0)
        if depth>6:continue
        offset=0
        while calls<110:
            info=req(share,path=path,offset=offset);calls+=1
            if info.get("type")!="dir":break
            embedded=info.get("_embedded",{})
            items=embedded.get("items",[])
            for i in items:
                name=i.get("name","")
                full=i.get("path","")
                if i.get("type")=="dir":
                    if any(w in normalize(name) for w in ("исходники","исходник","архив","видео","video","raw")):continue
                    queue.append((full,depth+1))
                elif i.get("type")=="file":
                    files.append(i)
            offset+=len(items)
            if not items or offset>=embedded.get("total",offset):break
    print("PUBLIC API:",share,"files:",len(files),"requests:",calls)
    return files
def match(item,key):
    name=item.get("name",""); low=normalize(Path(name).stem); ext=Path(name).suffix.lower()
    path=normalize(item.get("path",""))
    if "типограф" not in path:return False
    if key=="seasonal":
        return ext in (".jpg",".jpeg",".png") and "bravis" in low and "сезон" in low and "превью" in low
    if key=="main-front":
        return ext==".pdf" and low.startswith("менюосновное") and "печат" in low and "(1)" not in name
    if key=="main-back":
        return ext in (".jpg",".jpeg",".png") and low.startswith("менюосновное") and "оборот" in low
    if key=="business":
        return ext==".pdf" and "менюбизнес" in low and "печат" in low
    if key=="children":
        return ext==".pdf" and low=="менюдетское"
    return False
def download(share,item,dest,max_size=32*1024**2):
    info=req(share,path=item.get("path"),download=True);url=info.get("href","")
    parsed=urllib.parse.urlparse(url)
    host=parsed.hostname or ""
    if parsed.scheme!="https" or not (host.endswith(".yandex.ru") or host.endswith(".yandex.net") or host.endswith(".yandex.com")):
        raise ValueError("Unsafe download host")
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"BRAVIS-public-media/2.0"}),timeout=75) as r,open(dest,"wb") as out:
        count=0
        while True:
            block=r.read(1<<20)
            if not block:break
            count+=len(block)
            if count>max_size:raise ValueError("Media file too large")
            out.write(block)
def optimize(src,dest,max_px=2400):
    with Image.open(src) as img:
        img=ImageOps.exif_transpose(img)
        img.thumbnail((max_px,max_px))
        img.convert("RGB").save(dest,"JPEG",quality=84,optimize=True,progressive=True)
def proof(pdf,pageno,folder):
    dst=folder/("proof"+str(pageno))
    cmd=["pdftoppm","-f",str(pageno),"-l",str(pageno),"-singlefile","-gray","-scale-to","360","-png",str(pdf),str(dst)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=80)
    with Image.open(dst.with_suffix(".png")) as im:
        sample=im.convert("L").resize((48,48))
        pixels=list(sample.getdata())
        if max(pixels)-min(pixels)<18:return None
        return bytes(pixels)
def similarity(a,b):
    return sum(abs(x-y) for x,y in zip(a,b))/len(a) if a is not None and b is not None else 999
def pdf_unique(pdf,key,folder,max_pages=32,max_unique=8):
    meta=subprocess.run(["pdfinfo",str(pdf)],text=True,capture_output=True,timeout=25,check=True).stdout
    m=re.search(r"^Pages:\s*(\d+)",meta,re.M)
    if not m or not (1<=int(m.group(1))<=max_pages):raise ValueError("Unsupported PDF page count: "+pdf.name)
    n=int(m.group(1));fingerprints=[];choices=[]
    for ix in range(1,n+1):
        finger=proof(pdf,ix,folder)
        if finger is None:continue
        if any(similarity(finger,old)<=3 for old in fingerprints):continue
        fingerprints.append(finger);choices.append(ix)
        # Owner confirmed the 2 main-front pages and 20 business pages are repeated.
        # Keep one readable source page rather than displaying near-identical scans.
        if key in ("main-front","business"): break
        if len(choices)>=max_unique:break
    if not choices:raise RuntimeError("All menu pages rendered blank: "+pdf.name)
    print("MENU",key,"PDF pages",n,"unique",len(choices))
    return choices
def extract_text(pdf,path):
    result=subprocess.run(["pdftotext","-layout",str(pdf),str(path)],capture_output=True,text=True,timeout=30)
    if result.returncode:print("Text layer unavailable",pdf.name)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--media",choices=["all","menus","interior"],default="all")
    ap.add_argument("--dry-run",action="store_true")
    args=ap.parse_args()
    if args.media in ("all","menus"):
        files=scan(SECOND)
        chosen=[]
        for key,label in MENU_CATEGORIES:
            matches=[f for f in files if match(f,key)]
            if len(matches)!=1:
                raise RuntimeError(f"Expected one approved {label} file, found {len(matches)}: {[m.get('name') for m in matches]}")
            chosen.append((key,label,matches[0]))
            print("APPROVED:",label,matches[0].get("name"))
        if not args.dry_run:
            out=ROOT/"public/menu-media";out.mkdir(parents=True,exist_ok=True)
            extracted=ROOT/"content/menu-source-extract";extracted.mkdir(parents=True,exist_ok=True)
            manifest=[]
            with tempfile.TemporaryDirectory() as td:
                t=Path(td)
                for key,label,item in chosen:
                    ext=Path(item["name"]).suffix.lower()
                    raw=t/(key+ext)
                    download(SECOND,item,raw)
                    page_urls=[]
                    if ext==".pdf":
                        extract_text(raw,extracted/(key+".txt"))
                        picks=pdf_unique(raw,key,t)
                        for j,index in enumerate(picks,1):
                            frame=t/(key+"-"+str(j))
                            subprocess.run(["pdftoppm","-f",str(index),"-l",str(index),"-singlefile",
                                            "-scale-to","2100","-png",str(raw),str(frame)],
                                           check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=120)
                            dest=out/(key+("-"+str(j) if len(picks)>1 else "")+".jpg")
                            optimize(frame.with_suffix(".png"),dest)
                            page_urls.append("/menu-media/"+dest.name)
                    else:
                        dest=out/(key+".jpg")
                        optimize(raw,dest)
                        page_urls.append("/menu-media/"+dest.name)
                    manifest.append({"group":key,"title":label,"format":"images","url":page_urls[0],"pages":page_urls,
                                     "source_name":item["name"]})
            (ROOT/"content/menu_media.json").write_text(json.dumps({
                "selection":"owner-approved-print-menu","source":SECOND,"files":manifest
            },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print("MENU READY:",len(manifest),"groups /",sum(len(x["pages"]) for x in manifest),"unique pages")
    if args.media in ("all","interior"):
        files=scan(FIRST)
        eligible=[f for f in files if any(t in f.get("path","").lower() for t in ["фото заведения внутри и снаружи"]) and
                  Path(f.get("name","").lower()).suffix in (".jpg",".jpeg",".png",".webp") and
                  isinstance(f.get("size"),int) and f["size"]<=15*1024**2]
        eligible.sort(key=lambda f:f.get("name","").lower())
        print("INTERIOR CANDIDATES",len(eligible))
        if not eligible:raise RuntimeError("Restaurant interior folder unavailable; no surrogate dish photography")
        if not args.dry_run:
            dest=ROOT/"public/uploads";dest.mkdir(parents=True,exist_ok=True)
            paths=[]
            with tempfile.TemporaryDirectory() as td:
                for ix,item in enumerate(eligible[:12],1):
                    src=Path(td)/("interior-"+str(ix)+Path(item["name"]).suffix.lower())
                    try:download(FIRST,item,src,15*1024**2)
                    except Exception as ex:
                        print("SKIP photo",item["name"],str(ex)[:80]);continue
                    jpg=dest/("bravis-interior-"+str(ix).zfill(2)+".jpg")
                    optimize(src,jpg,max_px=2000)
                    paths.append("/uploads/"+jpg.name)
            if not paths:raise RuntimeError("No restaurant photos downloaded")
            gallery={"hero":paths[0],"interior":paths[min(1,len(paths)-1)],
                     "events":paths[min(2,len(paths)-1)],"food":"",
                     "gallery":paths[3:10] or paths[:3]}
            (ROOT/"content/gallery.json").write_text(json.dumps(gallery,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print("INTERIOR READY:",len(paths),"; food photo intentionally blank")
if __name__=="__main__":
    main()
