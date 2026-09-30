#!/usr/bin/env python3
"""Personal wiki harness. Standard-library application; Ollama supplies inference only."""
from __future__ import annotations
import argparse, collections, hashlib, json, math, os, re, resource, shutil, sqlite3, sys, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
VAULT = ROOT / 'vault'
STATE = ROOT / '.local'
API = 'http://127.0.0.1:11435/api/'
MODEL = 'gemma4:e2b'
INSUFFICIENT = 'Insufficient evidence in the indexed sources to answer this question.'
STOP = set('a an the is are was were to of in on and or for from with what how why which does do can my me tell about it this that please'.split())

def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def request(endpoint, payload=None):
    # A literal loopback endpoint and disabled proxy handling prevent remote fallback.
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + endpoint, data=data, headers={'Content-Type':'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=240) as response:
            return json.load(response)
    except (OSError, urllib.error.URLError) as e:
        raise RuntimeError('Local Gemma is unavailable. Start ./scripts/serve.sh and install gemma4:e2b. No cloud fallback. ' + str(e)) from e

def identity():
    tags = request('tags')['models']
    model = next((m for m in tags if m['name'] == MODEL), None)
    if not model: raise RuntimeError('Download gemma4:e2b before going offline.')
    return {'model': MODEL, 'digest': model['digest'], 'details':model.get('details'), 'download_bytes':model['size'], 'runtime': request('version'), 'execution':'local'}

def generate(messages, structured=False):
    ident = identity()
    body = {'model':MODEL, 'messages':messages, 'stream':False, 'think':False,
            'keep_alive':'5m', 'options':{'num_ctx':4096, 'num_predict':650, 'temperature':0.2, 'seed':42}}
    if structured: body['format'] = 'json'
    start = time.perf_counter()
    result = request('chat', body)
    metrics = {'elapsed_seconds': round(time.perf_counter()-start,3),
               'cli_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               'loaded_models':request('ps').get('models',[]),
               **{k:result[k] for k in ['total_duration','load_duration','prompt_eval_count','eval_count','eval_duration'] if k in result}}
    return result['message']['content'].strip(), {'identity':ident,'metrics':metrics,'options':body['options'],'thinking':False}

def instructions(name): return (ROOT/'instructions'/f'{name}.md').read_text()

def tokens(text): return [x for x in re.findall(r'[a-z0-9]+',text.lower()) if x not in STOP and len(x)>1]

def passages(text, limit=1400):
    # Exact slices retain original punctuation and line numbering. No paraphrase enters retrieval.
    lines = text.splitlines(keepends=True)
    start, block = 1, ''
    for n,line in enumerate(lines,1):
        if block and len(block)+len(line)>limit:
            yield start, n-1, block
            start,block = n,''
        block += line
    if block: yield start,len(lines),block

def catalog():
    value=read_json(ROOT/'sources.json',[])
    if not value: raise RuntimeError('No sources configured. Add source entries to sources.json first.')
    return value

def source_path(entry):
    path=(ROOT/entry['path']).resolve()
    if not path.is_relative_to((VAULT/'raw').resolve()): raise ValueError('Sources must be inside vault/raw/.')
    if path.suffix.lower() not in ('.md','.txt'): raise ValueError('This CLI ingests UTF-8 Markdown and text. Convert other formats explicitly first.')
    if entry.get('sha256') and digest(path) != entry['sha256']:
        raise ValueError('Original source checksum changed; restore the original or register a new version.')
    return path

def note_path(entry):
    title=entry['title']; topic=entry['topic']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 -]{1,69}', title) or not 2<=len(title.split())<=6:
        raise ValueError('Note title must be a descriptive 2–6 word name with no path separators.')
    if not re.fullmatch(r'[A-Za-z][A-Za-z -]{0,30}',topic): raise ValueError('Invalid topic folder')
    return VAULT/'wiki'/topic/(title+'.md')

def rebuild():
    STATE.mkdir(exist_ok=True)
    con=sqlite3.connect(STATE/'retrieval.sqlite')
    try:
        with con:
            con.execute('CREATE TABLE IF NOT EXISTS chunks (source TEXT, path TEXT, start INTEGER, end INTEGER, passage TEXT)')
            con.execute('DELETE FROM chunks')
            for entry in catalog():
                path=source_path(entry)
                for start,end,passage in passages(path.read_text(encoding='utf-8')):
                    con.execute('INSERT INTO chunks VALUES (?,?,?,?,?)',(entry['id'],entry['path'],start,end,passage))
    finally: con.close()

