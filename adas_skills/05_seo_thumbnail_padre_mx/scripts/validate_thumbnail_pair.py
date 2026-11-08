#!/usr/bin/env python3
"""Mechanical PNG gates for PADRE MX Step6 two-image deliverables.
Checks dimensions, RGB key, empty text side, and right-side visible subject.
Does NOT establish whether the person or pose matches; independent visual QA needed.
"""
import argparse, json, sys
from pathlib import Path

def check(thumbnail:Path, green:Path):
 errors=[]; metrics={}
 if thumbnail.name!='THUMBNAIL.png':errors.append('Final thumbnail MUST be named THUMBNAIL.png')
 if green.name!='THUMBNAIL-NENXANH.png':errors.append('Greenscreen MUST be named THUMBNAIL-NENXANH.png')
 try:
  from PIL import Image
 except ImportError:
  return {'pass':False,'errors':['Pillow is required for mechanical PNG validation; do not claim PASS'],'metrics':metrics}
 for p in (thumbnail,green):
  if not p.is_file():errors.append('File does not exist: '+str(p))
 if errors:return {'pass':False,'errors':errors,'metrics':metrics}
 try:
  with Image.open(thumbnail) as src:
   metrics['thumbnail_format']=src.format; dims_a=src.size
  with Image.open(green) as src:
   metrics['green_format']=src.format; dims_b=src.size
   key_image=src.convert('RGB')
 except Exception as e:return {'pass':False,'errors':['Cannot read image: '+str(e)],'metrics':metrics}
 if metrics['thumbnail_format']!='PNG' or metrics['green_format']!='PNG':errors.append('Both outputs must be real PNG images')
 metrics['thumbnail_dimensions']=dims_a;metrics['green_dimensions']=dims_b
 if dims_a!=dims_b:errors.append('Dimension mismatch: the SAME portrait coordinates require the SAME canvas size')
 w,h=dims_b
 if w<1280 or h<720 or abs(w/h-16/9)>0.002:errors.append('Both images must be 16:9 and >=1280x720')
 # Use small subsampled image for constant-color QA (not OCR).
 sample=key_image.resize((240,135),Image.Resampling.NEAREST)
 px=sample.load(); x_cut=int(240*0.55)
 left=[px[x,y] for y in range(135) for x in range(x_cut)]
 right=[px[x,y] for y in range(135) for x in range(int(240*0.70),240)]
 key=(0,255,0)
 ratio=sum(1 for x in left if x==key)/len(left)
 subject_ratio=sum(1 for x in right if x!=key)/len(right)
 metrics['left_exact_key_ratio']=round(ratio,5)
 metrics['right_non_green_ratio']=round(subject_ratio,5)
 if ratio<0.985:errors.append('Left 55% background must be uniformly exact #00FF00; observed key ratio '+str(round(ratio,5)))
 if subject_ratio<0.18:errors.append('Subject missing/too small on right 30% of canvas')
 return {'pass':not errors,'errors':errors,'metrics':metrics,'manual_review_required':['same exact person/wardrobe/expression','same cutout size, x/y coordinates and pose','clean hair and silhouette; no green spill','Spanish spelling and thumbnail readability']}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--thumbnail',type=Path,required=True);ap.add_argument('--green',type=Path,required=True);ns=ap.parse_args()
 res=check(ns.thumbnail,ns.green);print(json.dumps(res,ensure_ascii=False,indent=2));sys.exit(0 if res['pass'] else 2)
