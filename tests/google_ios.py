# Google nativo en la app iOS: configuración coherente (ID de cliente iOS, esquema en Info.plist, plugin, AppDelegate) y flujo en la app
# con un puente de Capacitor simulado: botón de Google junto a Apple, initialize con iOS + servidor, nonce con hash a Google y original a Supabase.
# Uso: `python tests/google_ios.py` (playwright y Edge). Usa el puerto 8395.
import os,re,sys,json,hashlib,subprocess,threading,functools,http.server
from playwright.sync_api import sync_playwright
RAIZ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fallos=[]
def ok(c,m):
    print(('OK   ' if c else 'FALLA ')+m)
    if not c: fallos.append(m)
def lee(*r): return open(os.path.join(RAIZ,*r),encoding='utf-8').read()
html=lee('index.html'); plist=lee('ios','App','App','Info.plist')
ios=re.search(r"const GOOGLE_IOS_ID='([^']*)'",html).group(1); web=re.search(r"const GOOGLE_WEB_ID='([^']*)'",html).group(1)
# --- configuración estática ---
ok(re.fullmatch(r'\d+-[a-z0-9]+\.apps\.googleusercontent\.com',web) is not None,'GOOGLE_WEB_ID tiene formato de ID de cliente')
ok(web in lee('supabase','config.toml'),'GOOGLE_WEB_ID es el cliente web de Supabase (config.toml)')
ok(ios!=web,'el ID de cliente iOS no es el del web (Google rechaza el nativo con el cliente web)')
esquemas=re.findall(r'<string>(com\.googleusercontent\.apps\.[^<]+)</string>',plist)
if ios:
    ok(re.fullmatch(r'\d+-[a-z0-9]+\.apps\.googleusercontent\.com',ios) is not None,'GOOGLE_IOS_ID tiene formato de ID de cliente')
    ok(['com.googleusercontent.apps.'+ios.replace('.apps.googleusercontent.com','')]==esquemas,'Info.plist: el esquema inverso es el de GOOGLE_IOS_ID')
else:
    print('AVISO GOOGLE_IOS_ID vacío: la app NO muestra Google hasta pegarlo (y el esquema de Info.plist)')
    ok(esquemas==['com.googleusercontent.apps.REEMPLAZAR'],'Info.plist: esquema pendiente de rellenar a la vez que GOOGLE_IOS_ID')
ok('GIDSignIn.sharedInstance.handle(url)' in lee('ios','App','App','AppDelegate.swift'),'AppDelegate devuelve la URL de vuelta a Google')
ok('CapgoCapacitorSocialLogin' in lee('ios','App','Podfile'),'Podfile: pod del plugin de Google')
ok(json.loads(lee('capacitor.config.json'))['plugins']['SocialLogin']['providers']['google'] is True,'capacitor.config.json: proveedor Google activo')
ok('apple-sign-in' in lee('ios','App','Podfile') or 'AppleSignIn' in lee('ios','App','Podfile'),'Apple sigue en el Podfile')
# --- flujo en la app (puente simulado) ---
subprocess.run(['node',os.path.join(RAIZ,'scripts','preparar-www.mjs')],cwd=RAIZ,check=True,stdout=subprocess.DEVNULL)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8395),functools.partial(Q,directory=os.path.join(RAIZ,'www'))); threading.Thread(target=srv.serve_forever,daemon=True).start()
PUENTE="""window.__llamadas=[];window.webkit={messageHandlers:{bridge:{postMessage(){}}}};
window.Capacitor={isNativePlatform:()=>true,PluginHeaders:[{name:'SocialLogin',methods:[{name:'initialize',rtype:'promise'},{name:'login',rtype:'promise'}]},{name:'SignInWithApple',methods:[{name:'authorize',rtype:'promise'}]}],
  nativePromise:(pl,m,o)=>{window.__llamadas.push([pl,m,o]);return Promise.resolve(m==='login'?{result:{idToken:'token-de-google'}}:{})}};"""
IOS_PRUEBA=ios or '111-abc.apps.googleusercontent.com' # con el ID real no hace falta parchear el HTML
with sync_playwright() as pw:
    br=pw.chromium.launch(channel='msedge')
    def abre(parcheado):
        ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
        if parcheado:
            def ruta(r):
                b=r.fetch().text().replace("const GOOGLE_IOS_ID='';","const GOOGLE_IOS_ID='"+IOS_PRUEBA+"';"); r.fulfill(status=200,content_type='text/html; charset=utf-8',body=b)
            p.route(re.compile(r'.*/(\?.*)?$'),ruta)
        p.add_init_script(PUENTE); p.goto('http://localhost:8395/?supa=x&supakey=x'); p.wait_for_selector('[data-a=entrarCuenta]'); return p,errs
    p,errs=abre(False)
    p.evaluate("GOOGLE=!!GOOGLE_IOS_ID;APPLE=true;pinta()"); p.wait_for_timeout(200)
    orden=p.evaluate("[...document.querySelectorAll('#app [data-a=google],#app [data-a=apple]')].map(e=>e.dataset.a)")
    ok(('google' in orden)==bool(ios) and 'apple' in orden,f'app con el index real: Apple siempre, Google solo con GOOGLE_IOS_ID {orden}')
    p,errs=abre(not ios)
    # el sondeo de /auth/v1/settings usa la lógica real: se reproduce su condición con Google activo en Supabase
    ok(p.evaluate("EN_APP&&!!GOOGLE_IOS_ID"),'app con ID de cliente iOS: la condición de mostrar Google se cumple')
    p.evaluate("GOOGLE=true;APPLE=true;pinta()"); p.wait_for_timeout(200)
    orden=p.evaluate("[...document.querySelectorAll('#app [data-a=google],#app [data-a=apple]')].map(e=>e.dataset.a)")
    ok(orden==['apple','google'],f'app: Apple y Google, Apple primero {orden}')
    p.evaluate("SB.auth.signInWithIdToken=async o=>{window.__idt=o;return {error:null}}")
    p.click('[data-a=google]'); p.wait_for_function("window.__idt",timeout=5000)
    ll=p.evaluate("window.__llamadas"); ini=[x for x in ll if x[1]=='initialize'][0][2]; lo=[x for x in ll if x[1]=='login'][0][2]; idt=p.evaluate("window.__idt")
    g=ini['google']
    ok(g['iOSClientId']==IOS_PRUEBA and g['iOSServerClientId']==web and g['mode']=='online','initialize: cliente iOS + cliente web como servidor')
    ok(lo['provider']=='google' and lo['options']['forcePrompt'] is True,'login de Google con selector de cuenta')
    ok(idt['provider']=='google' and idt['token']=='token-de-google','signInWithIdToken recibe el token de Google')
    ok(lo['options']['nonce']==hashlib.sha256(idt['nonce'].encode()).hexdigest(),'nonce: hash a Google, original a Supabase')
    ok(p.evaluate("!window.__llamadas.some(x=>x[0]==='Browser')"),'sin redirección web ni navegador externo')
    ok(not errs,f'sin errores de JS {errs}')
    br.close()
srv.shutdown()
print('\nFALLOS:',len(fallos)); sys.exit(1 if fallos else 0)
