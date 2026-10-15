# Prueba de los enlaces externos y de los plugins nativos en la app, y de que la web sigue igual.
# Uso: `python tests/enlaces_app.py` (necesita playwright y Edge). Genera www/ con scripts/preparar-www.mjs y lo sirve en el puerto 8393.
# El puente nativo se simula COMO EL REAL: window.Capacitor solo con isNativePlatform, PluginHeaders y nativePromise, SIN registerPlugin
# (lo aporta assets/capacitor.js, el UMD de @capacitor/core). Con el index.html de la raíz y sin ese archivo, el test fallaría.
import os,re,sys,subprocess,threading,functools,http.server
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
    # --- app: versión de la partida distinta (APP_V): no se pide recargar, se pide actualizar la app ---
    def bloq(p,vieja): p.evaluate(f"BLOQUEO={{vieja:{vieja}}};pinta()"); return p.evaluate("[document.querySelector('#bloqueo').innerText,!!document.querySelector('#bloqueoRecarga'),!!document.querySelector('#bloqueoTienda'),!!document.querySelector('#bloqueoSalir')]")
    ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page()
    p.add_init_script(PUENTE); p.goto('http://localhost:8393/'+U); portada(p)
    t,rec,tienda,salir=bloq(p,'true')
    ok('Actualiza la app' in t and not rec and tienda and salir,'app, partida más nueva: «Actualiza la app», sin recargar; con botón de la tienda')
    t,rec,tienda,salir=bloq(p,'false'); ok('anfitrión tiene que actualizar' in t and not rec,'app, partida más antigua: pide al anfitrión que actualice, sin recargar')
    p.click('#bloqueoSalir'); ok(p.evaluate("BLOQUEO")==None and p.locator('#bloqueo').count()==0,'app: «Salir de esta partida» quita el bloqueo'); ctx.close()
    ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page(); URL_T='https://apps.apple.com/app/id6822717539'
    p.route(re.compile(r'.*/(\?.*)?$'),lambda r:r.fulfill(status=200,content_type='text/html; charset=utf-8',body=r.fetch().text()))
    p.add_init_script(PUENTE); p.goto('http://localhost:8393/'+U); portada(p)
    t,rec,tienda,salir=bloq(p,'true'); ok(tienda and not rec,'app con enlace de la tienda: botón «Abrir la App Store»')
    p.click('#bloqueoTienda'); p.wait_for_timeout(200); ok(['Browser','open',{'url':URL_T}] in p.evaluate("window.__llamadas"),'el botón abre la ficha de la App Store'); ctx.close()
    # --- app Android: mismo puente pero con androidBridge (así lo detecta @capacitor/core), sin Sign in with Apple ni AudioSesion de iOS ---
    PUENTE_AND="""window.__llamadas=[];window.__cbs={};
window.androidBridge={postMessage(){}};
window.Capacitor={isNativePlatform:()=>true,
  PluginHeaders:[{name:'Browser',methods:[{name:'open',rtype:'promise'}]},
    {name:'App',methods:[{name:'addListener',rtype:'callback'},{name:'removeListener',rtype:'promise'},{name:'exitApp',rtype:'promise'},{name:'getLaunchUrl',rtype:'promise'}]},
    {name:'AudioSesion',methods:[{name:'modo',rtype:'promise'},{name:'abrirAjustes',rtype:'promise'},{name:'barras',rtype:'promise'}]},
    {name:'SocialLogin',methods:[{name:'initialize',rtype:'promise'},{name:'login',rtype:'promise'}]}],
  nativePromise:(plugin,metodo,opts)=>{window.__llamadas.push([plugin,metodo,opts]);return Promise.resolve({})},
  nativeCallback:(plugin,metodo,opts,cb)=>{window.__cbs[plugin+'.'+(opts&&opts.eventName)]=cb;window.__llamadas.push([plugin,metodo,opts]);return Promise.resolve('id1')}};"""
    def hay(p,plug,met): return any(a==plug and b==met for a,b,c in p.evaluate("window.__llamadas"))
    ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.add_init_script(PUENTE_AND); p.goto('http://localhost:8393/'+U); portada(p)
    ok(p.evaluate("[window.Capacitor.getPlatform(),ANDROID,document.documentElement.classList.contains('en-android')]")==['android',True,True],'android: plataforma detectada')
    ok(p.locator('.b-apple').count()==0,'android: sin botón de Apple')
    ok(hay(p,'App','getLaunchUrl'),'android: pide el enlace de arranque (getLaunchUrl)')
    ok(any(a=='AudioSesion' and b=='barras' and c.get('arriba','').startswith('#') for a,b,c in p.evaluate("window.__llamadas")),'android: pinta las barras del sistema con el color de la página')
    # Google: Credential Manager con el cliente WEB y sin «scopes»
    p.evaluate("SB={auth:{signInWithIdToken:async()=>({})}};entraConGoogleNativo().catch(()=>{})"); p.wait_for_timeout(300)
    ll=p.evaluate("window.__llamadas"); ini=[c for a,b,c in ll if a=='SocialLogin' and b=='initialize']; lg=[c for a,b,c in ll if a=='SocialLogin' and b=='login']
    ok(bool(ini) and ini[0]['google']['webClientId']=='696175970854-40tmmdnkpqb0gkclc964i72htekg42r5.apps.googleusercontent.com','android: Google se inicia con el cliente web (webClientId)')
    ok(bool(lg) and 'scopes' not in lg[0]['options'] and bool(lg[0]['options'].get('nonce')) and lg[0]['options'].get('forcePrompt')==True,'android: login de Google sin scopes y con nonce')
    # botón «atrás»
    def atras(): p.evaluate("window.__cbs['App.backButton']({canGoBack:false})"); p.wait_for_timeout(150)
    ok(p.evaluate("typeof window.__cbs['App.backButton']")=='function','android: escucha el botón atrás')
    p.evaluate("window.__llamadas=[]"); p.evaluate("abrirSheet('<h2>Prueba</h2>')"); ok(p.evaluate("!document.querySelector('#sheet').hidden"),'android: hoja abierta')
    atras(); ok(p.evaluate("document.querySelector('#sheet').hidden") and not hay(p,'App','exitApp'),'android: atrás cierra la hoja y no cierra la app')
    p.evaluate("WK.abierto=true;document.querySelector('#wk').hidden=false"); atras(); ok(p.evaluate("!WK.abierto"),'android: atrás cierra el walkie')
    p.evaluate("ME={code:'ABCDE',pid:'p1',name:'Yo'};S={phase:'play',players:[{id:'p1',name:'Yo'}],hostId:'x',v:1};window.pinta=()=>{}")
    atras(); ok(p.evaluate("!document.querySelector('#sheet').hidden && document.querySelector('#shBody').innerText.includes('¿Salir de la partida?')"),'android: atrás en plena partida pregunta «¿Salir de la partida?»')
    ok(not hay(p,'App','exitApp'),'android: atrás en plena partida no cierra la app')
    ctx.close()
    ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.add_init_script(PUENTE_AND); p.goto('http://localhost:8393/'+U); portada(p)
    p.evaluate("window.__llamadas=[]"); p.click('[data-a=jugar]'); p.wait_for_timeout(400)
    p.evaluate("window.__cbs['App.backButton']({canGoBack:false})"); p.wait_for_timeout(300)
    ok(p.evaluate("!document.querySelector('#nom')") and not hay(p,'App','exitApp'),'android: atrás desde el editor hace lo mismo que «‹ Volver» y no cierra la app')
    p.evaluate("window.__cbs['App.backButton']({canGoBack:false})"); p.wait_for_timeout(200)
    ok(hay(p,'App','exitApp'),'android: atrás en la pantalla de inicio sin partida cierra la app')
    # micrófono denegado al soplar: aviso con «Abrir Ajustes»
    p.evaluate("(()=>{navigator.mediaDevices.getUserMedia=()=>Promise.reject(Object.assign(new Error('x'),{name:'NotAllowedError'}))})()")
    p.evaluate("(()=>{window.__el=document.createElement('div');document.body.appendChild(window.__el);JUEGOS.soplar(window.__el,()=>{})})()"); p.click('#gMic'); p.wait_for_selector('#gAjustes')
    ok('Ajustes → Aplicaciones → Punto Ciego → Permisos → Micrófono' in p.evaluate("window.__el.innerText"),'android: micro denegado al soplar → aviso con la ruta de Android')
    p.evaluate("window.__llamadas=[]"); p.click('#gAjustes'); p.wait_for_timeout(150)
    ok(hay(p,'AudioSesion','abrirAjustes'),'android: «Abrir Ajustes» llama a AudioSesion.abrirAjustes')
    # tienda: Google Play
    p.evaluate("BLOQUEO={vieja:true};pinta()"); p.wait_for_selector('#bloqueoTienda')
    ok('Google Play' in p.evaluate("document.querySelector('#bloqueoTienda').innerText"),'android: el botón del aviso de versión dice «Abrir Google Play»')
    p.evaluate("window.__llamadas=[]"); p.click('#bloqueoTienda'); p.wait_for_timeout(200)
    ok(['Browser','open',{'url':'https://play.google.com/store/apps/details?id=es.puntostudio.puntociego'}] in p.evaluate("window.__llamadas"),'android: el botón abre la ficha de Google Play')
    ok(not errs,f'android: sin errores de JS {errs}'); ctx.close()
    # --- web: sin Capacitor, nada cambia ---
    ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
    p.goto('http://localhost:8394/'+U); portada(p)
    ok(p.evaluate("typeof window.Capacitor")=='undefined','web: no se carga Capacitor')
    ok(p.evaluate("[...document.scripts].every(s=>!/capacitor/.test(s.src))"),'web: ningún <script> de Capacitor')
    ok(p.evaluate("[...document.querySelectorAll('a[data-ext]')].map(a=>a.getAttribute('href'))")==['/privacidad/','terminos.html','/soporte/'],'web: los href de siempre')
    sin=p.evaluate("(()=>{let d=null;document.addEventListener('click',e=>{d=e.defaultPrevented;e.preventDefault()});document.querySelector('a[data-ext]').click();return d})()")
    ok(sin==False,'web: el clic en los enlaces no se intercepta')
    ok(p.evaluate("(()=>{ME={code:'ABCDE'};return urlPartida()})()")=='http://localhost:8394/?c=ABCDE','web: el enlace para compartir no cambia')
    t=p.evaluate("(()=>{BLOQUEO={vieja:true};pinta();return [document.querySelector('#bloqueo').innerText,!!document.querySelector('#bloqueoRecarga'),!!document.querySelector('#bloqueoTienda')]})()")
    ok('Recarga la página' in t[0] and t[1] and not t[2],'web, versión distinta: se pide recargar la página, como siempre')
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
