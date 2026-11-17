#!/usr/bin/env python3
"""Apply the pinned CPA runtime integration on the existing 2C/4GB host.

Run on the Kubernetes host from this directory. Private configuration, auth
files, plugin binaries and usage databases are never uploaded or overwritten.
"""
import base64, hashlib, json, os, pathlib, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
spec = json.loads((HERE/'runtime.json').read_text())
mem_kib = int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))
if os.cpu_count() != 2 or not 3_000_000 < mem_kib < 5_000_000:
    sys.exit('Refusing deployment: expected the Tencent Singapore 2C/4GB host')
k = ['sudo','-n','kubectl','-n',spec['namespace']]
def get(kind,name): return json.loads(subprocess.check_output(k+['get',kind,name,'-o','json']))
deployment = get('deployment',spec['deployment'])
selector = ','.join(key+'='+value for key,value in deployment['spec']['selector']['matchLabels'].items())
pods = json.loads(subprocess.check_output(k+['get','pods','-l',selector,'-o','json']))['items']
ready = [p for p in pods if p['status']['phase']=='Running' and all(c.get('ready') for c in p['status'].get('containerStatuses',[]))]
if len(ready)!=1: sys.exit('Expected one ready CPA pod')
pod = ready[0]['metadata']['name']
source = (HERE/'start-egress.py').read_bytes()
revision = sys.argv[1] if len(sys.argv)>1 else spec['release']
payload = {'source':base64.b64encode(source).decode(),'expected_core':spec['core_sha256'],'revision':revision}
remote = '''
from pathlib import Path
import base64,hashlib,json,os,shutil,socket,subprocess,sys,time
data=json.loads(sys.argv[1])
root=Path('/home/node/.cli-proxy-api/gemini-egress')
core=Path('/home/node/.openclaw/workspace/run/cliproxyapi/cli-proxy-api')
assert hashlib.sha256(core.read_bytes()).hexdigest()==data['expected_core'], 'Unexpected CPA binary; no changes made'
assert (root/'config.yaml').is_file() and (root/'mihomo').is_file(), 'Existing private egress setup is required'
source=base64.b64decode(data['source']);target=root/'start.py'
if not target.exists() or target.read_bytes()!=source:
    if target.exists(): shutil.copy2(target,root/('start.py.bak-'+str(int(time.time()))))
    temp=root/'start.py.next';temp.write_bytes(source);temp.chmod(0o700);temp.replace(target)
subprocess.run(['python3',str(target)],check=True)
with socket.create_connection(('127.0.0.1',17897),5): pass
with socket.create_connection(('127.0.0.1',8317),5): pass
auths=[]
for f in Path('/home/node/.cli-proxy-api').glob('antigravity-*.json'):
    j=json.loads(f.read_text())
    if not j.get('disabled'): auths.append(j)
assert auths and all(j.get('proxy_url')=='http://127.0.0.1:17897' for j in auths), 'An enabled Antigravity account is missing its proxy setting'
print('Pinned core, proxy and '+str(len(auths))+' enabled Antigravity account routes verified')
'''
subprocess.run(k+['exec','-i',pod,'--','python3','-',json.dumps(payload)],input=remote,text=True,check=True)
cm = get('configmap',spec['startup_configmap'])
startup=cm['data']['start_gateway.sh']
line='  python3 /home/node/.cli-proxy-api/gemini-egress/start.py\n'
if line.strip() not in startup:
    needle='start_cliproxyapi() {\n'
    assert startup.count(needle)==1, 'Unexpected startup format'
    new=startup.replace(needle,needle+line,1)
    subprocess.run(['sh','-n'],input=new,text=True,check=True)
    backup=pathlib.Path.home()/'.cpa-maintenance';backup.mkdir(mode=0o700,exist_ok=True)
    f=backup/('startup-before-runtime-sync-'+str(int(time.time()))+'.json');f.write_text(json.dumps(cm));f.chmod(0o600)
    patch=[{'op':'test','path':'/metadata/resourceVersion','value':cm['metadata']['resourceVersion']},{'op':'replace','path':'/data/start_gateway.sh','value':new}]
    subprocess.run(k+['patch','configmap',spec['startup_configmap'],'--type=json','--patch-file=/dev/stdin'],input=json.dumps(patch),text=True,check=True)
subprocess.run(k+['exec','-i',pod,'--','sh','-c','umask 077; cat > /home/node/.cli-proxy-api/runtime-release.json'],input=json.dumps({'revision':revision,'core_sha256':spec['core_sha256'],'supervisor_sha256':hashlib.sha256(source).hexdigest()}),text=True,check=True)
print('CPA runtime integration deployed: '+revision)
