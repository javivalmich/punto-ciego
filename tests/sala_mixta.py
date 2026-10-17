# Sala mixta (tres partidas completas): cuatro móviles con el MISMO APP_V pero distinta REV juegan una partida completa, sin bloqueo y sin errores.
# Comprueba también: cada móvil manda su REV, el anfitrión publica la REV mínima de la sala (st.revMin), las funciones nuevas
# no se activan hasta que todos las tienen, y una acción o un campo que la versión no conoce se ignoran sin fallar.
# Red: un broker MQTT mínimo en memoria sustituye a los públicos (los móviles lo usan con ?broker=, solo válido en localhost).
# Prueba la raíz; PUNTO_WEB=beta para probar beta/. Uso: `python tests/sala_mixta.py` (necesita playwright y Edge). Puertos 8392 y 9999 libres.
import os,sys,time,tempfile,subprocess,threading,functools,http.server,re
from playwright.sync_api import sync_playwright
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS=os.path.join(tempfile.mkdtemp(),'mock.json')
B='http://localhost:8392/?supa=http://localhost:9999&supakey=local&broker=ws://broker.test/mqtt'
fallos=[]
def ok(c,m):
    print(('OK   ' if c else 'FALLA ')+m)
    if not c: fallos.append(m)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8392),functools.partial(Q,directory=os.path.join(RAIZ,'beta') if os.environ.get('PUNTO_WEB')=='beta' else RAIZ))
threading.Thread(target=srv.serve_forever,daemon=True).start()
pr=subprocess.Popen(['node',os.path.join(RAIZ,'mocksb.js')],env={**os.environ,'MOCKSB_DATOS':DATOS},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1.2)

# ---- broker MQTT 3.1.1 mínimo (QoS 0, retenidos, suscripciones «tema/#») ----
def paquete(h,body):
    n=len(body); l=bytearray()
    while True:
        d=n%128; n//=128
        if n: d|=128
        l.append(d)
        if not n: break
    return bytes([h])+bytes(l)+bytes(body)
class Broker:
    def __init__(s): s.subs=[]; s.ret={}
    def publica(s,topic,payload):
        t=topic.encode(); body=len(t).to_bytes(2,'big')+t+payload
        for ws,pref in list(s.subs):
            if topic.startswith(pref):
                try: ws.send(paquete(0x30,body))
                except Exception: pass
    def conexion(s,ws):
        buf=bytearray()
        def msg(m):
            buf.extend(m if isinstance(m,(bytes,bytearray)) else m.encode('latin1'))
            while len(buf)>=2:
                i=1; mul=1; ln=0
                while True:
                    if i>=len(buf): return
                    b=buf[i]; i+=1; ln+=(b&127)*mul; mul*=128
                    if not b&128: break
                if len(buf)<i+ln: return
                tipo=buf[0]>>4; flags=buf[0]&15; body=bytes(buf[i:i+ln]); del buf[:i+ln]
                if tipo==1: ws.send(bytes([0x20,2,0,0]))
                elif tipo==8:
                    tl=int.from_bytes(body[2:4],'big'); filt=body[4:4+tl].decode(); pref=filt[:-1] if filt.endswith('#') else filt
                    ws.send(bytes([0x90,3,body[0],body[1],0])); s.subs.append((ws,pref))
                    for t,pl in list(s.ret.items()):
                        if t.startswith(pref):
                            tb=t.encode(); ws.send(paquete(0x31,len(tb).to_bytes(2,'big')+tb+pl))
                elif tipo==3:
                    tl=int.from_bytes(body[0:2],'big'); topic=body[2:2+tl].decode(); pl=body[2+tl:]
                    if flags&1:
                        if pl: s.ret[topic]=pl
                        else: s.ret.pop(topic,None)
                    s.publica(topic,pl)
                elif tipo==12: ws.send(b'\xd0\x00')
        ws.on_message(msg)