def search(query, count=4):
    if not (STATE/'retrieval.sqlite').exists(): raise RuntimeError('Index missing. Run python3 wiki.py rebuild or ingest first.')
    con=sqlite3.connect(STATE/'retrieval.sqlite');con.row_factory=sqlite3.Row
    rows=[dict(r) for r in con.execute('SELECT * FROM chunks')];con.close()
    terms=set(tokens(query)); docs=[tokens(r['passage']) for r in rows]
    average=sum(map(len,docs))/max(len(docs),1)
    df=collections.Counter(t for doc in docs for t in set(doc))
    scored=[]
    for row,doc in zip(rows,docs):
        frequencies=collections.Counter(doc);score=0
        for term in terms:
            f=frequencies[term]
            if f:
                idf=math.log(1+(len(rows)-df[term]+.5)/(df[term]+.5))
                score+=idf*f*2.2/(f+1.2*(.25+.75*len(doc)/max(average,1)))
        if score: scored.append({**row,'score':round(score,4)})
    scored.sort(key=lambda r:-r['score'])
    return [dict(row,label=f'S{i}') for i,row in enumerate(scored[:count],1)]

def context(hits):
    return '\n\n'.join(f"[{h['label']}] {h['path']} lines {h['start']}-{h['end']}\n{h['passage']}" for h in hits)

def check_citations(answer,hits):
    labels=set(re.findall(r'\[(S\d+)\]',answer))
    allowed={h['label'] for h in hits}
    return {'labels':sorted(labels),'unknown':sorted(labels-allowed),
            'valid_labels':bool(labels) and not (labels-allowed),
            'semantic_support':'Requires source-by-source review; label validity is not proof of support.'}

def save(mode, record):
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=ROOT/'evidence'/'runs'/f'{stamp}-{mode}.json'
    record={'mode':mode,'execution':'local','timestamp':stamp,'offline_verified':False,**record}
    # Network disconnection is established by a separate demonstration, never inferred from local mode.
    write_json(target,record)
    print(f'\nSaved: {target.relative_to(ROOT)}')
    return target

def ask(question):
    hits=search(question)
    meta={}; raw=None
    if hits:
        messages=[{'role':'system','content':instructions('research')},
                  {'role':'user','content':f'QUESTION\n{question}\n\nSOURCE PASSAGES\n{context(hits)}'}]
        raw,meta=generate(messages)
        checks=check_citations(raw,hits)
        if raw.startswith('Insufficient evidence'):
            answer=INSUFFICIENT
        elif not checks['valid_labels']:
            answer=INSUFFICIENT
            checks['rejected_reason']='Missing or unknown citation labels; original output retained.'
        else: answer=raw
    else:
        answer=INSUFFICIENT;checks={'reason':'No matching passages; model not called.'}
    print(answer)
    for h in hits: print(f"[{h['label']}] {h['path']}:{h['start']}-{h['end']}")
    return save('ask',{'question':question,'retrieved':hits,'answer':answer,'raw_model_answer':raw,'citation_check':checks,**meta})

def chat():
    print('Wren | local Gemma 4 E2B | /notes QUERY, /reset, /exit. Chat is not research evidence.')
    history=[]
    while True:
        try: prompt=input('You> ').strip()
        except EOFError: break
        if prompt=='/exit': break
        if prompt=='/reset': history=[];print('Conversation cleared.');continue
        if not prompt: continue
        hits=[]
        # Deliberate, transparent retrieval: user chooses /notes; casual messages never search.
        if prompt.startswith('/notes '): hits=search(prompt[7:])
        bounded=[];size=0
        for message in reversed(history[-8:]):
            if size+len(message['content'])>5500: break
            bounded.insert(0,message);size+=len(message['content'])
        if len(prompt)>2500: print('Please shorten this message to 2500 characters.');continue
        user=prompt+(f'\n\nSOURCE PASSAGES\n{context(hits)}' if hits else '')
        messages=[{'role':'system','content':instructions('persona')},*bounded,{'role':'user','content':user}]
        answer,meta=generate(messages)
        checks=check_citations(answer,hits) if hits else None
        if hits and not checks['valid_labels']:
            shown='I could not verify source citations for that response. Try ask for a grounded answer.'
        else: shown=answer
        print('Wren> '+shown)
        if hits: print(context(hits))
        save('chat',{'input':prompt,'answer':shown,'raw_model_answer':answer,'retrieved':hits,'conversation_messages_used':len(bounded),'citation_check':checks,**meta})
        history.extend([{'role':'user','content':prompt},{'role':'assistant','content':shown}])

def render_note(entry, generated, entries):
    path=note_path(entry);path.parent.mkdir(parents=True,exist_ok=True)
    source=source_path(entry)
    body=f'---\nsource_id: {entry["id"]}\nsource_sha256: {digest(source)}\nreview_status: pending\n---\n\n# {entry["title"]}\n\n'
    body+=str(generated['summary'])+'\n\n## Details\n\n'+'\n'.join('- '+str(x) for x in generated['details'])
    raw_link=source.relative_to(VAULT).as_posix()
    body+=f'\n\n## Sources\n\n- [[{raw_link}|Original source]]\n- Publisher: {entry.get("publisher","Not specified")}\n'
    if entry.get('url'):body+=f'- [Original publication]({entry["url"]})\n'
    body+='\n## Related notes\n\n'
    by_id={e['id']:e for e in entries}
    for relationship in entry.get('related',[]):
        other=by_id[relationship['id']]
        body+=f'- [[{other["title"]}]] — {relationship["reason"]}\n'
    path.write_text(body)
    return path

