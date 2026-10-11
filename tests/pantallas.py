# Prueba de las pantallas completas (revelado, muerte, reunión, final) en tamaños de iPhone SE, normal y Pro Max.
# Uso: servir beta/ en http://localhost:8392/ y `node mocksb.js` en marcha; luego `python tests/pantallas.py` (necesita playwright y Edge).
# Comprueba: sin barra/walkie/atajos donde no toca, botones pulsables y a la vista, sin desbordes, bots reportan pronto. Capturas en .cap/ (no se sube).
import sys,time,json
from playwright.sync_api import sync_playwright
OUT='C:/Users/javiv/Punto ciego/.cap/'
SIZES={'SE':(375,553),'normal':(390,664),'ProMax':(430,740)}
fallos=[]
def ok(c,m):
    print(('OK   ' if c else 'FALLA ')+m)
    if not c: fallos.append(m)
GEO="""()=>{const o=document.querySelector('#over');const q=s=>document.querySelector(s);
const vis=e=>{if(!e)return false;const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.display!=='none'&&cs.visibility!=='hidden'};
const c=q('#over .ov-cuerpo'),btn=[...document.querySelectorAll('#over button')].filter(vis);
const bots=btn.map(b=>{const r=b.getBoundingClientRect();const t=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {txt:b.textContent.trim().slice(0,25),bottom:Math.round(r.bottom),top:Math.round(r.top),ok:!!t&&b.contains(t)||t===b}});
return {ih:innerHeight,bar:vis(q('#bar')),wk:vis(q('#wkFab')),pr:vis(q('#prFab')),over:vis(o),
 desborda:c?c.scrollHeight>c.clientHeight+1:null,docScroll:document.documentElement.scrollHeight>innerHeight+1,btn:bots,
 pie:(()=>{const p=q('#over .ov-pie');return p?Math.round(p.getBoundingClientRect().bottom):null})()}}"""