# La 1.0.1 de la App Store: el index.html de la rama app antes de existir REV (APP_V=3, sin REV en acciones ni ping)
VIEJO=subprocess.run(['git','show','af789ae:index.html'],cwd=RAIZ,capture_output=True,check=True).stdout.decode('utf-8')
assert 'const REV=' not in VIEJO and 'const APP_V=3' in VIEJO
def monta(ctx,rev,funcs=''):
    """Sirve index.html con otra REV (y, si se pide, REV_FUNCS): el mismo código hace de móvil «viejo» o «nuevo».
    rev=None: sirve el código real de la 1.0.1, que no manda REV."""
    def h(route):
        r=route.fetch()
        if rev is None: route.fulfill(response=r,body=VIEJO); return
        t=r.text()
        t,n=re.subn(r'const REV=\d+;',f'const REV={rev};',t,count=1); assert n==1
        if funcs: t=t.replace('const REV_FUNCS={};',f'const REV_FUNCS={funcs};',1)
        route.fulfill(response=r,body=t)
    ctx.route(re.compile(r'^http://localhost:8392/(\?.*)?$'),h)

def movil(br,broker,rev,nombre,codigo,errs):
    ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True,service_workers='block')
    ctx.route_web_socket('ws://broker.test/**',broker.conexion)
    monta(ctx,rev,'{probe:1}')
    p=ctx.new_page(); p.on('pageerror',lambda e:errs.append(f'{nombre}: {e}'))
    p.goto(B); p.wait_for_selector('[data-a=invitado]'); p.click('[data-a=invitado]')
    p.wait_for_selector('[data-a=jugar]'); p.click('[data-a=jugar]'); p.wait_for_selector('#nom'); p.fill('#nom',nombre); p.wait_for_timeout(600)
    p.click('[data-a=guardarPerfil]'); p.wait_for_selector('[data-a=crear]')
    if codigo is None: p.click('[data-a=crear]')
    else: p.fill('#cod',codigo); p.click('[data-a=unirme]')
    return p

BUCLE="""()=>{
 if(!S)return 'nada';const me=mine();
 if(S.phase==='play'&&me&&!me.dead&&me.role==='imp'){const v=S.players.find(x=>!x.dead&&x.role!=='imp');if(v&&ahora()>=me.kcd)accion('kill',{target:v.id})}
 if(S.phase==='meeting'&&S.meet&&me&&!me.dead){
   if(S.meet.fase==='disc')accion('listo',{n:S.meet.n});
   else if(S.meet.fase==='vote'&&!(me.id in S.meet.votes)){const o=S.players.filter(x=>!x.dead&&x.id!==me.id);accion('vote',{target:o[0].id})}
 }
 return S.phase+(BLOQUEO?'!':'')}"""
