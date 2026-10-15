# App Android (Capacitor)

Mismo `appId` que iOS (`es.puntostudio.puntociego`), nombre «Punto Ciego», versión 1.0 (`versionCode 1`), minSdk 24, **compileSdk/targetSdk 36** (lo que Google Play exige a apps nuevas desde el 31-08-2026). Solo vertical. La web sigue sirviéndose desde la raíz: `npm run web` copia lo necesario a `www/`.

## Requisitos en el PC
Android Studio (SDK + emulador) y **JDK 21** (Capacitor 8 / Gradle 8.14 no compilan con el Java 25 que trae Android Studio). Se compila con `JAVA_HOME` apuntando al JDK 21 (PowerShell: `$env:JAVA_HOME='C:\ruta\jdk-21'`) y `android/local.properties` con `sdk.dir=C:/Users/<tú>/AppData/Local/Android/Sdk` (no va al repo).

```
npm install
npm run android:sync           # copia la web a www/ y sincroniza android/
cd android
.\gradlew.bat assembleDebug    # APK de pruebas: app/build/outputs/apk/debug/app-debug.apk
.\gradlew.bat assembleRelease  # APK firmado con la clave de subida (para instalar a mano): app/build/outputs/apk/release/
.\gradlew.bat bundleRelease    # .aab firmado para Google Play: app/build/outputs/bundle/release/app-release.aab
```
Al subir versión: `versionCode`/`versionName` en `android/app/build.gradle`.

