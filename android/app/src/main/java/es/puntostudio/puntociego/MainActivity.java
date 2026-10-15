package es.puntostudio.puntociego;

import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;

import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;

import com.getcapacitor.BridgeActivity;

/* Pantalla completa con márgenes REALES desde el lado nativo, sin depender de que el WebView entienda env(safe-area-inset-*) (los WebView antiguos no).
   El contenido de la ventana se rellena con el alto de las barras del sistema (estado y navegación, con gestos o con tres botones) y del teclado, y esos
   insets se consumen: el WebView solo ve el área libre, así que nada puede quedar debajo de las barras ni del teclado. Las franjas de las barras las pinta
   la ventana (ver AudioSesionPlugin.barras) con el color de la página. En capacitor.config.json, SystemBars.insetsHandling = "disable" desactiva el manejo de Capacitor. */
public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AudioSesionPlugin.class);
        super.onCreate(savedInstanceState);

        Window w = getWindow();
        WindowCompat.setDecorFitsSystemWindows(w, false);
        // barras transparentes y sin el velo de contraste: se ve el color que pinta la ventana debajo
        w.setNavigationBarColor(Color.TRANSPARENT);
        w.setStatusBarColor(Color.TRANSPARENT);
        if (Build.VERSION.SDK_INT >= 29) {
            w.setNavigationBarContrastEnforced(false);
            w.setStatusBarContrastEnforced(false);
        }

        View contenido = findViewById(android.R.id.content);
        ViewCompat.setOnApplyWindowInsetsListener(contenido, (v, insets) -> {
            int barras = WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout();
            Insets b = insets.getInsets(barras);
            Insets ime = insets.getInsets(WindowInsetsCompat.Type.ime());
            // el inset del teclado ya incluye la barra de navegación: abajo vale el mayor de los dos
            v.setPadding(b.left, b.top, b.right, Math.max(b.bottom, ime.bottom));
            return new WindowInsetsCompat.Builder(insets).setInsets(barras | WindowInsetsCompat.Type.ime(), Insets.NONE).build();
        });
        ViewCompat.requestApplyInsets(contenido);
    }
}
