# Salir de la partida a mitad de juego (reglas del reducer + pantalla) y ⚙ de Ajustes en todas las pantallas.
# Contra el servidor que imita a Supabase. Prueba la raíz; PUNTO_WEB=beta para probar beta/.
# Uso: `python tests/salida_ajustes.py` (necesita playwright y Edge). Usa los puertos 8392 y 9999 (deben estar libres).
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

# Partida montada a mano con el reducer real: h (anfitrión), a, b, c, d; el papel de cada uno lo fija el test.
MONTA="""([roles,fase])=>{
  const now=ahora(),st=nuevaPartida('h','Hugo',LOOK0);
  for(const n of ['a','b','c','d'])reducir(st,{t:'join',pid:n,name:n.toUpperCase(),look:LOOK0},now,false);
  empezar(st,now);
  st.players.forEach(p=>{p.role=roles[p.id]||'crew';p.seen=now-(p.id==='h'?0:({a:1000,b:2000,c:3000,d:4000})[p.id])});
  window.ST=st;
  if(fase==='meeting')reunion(st,now,'a',null);
  return true}"""
RES="""()=>{const st=window.ST;return {fase:st.phase,w:st.end&&st.end.w,why:st.end&&st.end.why,host:st.hostId,ids:st.players.map(p=>p.id),
  tareas:progreso(st),salidos:st.salidos,log:st.log.map(l=>l.txt),aviso:st.aviso&&st.aviso.txt,
  meet:st.meet&&{fase:st.meet.fase,votes:st.meet.votes,listos:st.meet.listos,res:st.meet.res&&{out:st.meet.res.out}}}}"""
def salida(p,quien):
    p.evaluate("q=>reducir(window.ST,{t:'leave',pid:q,gid:window.ST.gid},ahora(),false)",quien)
    return p.evaluate(RES)