def rebuild_landing(entries):
    text='# Personal Wiki\n\nA small, source-traceable knowledge base. Generated notes require review against their originals.\n'
    for topic in sorted({e['topic'] for e in entries}):
        text+=f'\n## {topic}\n\n'
        for entry in entries:
            if entry['topic']==topic and note_path(entry).exists():text+=f'- [[{entry["title"]}]] — {entry["description"]}\n'
    (VAULT/'index.md').write_text(text)

def ingest(selected, regenerate=False):
    entries=catalog(); paths=[note_path(e) for e in entries]
    if len(paths)!=len(set(paths)):raise ValueError('Two sources map to the same note. Curate/merge them explicitly.')
    target=Path(selected).resolve()
    if not target.exists():raise ValueError('Ingestion path does not exist.')
    ledger=read_json(STATE/'ingestion.json',{})
    selected_entries=[e for e in entries if source_path(e)==target or source_path(e).is_relative_to(target)]
    if not selected_entries:raise ValueError('No catalogued sources match this path; register them in sources.json.')
    for entry in selected_entries:
        path=source_path(entry);sha=digest(path);previous=ledger.get(entry['id'])
        if previous and previous['sha256']!=sha:raise ValueError('Original source changed. Preserve it and register a new source version explicitly.')
        if previous and note_path(entry).exists() and not regenerate:
            print(f'Unchanged; preserved reviewed note: {note_path(entry).relative_to(ROOT)}');continue
        start=time.perf_counter();text=path.read_text(encoding='utf-8')
        excerpt=text[:8000]
        raw,meta=generate([{'role':'system','content':instructions('ingest')},{'role':'user','content':f'Subject: {entry["title"]}\nSOURCE TEXT\n{excerpt}'}],True)
        generated=json.loads(raw)
        if not isinstance(generated.get('summary'),str) or not isinstance(generated.get('details'),list):raise ValueError('Invalid model summary JSON; no note saved.')
        destination=note_path(entry)
        if destination.exists():
            backup=ROOT/'evidence'/'note-backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')/destination.name
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,backup)
        render_note(entry,generated,entries)
        ledger[entry['id']]={'sha256':sha,'note':str(destination.relative_to(ROOT))}
        write_json(STATE/'ingestion.json',ledger)
        save('ingest',{'source':entry['path'],'sha256':sha,'note':str(destination.relative_to(ROOT)),
                      'source_characters':len(text),'characters_sent':len(excerpt),'truncated':len(text)>len(excerpt),
                      'generated':generated,'total_elapsed_seconds':round(time.perf_counter()-start,3),**meta})
    rebuild();rebuild_landing(entries)
    print('Original-source index and grouped wiki index rebuilt.')

def audit():
    entries=catalog(); errors=[]
    names=collections.Counter(p.stem for p in VAULT.rglob('*.md'))
    for entry in entries:
        path=note_path(entry)
        if not path.exists(): errors.append(f'Missing {path.name}');continue
        text=path.read_text()
        if f'# {path.stem}\n' not in text:errors.append(f'Heading mismatch: {path}')
        source_path(entry).read_bytes()
        for target in re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]',text):
            p=VAULT/target
            if p.exists() or p.with_suffix('.md').exists():continue
            if names[target]!=1:errors.append(f'Broken or ambiguous link: {target}')
    print(json.dumps({'errors':errors,'notes':len(entries)},indent=2))
    if errors:raise ValueError('Vault audit failed.')

def main():
    parser=argparse.ArgumentParser(description='Your local personal wiki: chat, factual ask, raw search, and ingestion. No cloud services.')
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ['ask','search']:
        sub=commands.add_parser(name);sub.add_argument('query');sub.add_argument('--mode',choices=['local'],default='local')
    sub=commands.add_parser('ingest');sub.add_argument('path',nargs='?',default=str(VAULT/'raw'));sub.add_argument('--regenerate',action='store_true')
    for name in ['chat','help','rebuild','audit','model-info']: commands.add_parser(name)
    args=parser.parse_args()
    if args.command=='help':parser.print_help();return
    try:
        if args.command=='ask':ask(args.query)
        elif args.command=='search':
            hits=search(args.query);print(context(hits) or 'No matching passages.');save('search',{'query':args.query,'retrieved':hits,'model_called':False})
        elif args.command=='chat':chat()
        elif args.command=='ingest':ingest(args.path,args.regenerate)
        elif args.command=='rebuild':rebuild();print('Index rebuilt from original sources.')
        elif args.command=='audit':audit()
        elif args.command=='model-info':
            info=identity();print(json.dumps(info,indent=2));write_json(ROOT/'evidence'/'model.json',info)
    except (RuntimeError,ValueError,OSError,KeyError) as e:
        print('Error: '+str(e),file=sys.stderr);save('error',{'command':vars(args),'error':str(e)});sys.exit(1)

if __name__=='__main__':main()
