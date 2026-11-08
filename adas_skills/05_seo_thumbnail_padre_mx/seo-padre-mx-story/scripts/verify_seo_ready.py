#!/usr/bin/env python3
"""PADRE MX V3 SEO preflight: require final QA after two full audits, SHA-bound.
This mechanically validates file identity, not subjective story or visual quality.
"""
import argparse,hashlib,json,sys
from pathlib import Path

def sha(x):return hashlib.sha256(x).hexdigest()
def die(x):raise ValueError(x)
def run(n):
 qa=json.loads(n.qa_frozen.read_text('utf-8'));raw=n.script.read_bytes();raw.decode('utf-8','strict')
 if qa.get('schema')!='PADRE_MX_QA_FINAL_V3':die('Requires V3 FINAL QA, not previous one-repair frozen QA')
 canon={k:v for k,v in qa.items() if k!='manifest_sha256'}
 if sha(json.dumps(canon,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8'))!=qa.get('manifest_sha256'):die('FINAL QA seal modified')
 if qa.get('status')!='PASS_PUBLISH_READY' or qa.get('score',0)<95:die('FINAL QA is not PASS_PUBLISH_READY >=95')
 if qa.get('script_sha256')!=sha(raw):die('Final script differs from independently verified exact source')
 if qa.get('remaining_issues') or qa.get('new_issues'):die('FINAL QA contains unresolved/new issues')
 if not qa.get('round1_audit_sha256') or not qa.get('round2_audit_sha256'):die('Both independently frozen V3 audits are mandatory')
 if qa.get('round2_proof_sha256'):
  if not n.round2_proof:die('Second repair proof is required for finalized REPAIR2 manuscript')
  proof=n.round2_proof.read_bytes();p=json.loads(proof.decode('utf8'))
  if sha(proof)!=qa['round2_proof_sha256'] or p.get('schema')!='PADRE_MX_REPAIR_PROOF_V3' or p.get('repair_round')!=2 or p.get('revised_sha256')!=sha(raw):die('REPAIR2 proof does not match exact FINAL manuscript')
 outline=n.outline_file.read_bytes();outline.decode('utf8','strict');osh=sha(outline)
 vid=sha((n.title+'\n'+osh).encode('utf8'))[:16]
 if qa.get('locked_title')!=n.title or qa.get('outline_sha256')!=osh or qa.get('video_id')!=vid:die('Title/outline/video identity mismatch')
 if n.script_manifest:
  manifest=json.loads(n.script_manifest.read_text('utf8'))
  if manifest.get('title')!=n.title or manifest.get('video_id')!=vid:die('Script manifest mismatched')
 return {'pass':True,'publication_readiness':'READY','final_score':qa['score'],'video_id':vid,'final_script_sha256':sha(raw),'final_qa_sha256':sha(n.qa_frozen.read_bytes()),'two_rounds_required':True}
if __name__=='__main__':
 ap=argparse.ArgumentParser()
 ap.add_argument('--script',required=True,type=Path);ap.add_argument('--qa-frozen',required=True,type=Path)
 ap.add_argument('--outline-file',required=True,type=Path);ap.add_argument('--title',required=True)
 ap.add_argument('--round2-proof',type=Path);ap.add_argument('--script-manifest',type=Path)
 ns=ap.parse_args()
 try:result=run(ns)
 except (ValueError,TypeError,KeyError,OSError,UnicodeError,json.JSONDecodeError) as ex:result={'pass':False,'error':str(ex)}
 print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['pass'] else 2)