with sync_playwright() as pw:
  br=pw.chromium.launch(channel='msedge')
  for nom,(w,h) in SIZES.items():
    ctx=br.new_context(viewport={'width':w,'height':h},device_scale_factor=2,is_mobile=True,has_touch=True)
    p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto('http://localhost:8392/?supa=http://localhost:9999&supakey=local&pruebas=1'); p.wait_for_timeout(1500)
    p.wait_for_selector('[data-a=modoAcceso]'); p.click('[data-a=modoAcceso][data-m=crear]')
    p.fill('#em','p%d@ejemplo.com'%int(time.time()*1000)); p.fill('#pw','clave1234'); p.click('[data-a=crearCuenta]')
    p.wait_for_selector('#nom'); p.fill('#nom','Ana'+str(int(time.time()))[-4:]); p.wait_for_timeout(800)
    p.click('[data-a=guardarPerfil]'); p.wait_for_selector('[data-a=crear]'); p.click('[data-a=crear]')
    p.wait_for_selector('[data-a=botMas]')
    for i in range(3): p.click('[data-a=botMas]'); p.wait_for_timeout(250)
    rol_list=['imp','crew']
    for rol in rol_list:
      p.evaluate("r=>accion('pruebas',{rol:r})",rol)
      if rol=='imp' and nom!='SE': pass
      p.evaluate("accion('cfg',{cfg:{walkie:true}})"); p.wait_for_timeout(300)  # el walkie viene desactivado por defecto
      p.click('[data-a=empezar]'); p.wait_for_selector('[data-hold=papel]'); p.wait_for_timeout(1500)
      g=p.evaluate(GEO); print(nom,rol,'tapa',json.dumps(g))
      ok(not g['bar'] and not g['wk'] and not g['pr'],f'{nom} {rol} tapa: sin barra/walkie/atajos'); ok(g['desborda']==False,f'{nom} {rol} tapa: no desborda')
      p.screenshot(path=OUT+f'{nom}-{rol}-tapa.png')
      p.focus('[data-hold=papel]'); p.keyboard.down('Space'); p.wait_for_timeout(700)
      g=p.evaluate(GEO); print(nom,rol,'papel',json.dumps(g))
      ok(not g['bar'] and not g['wk'] and not g['pr'],f'{nom} {rol} papel: nada de la partida')
      ok(g['desborda']==False and not g['docScroll'],f'{nom} {rol} papel: cabe sin desplazar')
      ok(all(b['ok'] and b['bottom']<=g['ih'] for b in g['btn']) and len(g['btn'])>=1,f'{nom} {rol} papel: botones visibles y pulsables')
      p.screenshot(path=OUT+f'{nom}-{rol}-papel.png')
      p.keyboard.up('Space'); p.wait_for_timeout(300)
      g=p.evaluate(GEO)
      ok(any('Entendido' in b['txt'] and b['ok'] and b['bottom']<=g['ih'] for b in g['btn']),f'{nom} {rol}: Entendido pulsable tras soltar')
      p.click('[data-a=entendido]'); p.wait_for_timeout(600)
      ok(p.evaluate("!document.querySelector('#bar').hidden")and p.evaluate(GEO)['bar'],f'{nom} {rol}: vuelve la barra tras Entendido')
      if rol=='crew':
        # muerte: un bot Punto me mata
        p.evaluate("()=>{const k=S.players.find(x=>esBot(x)&&x.role==='imp');k.kcd=0;botAccion(k.id,'kill',{target:ME.pid})}"); p.wait_for_timeout(1000)
        g=p.evaluate(GEO); print(nom,'muerte',json.dumps(g))
        ok(g['over'] and not g['bar'] and not g['wk'] and not g['pr'],f'{nom} muerte: sin barra ni walkie ni atajos')
        ok(all(b['ok'] for b in g['btn']),f'{nom} muerte: ningún botón visible bloqueado')
        p.screenshot(path=OUT+f'{nom}-muerte.png')
        # tiempo hasta que reportan
        t0=time.time()
        p.wait_for_function("()=>S&&S.phase==='meeting'",timeout=60000)
        print(nom,'bots reportan tras',round(time.time()-t0,1),'s'); ok(time.time()-t0<25,f'{nom}: los bots reportan en <25s')
        p.wait_for_timeout(800)
        g=p.evaluate(GEO); print(nom,'reunion',json.dumps(g))
        ok(g['over'] and not g['bar'] and g['wk'] and g['pr'],f'{nom} reunión: sin barra, walkie y atajos en su franja')
        ok(all(b['ok'] for b in g['btn']),f'{nom} reunión: botones pulsables (sin tapar)')
        p.screenshot(path=OUT+f'{nom}-reunion.png')
        # final
        p.evaluate("()=>{S.phase='end';S.end={w:'imp',why:'Prueba',t:ahora()};S.v++;pinta()}"); p.wait_for_timeout(800)
        g=p.evaluate(GEO); print(nom,'fin',json.dumps(g))
        ok(g['over'] and not g['bar'],f'{nom} final: sin barra')
        ok(all(b['ok'] and b['bottom']<=g['ih'] for b in g['btn']) and any('Otra' in b['txt'] for b in g['btn']),f'{nom} final: «Otra partida» visible y pulsable')
        p.screenshot(path=OUT+f'{nom}-fin.png')
      else:
        p.evaluate("()=>{S.phase='end';S.end={w:'crew',why:'x',t:ahora()};pinta()}"); 
      if rol=='imp':
        # reiniciar partida
        p.evaluate("()=>{accion('aLobby',{})}"); p.wait_for_timeout(1500)
        if not p.query_selector('[data-a=empezar]'):
          p.evaluate("()=>{S.phase='lobby';S.v++;pinta()}"); p.wait_for_timeout(500)
    ok(not errs,f'{nom}: sin errores JS {errs[:1]}')
    ctx.close()
  br.close()
print('FALLOS',len(fallos)); 