try:
    with sync_playwright() as pw:
        br=pw.chromium.launch(channel='msedge')
        ctx=br.new_context(viewport={'width':390,'height':760},is_mobile=True,has_touch=True); ctx.add_init_script("navigator.vibrate=function(){return true}")
        p=ctx.new_page(); errs=[]; p.on('pageerror',lambda e:errs.append(str(e)))
        p.goto(B); p.wait_for_selector('[data-a=invitado]')

        # ---------- 1. Reglas de salida (reducer) ----------
        # Un Ciego sale: queda fuera, sus tareas salen del total, la partida sigue y el aviso no dice su papel
        p.evaluate(MONTA,[{'h':'imp'},'play'])
        antes=p.evaluate("progreso(window.ST)"); suyas=p.evaluate("window.ST.players.find(x=>x.id==='b').tasks.reduce((s,t)=>s+t.steps.length,0)")
        r=salida(p,'b')
        ok(r['fase']=='play' and 'b' not in r['ids'] and len(r['ids'])==4,'Ciego sale: sigue la partida y deja de estar en la lista')
        ok(r['tareas']['total']==antes['total']-suyas,f"Ciego sale: sus tareas salen del total ({antes['total']} -> {r['tareas']['total']})")
        ok(r['aviso']=='B ha salido de la partida' and all('Ciego' not in l and 'Punto' not in l for l in r['log']),'Ciego sale: el aviso y el registro no revelan su papel')
        # Los Ciegos no se quedan bloqueados: si solo faltaban las tareas del que sale, ganan
        p.evaluate(MONTA,[{'h':'imp'},'play'])
        p.evaluate("(()=>{for(const q of window.ST.players)if(q.role==='crew'&&q.id!=='b')for(const t of q.tasks)t.done=t.steps.length;ganador(window.ST,ahora())})()")
        ok(p.evaluate(RES)['fase']=='play','sin la salida, faltando las tareas de uno, no han ganado')
        r=salida(p,'b'); ok(r['fase']=='end' and r['w']=='crew' and 'tareas' in r['why'],f"Ciego pendiente sale: los demás ya habían acabado, ganan los Ciegos ({r['why']})")
        # Sale el último Punto: ganan los Ciegos
        p.evaluate(MONTA,[{'c':'imp'},'play']); r=salida(p,'c')
        ok(r['fase']=='end' and r['w']=='crew' and 'último Punto' in r['why'],f"último Punto sale: ganan los Ciegos ({r['why']})")
        ok(r['salidos']['c']['role']=='imp','el papel del que salió se guarda para la pantalla final')
        # Una salida que iguala: 1 Punto y 3 Ciegos -> sale uno (sigue) -> sale otro (1 contra 1: ganan los Puntos)
        p.evaluate(MONTA,[{'d':'imp'},'play']); r=salida(p,'a'); ok(r['fase']=='play','1 Punto contra 2 Ciegos: sigue')
        r=salida(p,'b'); ok(r['fase']=='play','1 Punto contra 2 Ciegos: sigue')
        r=salida(p,'c'); ok(r['fase']=='end' and r['w']=='imp','la salida iguala a Puntos y Ciegos (1 contra 1): ganan los Puntos')
        # También con un Punto que sale cuando hay dos y los Ciegos se quedan por delante
        p.evaluate(MONTA,[{'c':'imp','d':'imp'},'play']); r=salida(p,'c'); ok(r['fase']=='play','sale un Punto de dos: sigue')
        # Un desconocido no puede sacar a nadie
        p.evaluate(MONTA,[{'d':'imp'},'play']); r=salida(p,'zzz'); ok(r['fase']=='play' and len(r['ids'])==5,'una salida de alguien que no está no hace nada')

        # ---------- 2. Salir durante una reunión / votación ----------
        p.evaluate(MONTA,[{'d':'imp'},'meeting'])
        p.evaluate("(()=>{const m=window.ST.meet;m.fase='vote';m.votes={a:'b',b:'skip',d:'b'}})()")
        r=salida(p,'b')
        ok(r['fase']=='meeting' and 'b' not in r['ids'],'sale durante la votación: la reunión sigue')
        ok(r['meet']['votes']=={},f"su voto no cuenta y quien le había votado queda sin votar {r['meet']['votes']}")
        p.evaluate("reducir(window.ST,{t:'vote',pid:'a',target:'c',gid:window.ST.gid},ahora(),false)")
        ok(p.evaluate(RES)['meet']['votes']=={'a':'c'},'quien había votado a quien salió puede volver a votar')
        ok(p.evaluate("(()=>{const h=vReunion;return true})()"),'(la reunión sigue pintándose)')
        # el último que faltaba por votar sale: la votación se resuelve
        p.evaluate("(()=>{const m=window.ST.meet;m.votes={a:'skip',d:'skip',h:'skip',b:'skip'}})()"); r=salida(p,'c')
        ok(r['meet']['fase']=='res','sale quien faltaba por votar: se cierra la votación')
        # sale en el debate: si los demás ya estaban listos, se pasa a votar
        p.evaluate(MONTA,[{'d':'imp'},'meeting']); p.evaluate("(()=>{const m=window.ST.meet;m.listos={a:true,b:true,d:true,h:true}})()")
        r=salida(p,'c'); ok(r['meet']['fase']=='vote','sale en el debate quien faltaba por estar listo: pasa a votar')
        # sale el último Punto en plena reunión: se acaba
        p.evaluate(MONTA,[{'d':'imp'},'meeting']); r=salida(p,'d')
        ok(r['fase']=='end' and r['w']=='crew','el último Punto sale en la reunión: ganan los Ciegos al momento')
        # los dos últimos Ciegos salen en la reunión y el Punto queda al par
        p.evaluate(MONTA,[{'d':'imp'},'meeting']); salida(p,'a'); salida(p,'b'); r=salida(p,'c'); ok(r['fase']=='end' and r['w']=='imp','salidas en la reunión que igualan: ganan los Puntos')
        # votos que otro había dado a quien sale cuando ya se había votado y se expulsa a otro: sin errores
        p.evaluate(MONTA,[{'d':'imp'},'meeting']); p.evaluate("(()=>{const m=window.ST.meet;m.fase='vote';m.votes={a:'c',b:'c'}})()")
        r=salida(p,'c'); ok('c' not in r['ids'] and r['meet']['votes']=={} and r['meet']['fase']=='vote','los votos a quien sale desaparecen y la votación sigue abierta')
        p.evaluate("(()=>{for(const q of ['a','b','d','h'])reducir(window.ST,{t:'vote',pid:q,target:'skip',gid:window.ST.gid},ahora(),false)})()"); r=p.evaluate(RES)
        ok(r['meet']['fase']=='res' and r['meet']['res']['out'] is None,'tras volver a votar nadie queda expulsado por votos a quien ya no está')

        # ---------- 3. Salir siendo anfitrión: el mando pasa ----------
        p.evaluate(MONTA,[{'d':'imp'},'play']); r=salida(p,'h')
        ok(r['fase']=='play' and r['host']=='a' and 'h' not in r['ids'],f"el anfitrión sale a mitad de partida: el mando pasa al conectado más reciente ({r['host']})")
        p.evaluate(MONTA,[{'d':'imp'},'meeting']); r=salida(p,'h'); ok(r['host']!='h' and r['fase']=='meeting','el anfitrión sale en una reunión: también pasa el mando')

        # ---------- 4. Pantallas: «Salir de la partida» y ⚙ ----------
        PINTA="""([rol,fase,sub,quien])=>{
          const st=window.ST;S=st;ME={code:'ABCDE',pid:quien,name:'x'};VISTA='portada';
          LS.set('imp.rol.'+st.gid,1);
          const m=st.meet;
          if(fase==='meeting'){if(!m){reunion(st,ahora(),'a',null)}const mm=st.meet;if(sub==='vote'){mm.fase='vote';mm.until=ahora()+60000}if(sub==='res'){mm.fase='res';mm.res={out:null,empate:false,cuenta:{},imp:false,quedan:1};mm.until=ahora()+60000}}
          if(fase==='muerto'){const q=st.players.find(x=>x.id===quien);q.dead=true;q.body=true}
          if(fase==='revela')LS.del('imp.rol.'+st.gid);
          if(fase==='end'){st.phase='end';st.end={w:'crew',why:'Prueba',t:ahora()}}
          repinta();return true}"""
        def pantalla(rol,fase,sub,quien):
            p.evaluate(MONTA,[{'d':'imp'},'play']); p.evaluate(PINTA,[rol,fase,sub,quien]); p.wait_for_timeout(120)
        textos=set();
        for fase,sub in [('play',''),('meeting','disc'),('meeting','vote'),('meeting','res'),('muerto','')]:
            for quien in ['h','a','d']:   # anfitrión, Ciego y Punto
                pantalla('',fase,sub,quien)
                vis=p.evaluate("[...document.querySelectorAll('[data-a=salirPartida]')].filter(e=>!e.closest('[inert]')).map(e=>e.textContent)")  # el de debajo de una pantalla completa queda inerte
                n=len(vis); txt=vis[0] if vis else None
                textos.add((fase,sub,n,txt))
                ok(n==1 and txt=='Salir de la partida',f"{fase} {sub}: «Salir de la partida» para {'el anfitrión' if quien=='h' else 'un Ciego' if quien=='a' else 'el Punto'}")
        # confirmación: abre la hoja, «Seguir» no sale, «Salir» sí
        pantalla('','play','','a'); p.click('[data-a=salirPartida]'); p.wait_for_selector('[data-a=salirPartidaOk]')
        ok('papel' in p.inner_text('#shBody') and p.locator('#shPie [data-a=cerrarSheet]').count()==1,'la confirmación explica que el papel no se revela y deja volver')
        p.click('#shPie [data-a=cerrarSheet]'); ok(p.evaluate("!!ME.code")==True,'«Volver» en la confirmación no saca de la partida')

        # ⚙ en todas las pantallas: mismo sitio, único, sin tapar nada y sin interferir con el «mantener pulsado»
        MIDE="""()=>{
          const f=document.getElementById('ajFab');if(!f)return null;const r=f.getBoundingClientRect(),cs=getComputedStyle(f);
          const solapa=[...document.querySelectorAll('button,a,input,summary,[data-hold],[role=button]')].filter(e=>e!==f&&!e.closest('[inert],[hidden]')&&e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden').filter(e=>{
            const b=e.getBoundingClientRect();return b.width>0&&b.height>0&&b.left<r.right&&b.right>r.left&&b.top<r.bottom&&b.bottom>r.top}).map(e=>(e.dataset.a||e.id||e.tagName)+':'+(e.textContent||'').trim().slice(0,20));
          const c=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
          return {x:Math.round(r.left),y:Math.round(r.top),w:Math.round(r.width),h:Math.round(r.height),solapa,encima:c===f,n:document.querySelectorAll('[data-a=ajustes]').length,pos:cs.position,top:cs.top}}"""
        def mide(nombre,ref=[None]):
            m=p.evaluate(MIDE);
            if m is None: ok(False,f'⚙ en {nombre}: no existe'); return
            if ref[0] is None: ref[0]=(m['x'],m['y'],m['w'],m['h'])
            ok((m['x'],m['y'],m['w'],m['h'])==ref[0],f"⚙ en {nombre}: misma posición {ref[0]}")
            ok(m['n']==1 and m['encima'],f'⚙ en {nombre}: único y pulsable (nada encima)')
            ok(m['solapa']==[],f"⚙ en {nombre}: no tapa ningún botón {m['solapa']}")
        # antes de entrar
        pn=ctx.new_page(); pn.goto(B); pn.wait_for_selector('[data-a=entrarCuenta]')
        m0=pn.evaluate(MIDE); ok(m0 is not None and m0['encima'] and m0['solapa']==[],f"⚙ en la pantalla de acceso, sin tapar nada {m0 and m0['solapa']}"); pn.close()
        p.reload(); p.wait_for_selector('[data-a=invitado]'); p.click('[data-a=invitado]'); p.wait_for_selector('[data-a=jugar]'); mide('portada')
        p.click('[data-a=ajustes]'); p.wait_for_selector('[data-a=ajVibra]')
        ok(p.locator('[data-a=ajTema]').count()==3 and p.locator('[data-a=ajSonido]').count()==0 and p.locator('[data-a=ajVibra]').count()==1,'portada: Tema y Vibración'); p.click('#shPie [data-a=cerrarSheet]')
        p.click('[data-a=jugar]'); p.wait_for_selector('#nom'); mide('editor del personaje')
        p.fill('#nom','Hugo'); p.wait_for_timeout(600); p.click('[data-a=guardarPerfil]'); p.wait_for_selector('[data-a=crear]'); mide('menú de jugar')
        p.click('[data-a=crear]'); p.wait_for_selector('[data-a=botMas3]'); mide('sala de espera')
        p.click('[data-a=ajustes]'); p.wait_for_selector('[data-a=ajVibra]')
        ok(p.locator('[data-a=ajTema]').count()==0 and p.locator('[data-a=ajVibra]').count()==1,'sala de espera: solo Vibración'); p.click('#shPie [data-a=cerrarSheet]')
        # partida montada con el reducer real, vista por cada papel
        for quien,nombre in [('h','anfitrión'),('a','Ciego'),('d','Punto')]:
            for fase,sub,nom in [('revela','','reparto de papel'),('play','','partida'),('meeting','disc','reunión (debate)'),('meeting','vote','votación'),('meeting','res','resultado de la votación'),('muerto','','te han matado'),('end','','final')]:
                pantalla('',fase,sub,quien); mide(f'{nom} ({nombre})')
        # «mantener pulsado» del papel: el ⚙ está lejos de la zona de pulsación
        pantalla('','revela','','a'); hold=p.evaluate("(()=>{const e=document.querySelector('[data-hold=papel]').getBoundingClientRect();const f=document.getElementById('ajFab').getBoundingClientRect();return e.left<f.right&&e.right>f.left&&e.top<f.bottom&&e.bottom>f.top})()")
        ok(hold==False,'reparto de papel: el ⚙ no solapa la zona de «mantener pulsado»')
        # zona segura del iPhone y capa por encima de las pantallas completas
        css=p.evaluate("[...document.styleSheets].flatMap(s=>[...s.cssRules]).filter(r=>r.selectorText==='#ajFab').map(r=>r.cssText).join(' ')")
        ok('safe-area-inset-top' in css and 'safe-area-inset-right' in css,'⚙ respeta la zona segura (arriba y derecha)')
        z=p.evaluate("[+getComputedStyle(document.getElementById('ajFab')).zIndex,+getComputedStyle(document.getElementById('over')).zIndex,+getComputedStyle(document.getElementById('sheet')).zIndex]")
        ok(z[0]>z[1] and z[0]<z[2],f'⚙ por encima de las pantallas completas y por debajo de las hojas {z}')
        # el ⚙ ya no está duplicado en la cabecera de tareas ni en la portada
        pantalla('','play','','a'); ok(p.locator('.aj-juego,.aj-btn').count()==0,'sin segundo ⚙ en la cabecera de tareas ni en la portada')
        # en partida (reunión incluida): ajustes con efecto inmediato
        pantalla('','meeting','vote','a'); p.click('#ajFab'); p.wait_for_selector('[data-a=ajVibra]')
        ok(p.locator('[data-a=ajTema]').count()==0,'reunión: sin Tema')
        p.click('[data-a=ajVibra]'); ok(p.evaluate("SET.vibra")==False,'reunión: la vibración se apaga al instante'); p.click('[data-a=ajVibra]'); p.click('#shPie [data-a=cerrarSheet]')
        ok(not errs,f'sin errores de JS {errs}')

        # ---------- 5. Salida real desde la pantalla, con bots (anfitrión) ----------
        p.evaluate('salir()'); p.wait_for_selector('[data-a=crear]')
        p.click('[data-a=crear]'); p.wait_for_selector('[data-a=botMas3]'); p.click('[data-a=botMas3]'); p.wait_for_timeout(400)
        p.evaluate("accion('pruebas',{rol:'crew',vel:'rapida'})"); p.evaluate("accion('cfg',{cfg:{killCd:10,disc:0,vote:15,tasks:2,largas:0,emerg:1}})")
        p.click('[data-a=empezar]'); p.wait_for_function("S&&S.phase==='play'",timeout=8000); p.wait_for_selector('[data-hold=papel]')
        box=p.locator('[data-hold=papel]').bounding_box(); p.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2); p.mouse.down(); p.wait_for_timeout(300); p.mouse.up()
        p.wait_for_selector('[data-a=entendido]'); p.click('[data-a=entendido]'); p.wait_for_timeout(500)
        n0=p.evaluate("S.players.length"); p.click('[data-a=salirPartida]'); p.wait_for_selector('[data-a=salirPartidaOk]'); p.click('[data-a=salirPartidaOk]'); p.wait_for_timeout(900)
        ok(p.evaluate("ME.code")==None and p.evaluate("S")==None,f'salir de la partida (anfitrión con bots, {n0} jugadores): vuelve al menú')
        ok(not errs,f'sin errores de JS al salir {errs}')
        br.close()
finally:
    pr.terminate()
print('\nFALLOS:',len(fallos)); sys.exit(1 if fallos else 0)