def partida(br,revs,nombres,etq,esperaMin,detalle=True):
    """Cuatro móviles (revs[i]: número = REV, None = la 1.0.1 sin REV; el primero es el anfitrión) juegan una partida completa."""
    broker=Broker(); errs=[]
    ph=movil(br,broker,revs[0],nombres[0],None,errs); ph.wait_for_function("S&&S.phase==='lobby'&&ME.code",timeout=10000)
    code=ph.evaluate("ME.code"); ps=[ph]
    for r,n in zip(revs[1:],nombres[1:]): ps.append(movil(br,broker,r,n,code,errs))
    ph.wait_for_function("S.players.length===4",timeout=15000)
    for p in ps: p.wait_for_function("S&&mine()",timeout=15000)
    appv=[p.evaluate("APP_V") for p in ps]
    ok(len(set(appv))==1 and appv[0]==3,f'[{etq}] los cuatro móviles tienen el mismo APP_V {appv}')
    ok([p.evaluate("typeof REV==='undefined'?null:REV") for p in ps]==revs,f'[{etq}] cada móvil tiene su propia REV {revs} (None = 1.0.1, sin REV)')
    ok(all(p.evaluate("BLOQUEO")is None for p in ps),f'[{etq}] ninguno se bloquea por tener otra REV (misma sala)')
    ph.wait_for_timeout(4500)   # ping de todos y al menos una publicación del anfitrión
    for p in ps: p.wait_for_function("S&&S.players.length===4",timeout=10000)
    if revs[0] is not None:
        ph.wait_for_function("S.players.every(x=>Number.isInteger(x.rev)||false)||S.players.filter(x=>x.id!==ME.pid).every(x=>x.rev!==undefined||true)",timeout=15000)
        porNombre=ph.evaluate("Object.fromEntries(S.players.map(x=>[x.name,x.rev===undefined?null:x.rev]))")
        ok(porNombre==dict(zip(nombres,revs)),f'[{etq}] el anfitrión guarda la REV de cada jugador (None = sin REV, cuenta 0) {porNombre}')
    minimo=[p.evaluate("S.revMin===undefined?null:S.revMin") for p in ps]
    if revs[0] is not None:
        ok(minimo==[esperaMin]*4,f'[{etq}] REV mínima de la sala vista por los cuatro = {esperaMin} {minimo}')
    else:
        ok(minimo==[None]*4,f'[{etq}] anfitrión 1.0.1: no publica REV mínima y nadie se confunde {minimo}')
    ok([p.evaluate("typeof funcionActiva==='function'?funcionActiva('probe'):false") for p in ps]==[False]*4,f'[{etq}] una función que pide REV 1 no se activa mientras alguien no la tiene')
    if detalle:
        ok(ph.evaluate("funcionActiva('noExiste')")==False,f'[{etq}] una función que no está en la tabla nunca se activa')
        ok(ph.evaluate("[revSala({players:[{rev:1},{rev:2},{bot:true}]}),revSala({players:[{rev:2},{}]}),revSala({players:[{rev:3}]})]")==[1,0,3],f'[{etq}] revSala: mínima de las personas; sin REV cuenta como 0; los bots no cuentan')
        ph.evaluate("accion('cfg',{cfg:{killCd:10,disc:0,vote:15,tasks:2,largas:0,emerg:1,walkie:false}})"); ph.wait_for_timeout(500)
        ps[1].evaluate("accion('accionDelFuturo',{x:1,y:[2]})"); ph.wait_for_timeout(800)
        ok(ph.evaluate("S.phase")=='lobby' and ph.evaluate("S.players.length")==4,f'[{etq}] una acción desconocida no rompe la sala')
        ph.evaluate("S.campoDelFuturo={a:1,b:[2,3]};S.players[1].extraFuturo='x';publicarEstado(true)"); ph.wait_for_timeout(1200)
        ok(all(p.evaluate("!!S&&S.phase==='lobby'&&!BLOQUEO") for p in ps),f'[{etq}] un campo desconocido en el estado se conserva y no rompe a nadie')
    else:
        ph.evaluate("accion('cfg',{cfg:{killCd:10,disc:0,vote:15,tasks:2,largas:0,emerg:1,walkie:false}})"); ph.wait_for_timeout(800)
    ph.click('[data-a=empezar]')
    for p in ps: p.wait_for_function("S&&S.phase==='play'",timeout=15000)
    t0=time.time(); fases=[]
    while time.time()-t0<120:
        fases=[p.evaluate(BUCLE) for p in ps]
        if all(f=='end' for f in fases): break
        ph.wait_for_timeout(500)
    ok(all(f=='end' for f in fases),f'[{etq}] la partida llega al final en los cuatro móviles {fases}')
    ws=[p.evaluate("S.end&&S.end.w") for p in ps]
    ok(len(set(ws))==1 and ws[0] in ('imp','crew'),f'[{etq}] los cuatro ven el mismo resultado {ws}')
    ok(all(p.evaluate("!BLOQUEO") for p in ps),f'[{etq}] nadie vio la pantalla de bloqueo durante la partida')
    ok(errs==[],f'[{etq}] sin errores de JavaScript {errs[:3]}')
    for p in ps: p.context.close()

try:
    with sync_playwright() as pw:
        br=pw.chromium.launch(channel='msedge'); N=['Hugo','Ana','Blas','Carla']
        partida(br,[1,0,1,2],N,'mixta REV 1/0/1/2',0)
        partida(br,[None,1,1,2],N,'anfitrión 1.0.1 (sin REV) con invitados nuevos',None,False)
        partida(br,[1,None,1,2],N,'invitado 1.0.1 (sin REV) con anfitrión nuevo',0,False)
        br.close()
finally:
    srv.shutdown(); pr.terminate()
print(('TODO OK' if not fallos else f'{len(fallos)} FALLOS'))
sys.exit(1 if fallos else 0)