## Firma (Play App Signing)
`app-release.aab` se firma con la **clave de subida**, que vive FUERA del repo en `%USERPROFILE%\keystores\puntociego\`: `punto-ciego-upload.jks` (alias `punto-ciego-upload`) y `keystore.properties` (ruta y contraseñas; `build.gradle` lo lee de ahí, o de `-PpcKeystoreProps=<ruta>`). `*.jks`, `*.keystore` y `keystore.properties` están en `.gitignore`. **Guarda copia del .jks y de sus contraseñas en un sitio seguro** (gestor de contraseñas): con Play App Signing Google puede restablecer la clave de subida si se pierde, pero es un trámite lento. Sin el archivo, el release sale sin firmar.

## Qué es distinto de iOS
- **Plugin `AudioSesion`** (`AudioSesionPlugin.java`): mismo nombre que el de iOS para que la web no distinga plataformas. `modo` no hace nada (Android no necesita sesión de audio), `abrirAjustes` abre los ajustes de la app y `barras` (solo Android) pinta las franjas de las barras del sistema. La web funciona aunque un plugin no exista (todo va en `try`).
- **Micro**: `RECORD_AUDIO` y `MODIFY_AUDIO_SETTINGS`. Al pulsar hablar (o soplar), el WebView de Capacitor pide el permiso; si se deniega, el walkie y el minijuego de soplar muestran el aviso con «Abrir Ajustes» (la ruta es Ajustes → Aplicaciones → Punto Ciego → Permisos → Micrófono) y el soplar sigue pudiéndose hacer tocando. En iOS el aviso es el mismo (`AudioSesion.abrirAjustes` también existe en `AudioSesion.swift`).
- **Sensores** (burbuja, agitar): el WebView de Android no pide permiso y emite `deviceorientation`/`devicemotion`; si el móvil no tiene sensor, `detectaSensor` pasa en menos de un segundo a la versión táctil, igual que en iOS.
- **Vibración**: `@capacitor/haptics` (permiso `VIBRATE`). Los efectos de sonido siguen desactivados (`SFX_ENABLED=false`).
- **Sign in with Apple**: no está en Android (el plugin es solo de iOS y el flujo web de Apple no vuelve a la app), así que `ANDROID` deja `APPLE=false`. Se entra con correo o con Google.
- **Google Sign-In nativo**: `@capgo/capacitor-social-login` usa Credential Manager. Ver «Google en Android» abajo.
- **Pantalla completa**: `MainActivity` rellena el contenido con el alto real de las barras del sistema (estado y navegación) y del teclado y consume esos insets, así que nada queda debajo de ellas, tampoco con el teclado abierto en el walkie (`adjustResize`). Las franjas las pinta la ventana con el color del fondo de la página (`AudioSesion.barras`). En `capacitor.config.json`, `SystemBars.insetsHandling = "disable"` desactiva el manejo de Capacitor.
- **Botón «atrás»** (`@capacitor/app`): cierra la hoja o el walkie abiertos; si no, hace lo mismo que «‹ Volver» de cada pantalla; en plena partida (jugando o en reunión) abre «¿Salir de la partida?» y nunca cierra la app; la app solo se cierra desde la pantalla de inicio o la de acceso.
- **Enlaces externos**: `@capacitor/browser` (Privacidad, Términos, Soporte y la ficha de la tienda).
- **Aviso de versión** (`APP_V`): en Android el botón abre la ficha de Google Play (`PLAY_STORE_URL`); en iOS, la de la App Store (`APP_STORE_URL`).
- Iconos y splash salen de `assets/icons/` con `python -I scripts/iconos-android.py`.

## Google en Android
No hay ningún ID nuevo en el código: Credential Manager usa el cliente **web** (el de Supabase, `GOOGLE_WEB_ID`) como `webClientId`, así que el ID token ya lleva ese cliente como audiencia y **Supabase no necesita ningún cambio** (Authentication → Providers → Google ya tiene ese cliente). Lo único que falta está en Google Cloud (proyecto 696175970854, el mismo del cliente web y del de iOS):

1. APIs y servicios → Credenciales → Crear credenciales → **ID de cliente de OAuth** → tipo **Android**.
2. Nombre de paquete: `es.puntostudio.puntociego`.
3. Huella SHA-1: hace falta **un cliente por cada certificado** con el que se instale la app:
   - Clave de subida (APK de `assembleRelease` instalado a mano): `C3:28:36:65:E3:AE:DB:41:B5:56:86:9C:0A:A8:81:4D:16:B6:76:6E`
   - Depuración (APK de `assembleDebug`, emulador): `B3:46:A6:0C:20:2D:1A:A5:A3:7D:D4:F7:CC:B8:3D:9B:7D:71:6A:3D`
   - **Google Play App Signing** (la que lleva la app instalada desde Play): Play Console → Punto Ciego → Integridad de la app → «Certificado de la clave de firma de la app» → copia el SHA-1 y crea otro cliente Android con él. Sin este, Google fallará (`[28444] Developer console is not set up correctly`) solo en la app descargada de Play.
4. La pantalla de consentimiento OAuth debe estar publicada (o el correo de prueba entre los usuarios de prueba).

El código del cliente Android **no se copia a ningún sitio**: Google solo comprueba paquete + firma. En un fallo, `adb logcat -s GoogleProvider` muestra el paquete y el SHA-1 con el que firmó el APK.

## Enlaces de sala (App Links)
`AndroidManifest.xml` reclama `https://puntostudio.es/punto-ciego/` (solo esa ruta, no `beta/`, `soporte.html`…) con `autoVerify`. La verificación lee `https://puntostudio.es/.well-known/assetlinks.json` (repo `javivalmich.github.io`), que lista las huellas **SHA-256**: subida y depuración ya están; **falta la de Play App Signing** (Play Console → Integridad de la app → «Certificado de la clave de firma de la app» → SHA-256; añadirla como tercera cadena de `sha256_cert_fingerprints` de `es.puntostudio.puntociego`). Sin ella, los usuarios de Play no verifican el enlace (se abre el navegador). Comprobarlo: `adb shell pm get-app-links es.puntostudio.puntociego` (debe salir `puntostudio.es: verified`). En un arranque en frío el enlace llega por `getLaunchUrl`; con la app abierta, por `appUrlOpen`.

## Pruebas
`tests/enlaces_app.py` simula el puente de Capacitor en Android (detección de plataforma, sin Apple, Google con `webClientId`, botón atrás, aviso de micro, Google Play). El emulador de este PC no arranca (sin aceleración por hardware), así que la app **no se ha probado todavía en un dispositivo real**: instala `app-debug.apk` o `app-release.apk` en un móvil y prueba walkie, soplar, atrás, teclado del walkie y Google.
