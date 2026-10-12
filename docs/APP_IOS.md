# App iOS (Capacitor)

Bundle ID `es.puntostudio.puntociego`, nombre «Punto Ciego». La web **no cambia de sitio**: GitHub Pages sigue sirviendo la raíz del
repo. `npm run web` copia lo necesario a `www/` (ignorado por git) y Capacitor lo mete en la app.

```
npm install
npm run cap:sync     # copia la web a www/ y sincroniza ios/
npm run cap:abrir    # lo anterior + abre Xcode
```

Hace falta un Mac con Xcode y CocoaPods (`cd ios/App && pod install`; Capacitor 8; el plugin de Apple 7.1 admite `@capacitor/core >=7`).
En Xcode: elegir el Team en *Signing & Capabilities* (la capability *Sign in with Apple* ya está en `App.entitlements`).

## Sign in with Apple
- **Web**: `signInWithOAuth({provider:'apple'})` (Services ID).
- **App nativa**: plugin `@capacitor-community/apple-sign-in` → `signInWithIdToken` con nonce (a Apple, el hash SHA-256; a Supabase, el original).
- **Plugins desde JS sin bundler**: el puente nativo inyecta `window.Capacitor` sin `registerPlugin`. `scripts/preparar-www.mjs` copia el UMD de `@capacitor/core` a `www/assets/capacitor.js` e `index.html` lo carga solo si `Capacitor.isNativePlatform()` (en la web no existe). Los plugins se piden con `plugin('Browser')` y `plugin('SignInWithApple')`, el `jsName` nativo de cada uno.
- **Vibración y audio**: `@capacitor/haptics` 8.0.2 (versión exacta; sin API de privacidad de motivo obligatorio, así que `PrivacyInfo.xcprivacy` no cambia), usado como `window.Capacitor.Plugins.Haptics.vibrate()` dentro de try/catch; en la web, `navigator.vibrate`. Solo vibran (y suenan) los avisos que llegan a todos a la vez (`avisa()` en `index.html`). Sesión de audio: `navigator.audioSession.type` = `ambient` por defecto y `play-and-record` mientras el walkie está abierto o una prueba usa el micro (`audioUso()`); el plugin local `AudioSesion.swift` (categoría nativa) queda de respaldo. El `console.log` `AUDIO tipo=…` y `HAPTIC ok/error` son temporales, para comprobarlo en Xcode.
- **Enlaces externos**: en la app la página va en `capacitor://localhost`, así que Privacidad, Términos y Soporte se abren con `@capacitor/browser` (`Browser.open`) y su URL pública `https://puntostudio.es/punto-ciego/*.html` (`enlaceLegal()` en `index.html`); el enlace de compartir, el QR y las redirecciones de los correos de Supabase llevan la web pública. Google en la app va con login nativo (ver «Google en la app»), no con OAuth web (su vuelta acabaría en Safari).
  Ver `entraConAppleNativo` en `index.html`. En Supabase → Providers → Apple, el **Bundle ID** debe estar en *Client IDs* (junto al Services ID).
- **Revocación al borrar la cuenta**: tras entrar, la app manda el `authorizationCode` (caduca a los 5 min) a la Edge Function
  `apple-canjear-codigo`, que lo canjea en `appleid.apple.com/auth/token` con `client_id` = Bundle ID y guarda el refresh token en
  `apple_tokens` (solo service role, `origen='app'`). `eliminar-cuenta` lo revoca con `/auth/revoke` antes de borrar al usuario:
  Bundle ID (`APPLE_CLIENT_ID_APP`) para logins de la app, Services ID (`APPLE_CLIENT_ID_WEB`) para los de la web.
  Las dos apps nativas (Punto Ciego `es.puntostudio.puntociego` y Punto Falso `es.puntostudio.puntofalso`) comparten estas funciones: la app envía su Bundle ID como `clientId`, la función lo valida contra la lista permitida (`BUNDLE_IDS_APP` en `_shared/apple.ts`) y lo guarda en `apple_tokens.client_id`; `eliminar-cuenta` revoca con ese client_id (filas antiguas sin él: el de siempre según `origen`). Migración: `20261008130000_apple_tokens_client_id.sql`.
  Secretos: `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY` (contenido del .p8), `APPLE_CLIENT_ID_APP`, `APPLE_CLIENT_ID_WEB`.
  Desplegar: `npx supabase functions deploy apple-canjear-codigo --project-ref qsmcdfyyxvqmesnbwsod` (y de nuevo `eliminar-cuenta`).


## Google en la app

Plugin `@capgo/capacitor-social-login` (pod `CapgoCapacitorSocialLogin`, solo con Google: `capacitor.config.json` desactiva Facebook, Apple y Twitter del plugin) + `supabase.auth.signInWithIdToken({provider:'google'})` con nonce (a Google se le pasa el hash; a Supabase, el original), igual que Apple. En la app, Apple sale por encima de Google.

Mientras `GOOGLE_IOS_ID` (index.html) esté vacío, la app no muestra el botón de Google. **Tiene que ser un ID de cliente de tipo iOS, distinto del web**: con el del web (`GOOGLE_WEB_ID`, el de Supabase en `supabase/config.toml`) Google rechaza el inicio de sesión nativo. `tests/google_ios.py` lo comprueba y también que el esquema de `Info.plist` coincide. La app pasa además `GOOGLE_WEB_ID` como `iOSServerClientId`, de modo que el token lleva el cliente web como audiencia.

1. **Google Cloud Console** → proyecto de Punto Studio → APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth → tipo **iOS**, ID de paquete `es.puntostudio.puntociego`. Si falta, configura antes la pantalla de consentimiento.
2. Copia el **ID de cliente** (`NNNN-xxxx.apps.googleusercontent.com`) a `GOOGLE_IOS_ID` en `index.html`.
3. En `ios/App/App/Info.plist`, sustituye `REEMPLAZAR` en `com.googleusercontent.apps.REEMPLAZAR` por `NNNN-xxxx` (el ID invertido; sin `.apps.googleusercontent.com`).
4. **Supabase** → Authentication → Providers → Google: el Client ID / Secret del cliente **web** siguen siendo los de la web. En **Authorized Client IDs** añade además el ID de cliente **iOS** del paso 1 (cinturón y tirantes: con `iOSServerClientId` el token ya lleva el del web).
5. `npm run cap:sync`, `pod install` (en el Mac) y compilar. No se puede probar en el simulador sin cuenta de Google en el dispositivo/simulador.
