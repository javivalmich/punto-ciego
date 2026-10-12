# Prueba del modo invitado: «‹ Volver» del editor lleva al acceso, enlace «Crear cuenta o entrar» en la portada del invitado,
# y que al crear cuenta el invitado conserva su nombre y su personaje. También que la web sigue con Google antes que Apple.
# Uso: `python tests/invitado_cuenta.py` (playwright y Edge). Arranca solo mocksb.js y un servidor estático en el puerto 8392.
import os,sys,time,tempfile,subprocess,threading,functools,http.server
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
with sync_playwright() as pw:
    br=pw.chromium.launch(channel='msedge')
    try:
        ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
        p.goto(B); p.wait_for_selector('[data-a=invitado]'); p.click('[data-a=invitado]'); p.wait_for_selector('[data-a=jugar]')
        ok(p.locator('[data-a=aAcceso]').count()==1 and 'Crear cuenta o entrar' in p.inner_text('[data-a=aAcceso]'),'portada de invitado: enlace «Crear cuenta o entrar»')
        # editor nuevo: «‹ Volver» (arriba y abajo) lleva al acceso
        p.click('[data-a=jugar]'); p.wait_for_selector('#nom')
        ok('Volver' in p.inner_text('[data-a=editorVolver]'),'editor de invitado: hay «‹ Volver»')
        p.click('[data-a=editorVolver]'); p.wait_for_selector('[data-a=entrarCuenta]'); ok(True,'«‹ Volver» sin cambios: lleva a la pantalla de acceso')
        p.click('[data-a=invitado]'); p.click('[data-a=jugar]'); p.wait_for_selector('#nom'); p.fill('#nom','Zoe')
        p.click('[data-a=editorVolver]'); p.wait_for_selector('[data-a=editorSalirOk]'); p.click('[data-a=editorSalirOk]'); p.wait_for_selector('[data-a=entrarCuenta]')
        ok(True,'«‹ Volver» con cambios: pregunta y luego va al acceso')
        p.click('[data-a=invitado]'); p.click('[data-a=jugar]'); p.wait_for_selector('#nom')
        p.click('#app [data-a=aAcceso]'); p.wait_for_selector('[data-a=entrarCuenta]'); ok(True,'«Volver» de abajo: lleva al acceso')
        # invitado con personaje -> crear cuenta conserva nombre y look
        p.click('[data-a=invitado]'); p.click('[data-a=jugar]'); p.wait_for_selector('#nom'); p.fill('#nom','Zoe'+str(int(time.time()))[-4:])
        p.click('[data-a=look][data-k=hood][data-v="3"]'); p.wait_for_timeout(500)
        nom=p.input_value('#nom'); p.click('[data-a=guardarPerfil]'); p.wait_for_selector('[data-a=crear]')
        look=p.evaluate("PERFIL.look")
        p.click('[data-a=aPortada]'); p.wait_for_selector('[data-a=aAcceso]'); p.click('[data-a=aAcceso]')
        p.wait_for_selector('[data-a=modoAcceso]'); p.click('[data-a=modoAcceso][data-m=crear]')
        p.fill('#em','inv%d@ejemplo.com'%int(time.time())); p.fill('#pw','clave1234'); p.click('[data-a=crearCuenta]')
        p.wait_for_selector('[data-a=jugar]'); p.click('[data-a=jugar]'); p.wait_for_selector('[data-a=crear]')
        ok(p.evaluate("!!USER&&!INVITADO"),'crear cuenta: sesión iniciada y fuera del modo invitado')
        ok(p.evaluate("PERFIL.name")==nom,'crear cuenta: conserva el nombre')
        ok(p.evaluate("PERFIL.look")==look,'crear cuenta: conserva el personaje')
        ok(p.evaluate("LS.get('pc.migrar')")is None,'crear cuenta: la marca de migración se limpia')
        # web: Google antes que Apple
        c2=br.new_context(viewport={'width':390,'height':760}); q=c2.new_page(); q.goto(B); q.wait_for_selector('[data-a=entrarCuenta]')
        q.evaluate("GOOGLE=true;APPLE=true;pinta()"); q.wait_for_timeout(200)
        orden=q.evaluate("[...document.querySelectorAll('#app [data-a=google],#app [data-a=apple]')].map(e=>e.dataset.a)")
        ok(orden==['google','apple'],f'web: Google y luego Apple como antes {orden}')
        ok(not errs,f'sin errores de JS {errs}')
    finally:
        pr.terminate(); srv.shutdown(); br.close()
print('\nFALLOS:',len(fallos)); sys.exit(1 if fallos else 0)
