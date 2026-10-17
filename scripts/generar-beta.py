# Regenera beta/index.html a partir de index.html (la raíz es la fuente) aplicando solo lo propio de la beta:
# sin el cargador de Capacitor, título «(beta)», EN_APP=false y la etiqueta roja BETA (se conserva la que ya tiene beta/).
# Uso: python scripts/generar-beta.py
import os,re
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd=lambda p:open(os.path.join(R,p),'rb').read().decode('utf-8').replace('\r\n','\n')
raiz=rd('index.html'); beta=rd('beta/index.html')
tag=next(l for l in beta.split('\n') if l.startswith('<div id="betaTag"'))
out=[]
for l in raiz.split('\n'):
    if l.startswith('<script>/* App nativa (Capacitor)'): continue
    if l.startswith("if(window.Capacitor&&typeof window.Capacitor.isNativePlatform==='function'"): continue
    if l=='<title>Punto Ciego</title>': l='<title>Punto Ciego (beta)</title>'
    if l.startswith('const EN_APP='): l='const EN_APP=false; /* la beta es solo web: sin Capacitor, sin plugins nativos */'
    out.append(l)
t='\n'.join(out)
assert t.count('</body>')==1
t=t.replace('</body>',tag+'\n</body>')
open(os.path.join(R,'beta/index.html'),'wb').write(t.replace('\n','\r\n').encode('utf-8'))
print('beta/index.html regenerado')
