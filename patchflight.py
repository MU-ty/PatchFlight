"""PatchFlight: a coding-agent harness with replayable evidence."""
import argparse, json, os, shutil, subprocess, tempfile, time, urllib.request, uuid
from pathlib import Path

class Trace:
    def __init__(self, path): self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def emit(self, kind, **data):
        with self.path.open('a', encoding='utf8') as f: f.write(json.dumps({'time':time.time(),'kind':kind,**data}, ensure_ascii=False)+'\n')

def contained(root, name):
    p=(root/name).resolve()
    if not p.is_relative_to(root.resolve()) or '.git' in p.relative_to(root.resolve()).parts: raise ValueError('path outside workspace or git metadata')
    return p

def run_test(root, timeout):
    try:
        p=subprocess.run(['python','-m','unittest','discover','-s','tests'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
        return {'exit_code':p.returncode,'output':p.stdout[-12000:]}
    except subprocess.TimeoutExpired: return {'exit_code':124,'output':'test timed out'}

def call_model(messages, model, base_url, key):
    body=json.dumps({'model':model,'messages':messages,'temperature':0}).encode()
    req=urllib.request.Request(base_url.rstrip('/')+'/chat/completions',data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=90) as r: return json.load(r)['choices'][0]['message']['content']

def execute(source, task, trace_path, model_fn, steps=8, timeout=20, evaluator=None):
    source=Path(source).resolve(); trace=Trace(trace_path); run_id=uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix='patchflight-') as tmp:
        root=Path(tmp)/'repo'; shutil.copytree(source,root,ignore=shutil.ignore_patterns('.git','__pycache__','.patchflight'))
        files=[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.stat().st_size<100000][:200]
        trace.emit('run_started',run_id=run_id,task=task,files=files)
        system='You are a coding agent. Respond ONLY with a JSON object. Actions: {"action":"read","path":"..."}, {"action":"write","path":"...","content":"entire file"}, {"action":"test"}, or {"action":"finish","summary":"..."}. Paths must be relative. Always run tests after editing. Repository files: '+json.dumps(files)
        messages=[{'role':'system','content':system},{'role':'user','content':task}]; changed=set(); last_test=None; dirty=False
        for step in range(steps):
            raw='{}'
            try:
                raw=model_fn(messages); trace.emit('model_response',step=step,content=raw)
                action=json.loads(raw); kind=action['action']; result={}
                if kind=='read': result={'content':contained(root,action['path']).read_text(encoding='utf8')[:30000]}
                elif kind=='write':
                    p=contained(root,action['path']); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(action['content'],encoding='utf8'); changed.add(action['path']); dirty=True; result={'written':action['path']}
                elif kind=='test': result=run_test(root,timeout); last_test=result; dirty=False
                elif kind=='finish':
                    if not changed or last_test is None or last_test['exit_code']!=0 or dirty: result={'error':'A change and a passing test after the final edit are required.'}
                    else:
                        patch=subprocess.run(['diff','-ruN',str(source),str(root),'--exclude=.git','--exclude=__pycache__','--exclude=.patchflight'],capture_output=True,text=True).stdout
                        evaluation = evaluator(root) if evaluator else None
                        trace.emit('run_finished',run_id=run_id,status='passed',summary=action.get('summary',''),patch=patch,changed=sorted(changed)); return {'status':'passed','patch':patch,'run_id':run_id,'evaluation':evaluation}
                else: result={'error':'unknown action'}
            except Exception as e: result={'error':f'{type(e).__name__}: {e}'}; kind='error'
            trace.emit('tool_result',step=step,action=kind,result=result)
            messages.extend([{'role':'assistant','content':raw}, {'role':'user','content':json.dumps(result,ensure_ascii=False)}])
        trace.emit('run_finished',run_id=run_id,status='exhausted',last_test=last_test); return {'status':'exhausted','run_id':run_id}

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run'); r.add_argument('repo'); r.add_argument('task'); r.add_argument('--trace',default='.patchflight/trace.jsonl'); r.add_argument('--model',default=os.getenv('MODEL','')); r.add_argument('--base-url',default=os.getenv('BASE_URL','https://api.openai.com/v1')); r.add_argument('--steps',type=int,default=8)
    v=sub.add_parser('replay'); v.add_argument('trace'); a=p.parse_args()
    if a.command=='replay':
        for line in Path(a.trace).read_text().splitlines(): print(json.dumps(json.loads(line),ensure_ascii=False,indent=2))
        return
    key=os.getenv('API_KEY')
    if not key or not a.model: p.error('Set API_KEY and MODEL (or --model)')
    print(json.dumps(execute(a.repo,a.task,a.trace,lambda m:call_model(m,a.model,a.base_url,key),steps=a.steps),ensure_ascii=False,indent=2))
if __name__=='__main__': main()

