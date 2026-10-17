# Versiones de la partida: `APP_V` y `REV`

Todos los móviles de una sala comparten un único estado (`S`) y se mandan acciones. Hay dos números, los dos en `index.html`
junto a `nuevaPartida` (y en `beta/index.html`, que se genera de la raíz):

| | Qué es | Qué pasa si no coincide |
|---|---|---|
| `APP_V` | Versión del **protocolo**. Hoy **3**. | El móvil se bloquea: «Hay una versión nueva» (web) o «Actualiza la app» (app). No juega. |
| `REV` | Revisión **compatible** dentro del mismo `APP_V`. Hoy **1**. | Nada: la sala acepta a cualquiera con el mismo `APP_V`. Las funciones nuevas esperan a que todos tengan la `REV`. |

`REV` 0 es un móvil que no manda `REV` (la 1.0.1 de las tiendas): cuenta como 0.

## Cómo decidir en cada cambio

Pregúntate: **¿puede un móvil con el código anterior seguir jugando bien al lado de uno con el código nuevo, ignorando lo que no entiende?**

**Sube `REV`** (no toques `APP_V`) si el cambio **solo añade**:
- un campo nuevo en el estado (`S`), en un jugador, en `cfg`…, que el código viejo puede ignorar;
- una acción nueva (`t:'algo'`) que el código viejo ignora sin fallar (el `default` del reducer devuelve `true`);
- una función que se ve o se oye solo en los móviles nuevos y no cambia lo que hacen los demás.

**Sube `APP_V`** si el cambio **cambia o quita** algo que el código viejo usa:
- cambia la forma de una acción existente (nombres de campos, significado, valores);
- cambia la forma o el significado de un campo del estado que ya existía (por ejemplo `p.tasks`, `S.meet`, `S.cfg`);
- cambia una regla del juego que cada móvil calcula por su cuenta (el anfitrión decide y todos pintan, pero si dos móviles
  aplican reglas distintas la pantalla deja de coincidir);
- quita un campo o una acción que el código viejo necesita;
- cambia el cifrado, el tema MQTT o el formato de los mensajes.

**En la duda, sube `APP_V`:** el coste es que todos tengan que actualizar; el riesgo contrario es una partida corrupta o
móviles colgados sin aviso. Los cambios solo visuales o de textos (estilos, maquetación, mensajes, el personaje) no suben ninguno.

Al subir `APP_V`, `REV` **vuelve a 1** y `REV_FUNCS` se vacía (todo el mundo parte de cero con el protocolo nuevo). Al subir `REV`,
`APP_V` no se toca.

## Cómo añadir una función que necesita que todos la tengan (`REV`)

1. Sube `REV` (por ejemplo a 2).
2. Apunta la función en `REV_FUNCS` con la `REV` mínima de **toda** la sala: `const REV_FUNCS={reacciones:2}`.
3. En el código, todo lo que dependa de ella va detrás de `funcionActiva('reacciones')`. Es la lectura de `S.revMin`, que
   publica el anfitrión en cada estado (la `REV` más baja entre las personas de la sala; los bots no cuentan).
4. El anfitrión no activa la función hasta que todos la tienen; si entra o está un móvil con menos `REV`, sigue apagada.
   Si ese móvil se va, se enciende sola.
5. Una acción nueva la puede enviar un móvil con `REV` alta: los viejos la ignoran (`default:return true` en `reducir`). Si la
   función cambia lo que el **anfitrión** hace, el anfitrión solo la aplica si `funcionActiva` es cierto.

## Cómo viaja

- Cada acción (`accion()`) y el ping (cada 3 s) llevan `rev:REV`. `reducir` lo guarda en `p.rev` del jugador (solo enteros
  entre 0 y 999; cualquier otra cosa se ignora). El que entra con `join` ya lo trae.
- El anfitrión pone su propia `REV` en su jugador y, en cada `publicarEstado`, `S.revMin=revSala(S)`.
- El estado y las acciones de otra `REV` **no se rechazan**: los campos que no se conocen se conservan y se ignoran, y las
  acciones desconocidas se dan por atendidas (no se reintentan) sin cambiar nada.
- Un móvil con otro `APP_V` sí se rechaza, como siempre (`recibeEstado` / `recibeAccion`).

## Cómo probarlo

- `python tests/sala_mixta.py` (o `PUNTO_WEB=beta python tests/sala_mixta.py`): cuatro móviles con el mismo `APP_V` y `REV` 1, 0, 1 y 2
  juegan una partida completa contra un broker MQTT local; comprueba la `REV` mínima, que una función que pide `REV` 1 no se
  activa, y que una acción y un campo desconocidos no rompen nada.
- Al añadir una función con `REV`, amplía ese test con ella (en el test `REV_FUNCS` se sustituye por `{probe:1}`).

## Publicar

Los dos números se publican **a la vez en la raíz y en `beta/`**. `beta/index.html` se genera de `index.html` con
`python scripts/generar-beta.py`; no se edita a mano. Sube también `VERSION` de `sw.js` y de `beta/sw.js` para que los móviles
descarguen la web nueva.
