# Prueba de ajustes (⚙), avisos (sonido y vibración solo en avisos para todos) y walkie desactivado por defecto,
# contra el servidor que imita a Supabase. Prueba la raíz; PUNTO_WEB=beta para probar beta/.
# Uso: `python tests/avisos.py` (necesita playwright y Edge). Usa los puertos 8392 y 9999 (deben estar libres).
import os,sys,json,time,tempfile,subprocess,threading,functools,http.server
from playwright.sync_api import sync_playwright
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS=os.path.join(tempfile.mkdtemp(),'mock.json')
B='http://localhost:8392/?supa=http://localhost:9999&supakey=local'
fallos=[]
def ok(c,m):
    print(('OK   ' if c else 'FALLA ')+m)
    if not c: fallos.append(m)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8392),functools.partial(Q,directory=os.path.join(RAIZ,'beta') if os.environ.get('PUNTO_WEB')=='beta' else RAIZ))
threading.Thread(target=srv.serve_forever,daemon=True).start()
pr=subprocess.Popen(['node',os.path.join(RAIZ,'mocksb.js')],env={**os.environ,'MOCKSB_DATOS':DATOS},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(1.2)
INIT="window.__vib=[];navigator.vibrate=function(p){window.__vib.push(p);return true}"
BUCLE="""()=>{
 if(!S)return 'nada';const me=mine();
 if(S.phase==='play'&&me&&!me.dead){const v=S.players.find(x=>!x.dead&&x.role!=='imp');if(v&&ahora()>=me.kcd)accion('kill',{target:v.id})}
 if(S.phase==='meeting'&&S.meet&&me&&!me.dead){
   if(S.meet.fase==='disc')accion('listo',{n:S.meet.n});
   else if(S.meet.fase==='vote'&&!(me.id in S.meet.votes)){const o=S.players.filter(x=>!x.dead&&x.id!==me.id);accion('vote',{target:o[0].id})}
 }
 return S.phase}"""
try:
    with sync_playwright() as pw:
        br=pw.chromium.launch(channel='msedge')
        ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); ctx.add_init_script(INIT); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
        p.goto(B); p.wait_for_selector('[data-a=invitado]'); p.click('[data-a=invitado]'); p.wait_for_selector('[data-a=jugar]')
        # ajustes
        ok(p.evaluate("document.documentElement.getAttribute('data-theme')")=='dark','tema oscuro por defecto')
        p.click('[data-a=ajustes]'); p.wait_for_selector('[data-a=ajTema]')
        ok(p.locator('[data-a=ajSonido]').count()==1 and p.locator('[data-a=ajVibra]').count()==1,'ajustes: tema, sonido y vibración')
        p.click('[data-a=ajTema][data-v=light]'); ok(p.evaluate("document.documentElement.getAttribute('data-theme')")=='light','tema claro aplicado')
        p.click('[data-a=ajTema][data-v=auto]'); ok(p.evaluate("document.documentElement.hasAttribute('data-theme')")==False,'tema automático: sin atributo')
        p.click('[data-a=ajTema][data-v=dark]')
        p.click('[data-a=ajVibra]'); ok(p.evaluate("SET.vibra")==False,'vibración apagada'); p.click('[data-a=ajVibra]'); ok(p.evaluate("SET.vibra")==True,'vibración encendida')
        p.click('[data-a=ajSonido]'); p.reload(); p.wait_for_selector('[data-a=jugar]'); ok(p.evaluate("SET.sound")==False,'el ajuste de sonido se guarda'); p.evaluate("setAjuste('sound',true)")
        # sala: walkie desactivado por defecto
        p.click('[data-a=jugar]'); p.wait_for_selector('#nom'); p.fill('#nom','Avisos'); p.wait_for_timeout(600); p.click('[data-a=guardarPerfil]'); p.wait_for_selector('[data-a=crear]')
        p.click('[data-a=crear]'); p.wait_for_selector('[data-a=botMas3]'); p.click('[data-a=botMas3]'); p.wait_for_timeout(400)
        ok(p.evaluate("S.cfg.walkie")==False,'walkie desactivado por defecto al crear partida')
        ok(p.evaluate("document.querySelector('#wkFab').hidden")==True,'sin botón de walkie con el walkie desactivado')
        p.click('.tog[data-k=walkie]'); p.wait_for_timeout(300); ok(p.evaluate("S.cfg.walkie")==True,'el anfitrión puede activarlo')
        p.click('.tog[data-k=walkie]'); p.wait_for_timeout(300)
        # partida: el anfitrión es Punto y mata; solo vibran los avisos
        p.evaluate("accion('pruebas',{rol:'imp',vel:'rapida'})"); p.evaluate("accion('cfg',{cfg:{killCd:10,disc:0,vote:15,tasks:2,largas:0,emerg:1}})")
        p.evaluate("window.__vib=[]")
        p.click('[data-a=empezar]'); p.wait_for_function("S&&S.phase==='play'",timeout=8000); p.wait_for_timeout(600)
        v=p.evaluate("window.__vib"); ok(v==[[80,60,80]],f'al empezar vibra el aviso de inicio, antes de ver el papel {v}')
        p.wait_for_selector('[data-hold=papel]'); box=p.locator('[data-hold=papel]').bounding_box()
        p.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2); p.mouse.down(); p.wait_for_timeout(300); p.mouse.up()
        ok(len(p.evaluate("window.__vib"))==1,'ver el papel no vibra')
        t0=time.time(); fase='play'
        while time.time()-t0<240:
            fase=p.evaluate(BUCLE)
            if fase=='end': break
            p.wait_for_timeout(700)
        ok(fase=='end','la partida llega al final')
        v=p.evaluate("window.__vib"); print('     vibraciones:',v)
        conocidos=[[80,60,80],[600,200,600,200,600],[300,120,300,120,300],[500,200,500],[200,100,200]]
        ok(all(x in conocidos for x in v),'toda vibración es un aviso conocido (ninguna por matar, tareas, etc.)')
        ok(any(x in ([600,200,600,200,600],[300,120,300,120,300]) for x in v),'vibró al abrirse una reunión')
        ok([200,100,200] in v,'vibró al terminar la votación')
        ok(not errs,f'sin errores de JS {errs}')
        br.close()
finally:
    pr.terminate()
print('\nFALLOS:',len(fallos)); sys.exit(1 if fallos else 0)
