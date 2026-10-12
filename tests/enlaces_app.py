# Prueba de los enlaces externos y de los plugins nativos en la app, y de que la web sigue igual.
# Uso: `python tests/enlaces_app.py` (necesita playwright y Edge). Genera www/ con scripts/preparar-www.mjs y lo sirve en el puerto 8393.
# El puente nativo se simula COMO EL REAL: window.Capacitor solo con isNativePlatform, PluginHeaders y nativePromise, SIN registerPlugin
# (lo aporta assets/capacitor.js, el UMD de @capacitor/core). Con el index.html de la raíz y sin ese archivo, el test fallaría.
import os,sys,subprocess,threading,functools,http.server
from playwright.sync_api import sync_playwright
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fallos=[]
def ok(c,m):
    print(('OK   ' if c else 'FALLA ')+m)
    if not c: fallos.append(m)
subprocess.run(['node',os.path.join(RAIZ,'scripts','preparar-www.mjs')],cwd=RAIZ,check=True,stdout=subprocess.DEVNULL)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
def sirve(d,port):
    s=http.server.ThreadingHTTPServer(('127.0.0.1',port),functools.partial(Q,directory=d)); threading.Thread(target=s.serve_forever,daemon=True).start(); return s
www=sirve(os.path.join(RAIZ,'www'),8393); raiz=sirve(RAIZ,8394); beta=sirve(os.path.join(RAIZ,'beta'),8396)
PUENTE="""window.__llamadas=[];
window.webkit={messageHandlers:{bridge:{postMessage(){}}}};
window.Capacitor={isNativePlatform:()=>true,
  PluginHeaders:[{name:'Browser',methods:[{name:'open',rtype:'promise'}]},{name:'SignInWithApple',methods:[{name:'authorize',rtype:'promise'}]}],
  nativePromise:(plugin,metodo,opts)=>{window.__llamadas.push([plugin,metodo,opts]);return Promise.resolve({})}};"""
U='?supa=x&supakey='
def portada(p): # con cuentas se entra como invitado (acceso -> portada con Jugar y los tres enlaces); en local sin clave de Supabase ya sale la portada
    p.wait_for_selector('[data-a=invitado],[data-a=jugar]')
    if p.locator('[data-a=invitado]').count(): p.click('[data-a=invitado]')
    p.wait_for_selector('[data-a=jugar]')
with sync_playwright() as pw:
    br=pw.chromium.launch(channel='msedge')
    # --- app: puente sin registerPlugin ---
    ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.add_init_script(PUENTE); p.goto('http://localhost:8393/'+U); portada(p)
    ok(p.evaluate("typeof window.Capacitor.registerPlugin")=='function','app: registerPlugin existe (lo aporta assets/capacitor.js)')
    ok(p.evaluate("EN_APP")==True,'app: EN_APP activo')
    ext=p.evaluate("[...document.querySelectorAll('a[data-ext]')].map(a=>a.dataset.ext)")
    ok(ext==['https://puntostudio.es/punto-ciego/privacidad.html','https://puntostudio.es/punto-ciego/terminos.html','https://puntostudio.es/punto-ciego/soporte.html'],f'app: URLs absolutas {ext}')
    for i in range(3): p.evaluate("i=>document.querySelectorAll('a[data-ext]')[i].click()",i)
    p.wait_for_timeout(300); ll=p.evaluate("window.__llamadas")
    ok([(a,b,c['url']) for a,b,c in ll]==[('Browser','open',u) for u in ext],f'app: los tres enlaces llaman a Browser.open {ll}')
    ok(p.evaluate("location.pathname")=='/','app: la página no navega')
    ok(p.evaluate("(()=>{ME={code:'ABCDE'};return urlPartida()})()")=='https://puntostudio.es/punto-ciego/?c=ABCDE','app: el enlace para compartir lleva la web pública')
    ok(p.evaluate("redirigeA()")=='https://puntostudio.es/punto-ciego/','app: las redirecciones de cuentas llevan a la web')
    p.evaluate("plugin('SignInWithApple').authorize({clientId:'x'}).catch(()=>{})"); p.wait_for_timeout(200)
    ok(p.evaluate("window.__llamadas").pop()[:2]==['SignInWithApple','authorize'],'app: el plugin SignInWithApple se registra con su nombre nativo')
    ok(not errs,f'app: sin errores de JS {errs}'); ctx.close()
    # --- web: sin Capacitor, nada cambia ---
    ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto('http://localhost:8394/'+U); portada(p)
    ok(p.evaluate("typeof window.Capacitor")=='undefined','web: no se carga Capacitor')
    ok(p.evaluate("[...document.scripts].every(s=>!/capacitor/.test(s.src))"),'web: ningún <script> de Capacitor')
    ok(p.evaluate("[...document.querySelectorAll('a[data-ext]')].map(a=>a.getAttribute('href'))")==['/privacidad/','terminos.html','/soporte/'],'web: los href de siempre')
    sin=p.evaluate("(()=>{let d=null;document.addEventListener('click',e=>{d=e.defaultPrevented;e.preventDefault()});document.querySelector('a[data-ext]').click();return d})()")
    ok(sin==False,'web: el clic en los enlaces no se intercepta')
    ok(p.evaluate("(()=>{ME={code:'ABCDE'};return urlPartida()})()")=='http://localhost:8394/?c=ABCDE','web: el enlace para compartir no cambia')
    ok(not errs,f'web: sin errores de JS {errs}'); ctx.close()
    # --- beta: web pura, sin Capacitor ni modo app, aunque exista el puente ---
    ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.add_init_script(PUENTE); p.goto('http://localhost:8396/'+U); portada(p)
    ok(p.evaluate("EN_APP")==False,'beta: EN_APP desactivado')
    ok(p.evaluate("[...document.scripts].every(s=>!/capacitor/.test(s.src))"),'beta: ningún <script> de Capacitor')
    ok(p.evaluate("[...document.querySelectorAll('a[data-ext]')].map(a=>a.getAttribute('href'))")==['/privacidad/','terminos.html','/soporte/'],'beta: los href de la web')
    ok(p.evaluate("(()=>{ME={code:'ABCDE'};return urlPartida()})()")=='http://localhost:8396/?c=ABCDE','beta: el enlace para compartir es el de la propia web')
    ok(not errs,f'beta: sin errores de JS {errs}'); ctx.close(); br.close()
www.shutdown(); raiz.shutdown(); beta.shutdown(); print('\nFALLOS:',len(fallos)); sys.exit(1 if fallos else 0)
