# Punto Ciego

No puedes confiar en lo que ves: se juega por la casa con el móvil. Unos jugadores son
tripulantes y hacen tareas por las habitaciones; otros son impostores y sabotean y eliminan
sin que los vean. Cuando alguien encuentra un cuerpo, o pulsa la emergencia, se abre una
reunión y se vota a quién expulsar.

Un juego de Punto Studio, hermano de [Punto Falso](https://puntostudio.es/punto-falso/).

Es una web estática: `index.html` (HTML, CSS y JS) más una carpeta `assets/` con el personaje.
No tiene paso de compilación ni dependencias que instalar.

## El personaje 3D

El personaje es un modelo 3D real que se dibuja con un renderizador WebGL propio y sin
dependencias (`assets/personaje3d.js`, un único contexto WebGL para toda la app):

- `assets/personaje.bin`: la malla (26 k triángulos, ~300 KB). Solo se descarga al llegar al menú.
- `assets/img/*.webp` y `assets/img/m_*.png`: imágenes del look de serie y sus máscaras. Son el
  respaldo si el navegador no tiene WebGL (se recolorean en 2D) y el marcador mientras carga.
- Los colores de capucha, sudadera, pantalón, mochila, estampado, guantes y ojos se aplican en el shader; las zonas
  se calculan con la posición en reposo de cada vértice, así que seguirán valiendo cuando la malla
  se deforme con un esqueleto. La unión capucha/cuello es una línea curva calculada sobre la malla y horneada
  en el canal `w` de la posición en reposo. Pantalón y mochila valen 0 = «como la sudadera» (así los looks
  guardados antes de existir esos campos se ven igual).
- Menú, editor (se gira arrastrando), revelado, reunión y muerte son vistas vivas con animación.
  Los avatares de listas y votaciones son imágenes (`data:` URL) generadas con el mismo modelo.
  El bucle de dibujo solo corre si hay un 3D visible y la pestaña está activa, y respeta
  `prefers-reduced-motion`.

El modelo original y los archivos pesados de origen están en `fuentes/`, que **no** se sube
al repositorio (`.gitignore`).

## Dependencias de terceros

La única dependencia de terceros de todo el proyecto es el generador de códigos QR con el que
se puede entrar en una partida escaneando en vez de escribir el código: `assets/qr.js`,
vendorizado (el archivo copiado tal cual en el repo, no instalado como paquete) a partir de
[`qrcode-generator`](https://github.com/kazuhikoarase/qrcode-generator) de Kazuhiko Arase
(licencia MIT). No hace ninguna llamada a internet ni a ningún servicio externo: el QR se calcula
entero en el propio móvil, igual que el resto de la app.

## Cómo se juega

1. Cada jugador abre la web en su móvil, pulsa **Jugar** y entra con su cuenta (o crea una).
2. Un jugador crea la partida y comparte el código; los demás se unen con él.
3. El anfitrión configura habitaciones, número de impostores y tareas, y empieza la partida.
4. Se reparten los roles en secreto. Tripulantes: completad las tareas. Impostores: eliminad
   y sabotead sin que os pillen.
5. Al encontrar un cuerpo o usar la emergencia hay reunión y votación. Ganan los tripulantes si
   completan las tareas o echan a todos los impostores; ganan los impostores si igualan en número.

Las partidas y el walkie viajan por MQTT cifrado a través de brokers públicos; no hay servidor propio.

## Modo bots (jugar solo, para la revisión de Apple y las pruebas)

Solo lo ven las cuentas con `puede_bots = true` en su fila de `profiles`. Ese indicador **solo se cambia desde el servidor**
(un trigger de Supabase lo fuerza a `false` al crear el perfil y lo conserva al actualizarlo cuando quien llama es la app, así que
ni el cliente ni un `upsert` manual pueden activarlo). La migración es `supabase/migrations/20261008120000_puede_bots.sql`.

Activarlo en una cuenta (SQL Editor de Supabase; el perfil debe existir, es decir, la cuenta ya ha creado su personaje):

```sql
update public.profiles set puede_bots = true
where id = (select id from auth.users where email = 'revisor@ejemplo.com');
```

Quitarlo: lo mismo con `false`. Ver quién lo tiene: `select username from public.profiles where puede_bots;`.

- **Sala de espera** (solo el anfitrión): bloque *Bots* con **Añadir bots** (3 de golpe; con el anfitrión ya son los 4 que hacen
  falta), *+1 bot* y *Quitar bots*; elegir tu papel en la próxima partida (aleatorio, Ciego, Punto) y la velocidad de los bots
  (lenta, normal, rápida).
- **Los bots** se unen, reciben rol, hacen tareas con esperas de 20 a 50 s (o la duración real de las tareas de vida real), reportan
  cuerpos, votan en las reuniones, pueden ser expulsados o muertos, y el bot Punto mata y sabotea (gas, luces, comunicaciones, puertas).
  No hablan por el walkie.
- **Durante la partida**: botón discreto *⚡ Atajos* para convocar una reunión ya, saltar el debate, terminar la votación,
  hacer que un bot Punto mate a alguien (incluido tú), lanzar cualquier sabotaje o completar las tareas de los bots.
- Los bots viven en el navegador del anfitrión: generan acciones con ids `bot-1`, `bot-2`… y se aplican con el mismo
  reducer que las de los jugadores reales. Si el anfitrión se desconecta, se paran. Si entra una persona en la sala, se acaba el
  modo y los bots se van.
- Las partidas con bots **no** cuentan para las estadísticas de Supabase. El enlace de *Compartir* no lleva ningún parámetro
  especial y las acciones que llegan por la red con id de bot se descartan.
- Si la cuenta no tiene el indicador, o la migración aún no está aplicada, no existe nada de esto (ni panel ni atajos).
- Para los tests en local, `?pruebas=1` sigue activándolo **solo en localhost**; en producción ese parámetro no hace nada.
  `python tests/bots_cuenta.py` comprueba el indicador y partidas completas como Ciego y como Punto.

## Instalable y fichas de tienda

- Es instalable (PWA): `manifest.json`, iconos en `assets/icons/` y etiquetas de iOS (pantalla completa, barra de estado oscura). La beta tiene su propio `manifest.json` y `sw.js` (copias en `beta/`).
- `sw.js` tiene la caché versionada (`VERSION`): **sube `VERSION` al pasar cambios a la principal**. Red primero con revalidación, precarga de lo básico y recarga automática si estás en la portada.
- `privacidad.html` y `soporte.html` (en la raíz y en `beta/`) se enlazan desde la portada, el acceso y el perfil. Al pasar la beta a la principal no hace falta tocarlos.
- `tienda.md` y `tienda/capturas/` son el material de las fichas; las capturas se regeneran con `tienda/capturar.js`.

## Bloquear y reportar, y borrado de cuenta

- **Bloquear / reportar**: en la lista de jugadores («Bloquear») y con ⚑ junto a los mensajes del walkie. Bloquear oculta la voz y los mensajes de ese jugador en esa partida, solo en ese móvil (`imp.bloq.<código>` en localStorage). Reportar abre un correo a `SUPPORT_MAIL` con nombre, id, código de partida y fecha. No hay moderación ni servidor nuevo; los textos avisan de que el chat es entre amigos y sin moderar.
- **Eliminar cuenta**: la cuenta es **compartida con Punto Falso** (mismo proyecto de Supabase y misma tabla `profiles`): borrarla en un juego la borra en el otro, y así lo dice el aviso de los dos. El cliente llama a la Edge Function `eliminar-cuenta` (que revoca el token de Apple si hace falta y borra) y, si no está desplegada o falla, usa el respaldo `eliminar_mi_cuenta()`. Ver `docs/BORRADO_APPLE.md`.

## Cómo se publica (GitHub Pages)

1. Sube el repositorio a GitHub (rama `main`).
2. En **Settings > Pages**, elige *Deploy from a branch*, rama `main`, carpeta `/ (root)`.
3. La web se sirve desde GitHub Pages; la dirección pública es `https://puntostudio.es/punto-ciego/` (la antigua de github.io redirige sola).

El archivo `.nojekyll` hace que GitHub Pages sirva `index.html` tal cual.

## Cómo se configura Supabase (cuentas de jugador)

Las cuentas, los looks y las estadísticas usan [Supabase](https://supabase.com). Si no se
configura, el juego funciona igualmente y guarda el perfil solo en cada móvil.

1. Crea un proyecto en Supabase (región Europa).
2. Aplica la migración `supabase/migrations/*_perfiles.sql`. Con la CLI:
   ```bash
   supabase link --project-ref TU_REF
   supabase db push
   ```
   O pégala entera en **SQL Editor > New query > Run**.
   Crea la tabla `profiles`, sus políticas RLS y la función `sumar_partida`.
3. En **Authentication > Sign In / Providers > Email**, deja activado **Confirm email**: quien se registra con
   correo no abre sesión hasta pulsar el enlace (Google y Apple entran directamente). El correo gratuito de
   Supabase solo envía a miembros del equipo y con un límite muy bajo, así que hace falta un **SMTP propio**
   (Authentication > Emails > SMTP Settings, p. ej. un remitente de puntostudio.es). Las plantillas con la marca
   están en `supabase/templates/` (`confirmar.html`, `recuperar.html`) y se pegan en Authentication > Emails > Templates.
4. En **Authentication > URL Configuration**, pon como *Site URL* la URL de GitHub Pages
   y añádela también a *Redirect URLs*.
5. En **Project Settings > API Keys** copia la *Project URL* y la clave **publishable**
   (`sb_publishable_...`) y pégalas en el bloque `const SUPA={url:'...',key:'...'}` de `index.html`.

> La clave publicable puede estar en el repositorio porque la tabla está protegida con RLS.
> **Nunca** subas una clave `sb_secret_...` ni `service_role`.

### Probar cuentas en local sin tocar Supabase

`mocksb.js` es un servidor local (Node, sin dependencias) que imita lo justo de la API de
Supabase (cuentas, perfiles, borrado de cuenta) para probar esos flujos sin conexión ni riesgo
sobre el proyecto real:

```bash
node mocksb.js          # escucha en http://localhost:9999
```

Y abre la beta apuntando a él:

```
http://localhost:8080/beta/?supa=http://localhost:9999&supakey=local&pruebas=1
```

Los datos de prueba se guardan en `.mocksb-data.json` (no se sube a git); bórralo para
empezar de cero.

## Cómo actualizar el juego: beta → principal

Hay dos copias de la web:

- **Principal** (raíz: `index.html` y `assets/`): `https://puntostudio.es/punto-ciego/`. La usan los jugadores.
- **Beta** (`beta/`): `https://puntostudio.es/punto-ciego/beta/`. Zona de pruebas permanente, con una etiqueta roja
  «BETA» y «(beta)» en el título. Comparte cuentas y base de datos con la principal.

Flujo de trabajo: los cambios se hacen siempre en `beta/`, se prueban en el iPhone y, cuando están bien, se pasan a la raíz:

```bash
git tag antes-beta-AAAA-MM-DD && git push origin antes-beta-AAAA-MM-DD   # punto de vuelta atrás
cp beta/index.html index.html && cp -r beta/assets/. assets/ && cp beta/NOTAS_ESQUELETO.md NOTAS_ESQUELETO.md
# en index.html: quita <div id="betaTag"...> y el «(beta)» del <title>
git add -A index.html assets NOTAS_ESQUELETO.md && git commit -m "Describe el cambio" && git push
```

Si cambias `assets/personaje.bin`, `personaje3d.js`, `qr.js` o las imágenes, sube su `?v=` en `index.html` (y el `bin:` de
`personaje3d.js`) para que los móviles no se queden con la versión vieja en caché.

### Versión de la partida (`APP_V`)

> Hay dos números: `APP_V` (protocolo; bloquea) y `REV` (cambios que solo añaden; no bloquea y las funciones nuevas esperan a toda la sala). Cómo elegir: [docs/VERSIONES.md](docs/VERSIONES.md). `beta/index.html` se genera con `python scripts/generar-beta.py`.

`APP_V` (en `index.html`, junto a `nuevaPartida`) es el número de versión de la partida compartida. Un móvil cuya
versión no coincide con la de la partida se bloquea con el aviso «Hay una versión nueva, recarga la página».

- **Súbelo** cuando el cambio afecte a la partida compartida: acciones nuevas o cambiadas, campos nuevos o cambiados en
  el estado de la partida, o reglas del juego. Dos versiones distintas no podrían jugar bien juntas.
- **No hace falta** en cambios solo visuales o de textos (estilos, maquetación, mensajes, el personaje...).
- **En la duda, súbelo:** el coste es que todos tengan que recargar; el riesgo de no subirlo es una partida
  corrupta o móviles que se quedan colgados sin aviso.
- Se sube **a la vez en `beta/` y en la raíz** al pasar a la principal, y al pasarlo hay que avisar a los jugadores de que recarguen.
- Los móviles anteriores al control de versión (antes de `APP_V=2`) no pueden mostrar el bloqueo: solo reciben un aviso breve.

Para volver a una versión anterior: `git revert <commit>` (o restaurar los archivos de la etiqueta con
`git checkout <etiqueta> -- index.html assets`) y push.

Para probar en local, sirve la carpeta con cualquier servidor estático, por ejemplo
`python -m http.server 8000`, y abre `http://localhost:8000` (principal) o `http://localhost:8000/beta/`.

## Avisos

- Los proyectos gratuitos de Supabase se **pausan** si no se usan durante varios días
  (se reactivan desde el panel).
- "He olvidado la contraseña" **no enviará correos** mientras no se configure un SMTP propio en Supabase.
