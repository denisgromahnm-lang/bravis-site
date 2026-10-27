#!/usr/bin/env python3
"""Read-only public DNS/WHOIS preflight for BRAVIS registrar/mail migration.

Never changes records, uses no credentials, and never treats lookup failures as
proof that a domain is available or unconfigured.
"""
from datetime import datetime, timezone
import json
import socket
import urllib.parse
import urllib.request

DOMAIN = 'bravisrest.ru'
TYPES = [('NS',DOMAIN),('MX',DOMAIN),('A',DOMAIN),('AAAA',DOMAIN),
         ('TXT',DOMAIN),('CAA',DOMAIN),('CNAME','www.'+DOMAIN),
         ('A','www.'+DOMAIN),('MX','_dmarc.'+DOMAIN),('TXT','_dmarc.'+DOMAIN)]

def resolve(name,kind):
    url='https://dns.google/resolve?'+urllib.parse.urlencode({'name':name,'type':kind})
    req=urllib.request.Request(url,headers={'User-Agent':'BRAVIS-readonly-domain-check/1.0'})
    with urllib.request.urlopen(req,timeout=12) as r:
        data=json.load(r)
    status=data.get('Status')
    values=[]
    for answer in data.get('Answer',[]):
        value=answer.get('data','')
        if kind=='TXT':
            # SPF/DMARC may be shared; suppress other TXT verification tokens.
            if 'v=spf1' not in value.lower() and 'v=dmarc1' not in value.lower():
                continue
        values.append({'data':value,'ttl':answer.get('TTL')})
    labels={0:'NOERROR',2:'SERVFAIL',3:'NXDOMAIN',5:'REFUSED'}
    return {'status':status,'status_label':labels.get(status,'DNS_RESPONSE_'+str(status)),
            'answers':values, 'ad':data.get('AD'), 'comment':data.get('Comment','')[:300]}

def whois(domain):
    # .RU official registry WHOIS. Preserve only operational non-PII fields.
    fields={}
    with socket.create_connection(('whois.tcinet.ru',43),timeout=8) as sock:
        sock.settimeout(8)
        sock.sendall((domain+'\r\n').encode('ascii'))
        blocks=[]
        while sum(map(len,blocks))<120000:
            data=sock.recv(4096)
            if not data:break
            blocks.append(data)
        response=b''.join(blocks).decode('utf8','replace')
    approved={'domain','registrar','created','paid-till','free-date',
              'state','nserver','status','source'}
    for line in response.splitlines():
        if ':' not in line or line.startswith('%'):continue
        k,v=line.split(':',1)
        key=k.strip().lower()
        if key in approved:fields.setdefault(key,[]).append(v.strip()[:250])
    return fields

result={'domain':DOMAIN,'checked_at':datetime.now(timezone.utc).isoformat(),
        'note':'Non-authoritative read-only snapshot. Recheck in registrar dashboards before any DNS changes.',
        'dns':{},'whois':{},'errors':[]}
for kind,name in TYPES:
    key=name+' '+kind
    try:
        result['dns'][key]=resolve(name,kind)
    except Exception as e:
        result['dns'][key]={'status':'unavailable','answers':[]}
        result['errors'].append(key+': '+str(e)[:120])
# A SERVFAIL is not NXDOMAIN: collect a DNSSEC-disabled probe and alternative
# public resolver result without guessing whether delegation is broken.
if result['dns'].get(DOMAIN+' NS',{}).get('status')==2:
    for base,label in [
        ('https://dns.google/resolve','Google DNSSEC check disabled'),
        ('https://cloudflare-dns.com/dns-query','Cloudflare DoH')]:
        try:
            params={'name':DOMAIN,'type':'NS','cd':'true'} if 'google' in base else {'name':DOMAIN,'type':'NS'}
            url=base+'?'+urllib.parse.urlencode(params)
            headers={'User-Agent':'BRAVIS-readonly-domain-check/1.0','Accept':'application/dns-json'}
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=12) as res:
                raw=json.load(res)
            result['dns_diagnostics_'+label]={'status':raw.get('Status'),'comment':raw.get('Comment',''),
                'answers':[a.get('data') for a in raw.get('Answer',[])]}
        except Exception as e:
            result['dns_diagnostics_'+label]={'error':str(e)[:200]}
try:
    result['whois']=whois(DOMAIN)
except Exception as e:
    result['whois']={'status':'unavailable'}
    result['errors'].append('WHOIS: '+str(e)[:120])
print(json.dumps(result,ensure_ascii=False,indent=2))
