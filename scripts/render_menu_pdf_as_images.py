#!/usr/bin/env python3
"""Render the five owner-approved BRAVIS menus to browser-friendly images.

Changes only /home/a4dev/bravis-ready on the Russian preview VPS.
Original PDFs are preserved in .menu-backups outside the public site.
"""
import argparse
import datetime
import json
import re
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path

ROOT = Path("/home/a4dev/bravis-ready")
MANIFEST = ROOT / "content/menu_media.json"
MEDIA = ROOT / "public/menu-media"
EXPECTED = ("seasonal", "main-front", "main-back", "business", "children")

def pgm_has_content(pdf, page, folder):
    target = folder / ("proof-%s-%d" % (pdf.stem, page))
    result = subprocess.run(
        ["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile",
         "-gray", "-scale-to", "350", str(pdf), str(target)],
        capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError("PDF preview failed: "+pdf.name+" "+result.stderr[-450:])
    data = target.with_suffix(".pgm").read_bytes()
    m = re.match(rb"P5\s+(\d+)\s+(\d+)\s+(\d+)\s", data)
    if not m:
        raise RuntimeError("Cannot verify PDF preview of "+pdf.name)
    width,height,maximum = map(int,m.groups())
    pixels=data[m.end():]
    if maximum!=255 or width*height<1000 or len(pixels)<width*height:
        raise RuntimeError("Invalid PDF preview of "+pdf.name)
    sample=pixels[::max(1,len(pixels)//15000)]
    return max(sample)-min(sample)>=20 and statistics.pstdev(sample)>2.5

def pages(pdf):
    result=subprocess.run(["pdfinfo",str(pdf)],capture_output=True,text=True,timeout=30)
    if result.returncode:
        raise RuntimeError("Cannot read PDF "+pdf.name+": "+result.stderr[-450:])
    m=re.search(r"^Pages:\s*(\d+)",result.stdout,re.M)
    if not m or not 1<=int(m.group(1))<=8:
        raise RuntimeError("Invalid or excessive PDF pages: "+pdf.name)
    return int(m.group(1))

def convert(pdf,key,title,out,proof):
    count=pages(pdf)
    result=[]
    for page in range(1,count+1):
        if not pgm_has_content(pdf,page,proof):
            print("WARNING: PDF page renders blank:",pdf.name,page)
            continue
        dest=out/("%s-page-%d"%(key,page))
        run=subprocess.run(["pdftoppm","-f",str(page),"-l",str(page),
            "-singlefile","-jpeg","-jpegopt","quality=91,optimize=y,progressive=y",
            "-scale-to","2300",str(pdf),str(dest)],capture_output=True,text=True,timeout=150)
        jpg=dest.with_suffix(".jpg")
        if run.returncode or not jpg.is_file() or jpg.stat().st_size<10000:
            raise RuntimeError("PDF conversion failed: "+pdf.name+" "+run.stderr[-450:])
        result.append({"title": title+((" — страница %d"%page) if count>1 else ""),
                       "url":"/menu-media/"+jpg.name,"format":"image"})
    if not result:
        raise RuntimeError("All pages of "+pdf.name+" render blank; original files may be defective. Site unchanged.")
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    if not shutil.which("pdftoppm") or not shutil.which("pdfinfo"):
        raise RuntimeError("Install poppler-utils first.")
    if not MANIFEST.is_file() or not MEDIA.is_dir():
        raise RuntimeError("Previously approved menu is missing.")
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    files=manifest.get("files",[])
    if len(files)!=5:
        raise RuntimeError("Exactly five previously approved menu files required.")
    chosen=[]
    for entry in files:
        url=entry.get("url","")
        if not url.startswith("/menu-media/") or "/" in url[len("/menu-media/"):]:
            raise RuntimeError("Unapproved media URL: "+url)
        path=MEDIA/Path(url).name
        if not path.is_file():
            raise RuntimeError("Approved menu file missing: "+url)
        chosen.append(path)
    if tuple(p.stem for p in chosen)!=EXPECTED:
        raise RuntimeError("Unexpected menu order or files: "+str([p.name for p in chosen]))
    print("PDF files:",[f.name for f in chosen if f.suffix.lower()==".pdf"])
    if not args.apply:
        print("DRY RUN complete; site unchanged")
        return
    stage=Path(tempfile.mkdtemp(prefix=".menu-pdf-render-",dir=str(ROOT)))
    try:
        output=stage/"menu-media"; output.mkdir()
        proof=stage/"proof";proof.mkdir()
        images=[]
        for entry,key,src in zip(files,EXPECTED,chosen):
            if src.suffix.lower()==".pdf":
                images.extend(convert(src,key,entry.get("title",key),output,proof))
            elif src.suffix.lower() in (".jpg",".jpeg",".png",".webp"):
                shutil.copy2(src,output/src.name)
                images.append(entry)
            else:
                raise RuntimeError("Unapproved file format: "+src.name)
        for i in images:
            path=output/Path(i["url"]).name
            if not path.is_file() or i.get("format")!="image":
                raise RuntimeError("Image or manifest invalid: "+i.get("url",""))
        backup=ROOT/".menu-backups"/("rendered-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        backup.mkdir(parents=True,exist_ok=False)
        shutil.copy2(MANIFEST,backup/"menu_media.json")
        shutil.move(str(MEDIA),str(backup/"previous-menu-media"))
        try:
            shutil.move(str(output),str(MEDIA))
            MANIFEST.write_text(json.dumps({
                "source":manifest.get("source",""),"selection":"owner-approved-raster-menu",
                "files":images},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        except BaseException:
            if MEDIA.exists():shutil.rmtree(MEDIA)
            shutil.move(str(backup/"previous-menu-media"),str(MEDIA))
            shutil.copy2(backup/"menu_media.json",MANIFEST)
            raise
        print("SUCCESS:",len(images),"menu images generated.")
        print("Original PDF backup:",backup)
    finally:
        shutil.rmtree(stage,ignore_errors=True)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("STOP:",str(exc))
        raise SystemExit(2)
