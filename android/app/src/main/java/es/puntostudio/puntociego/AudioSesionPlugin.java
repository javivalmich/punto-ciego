package es.puntostudio.puntociego;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.LayerDrawable;
import android.net.Uri;
import android.provider.Settings;
import android.view.Gravity;
import android.view.Window;

import androidx.core.graphics.ColorUtils;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/* Mismo nombre que el plugin local de iOS (AudioSesion.swift) para que la web no distinga plataformas.
   En Android la sesión de audio no hace falta: `modo` no hace nada y `abrirAjustes` abre los ajustes de la app (micrófono denegado). */
@CapacitorPlugin(name = "AudioSesion")
public class AudioSesionPlugin extends Plugin {

    @PluginMethod
    public void modo(PluginCall call) {
        JSObject r = new JSObject();
        r.put("modo", call.getString("modo", "ambient"));
        call.resolve(r);
    }

    @PluginMethod
    public void abrirAjustes(PluginCall call) {
        try {
            Intent i = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", getContext().getPackageName(), null));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(i);
            call.resolve();
        } catch (Exception e) {
            call.reject("No se pudieron abrir los ajustes", e);
        }
    }

    /* Solo Android: color de las franjas de las barras del sistema (la ventana las pinta debajo del WebView, ver MainActivity).
       `arriba` = barra de estado, `abajo` = barra de navegación (#rrggbb). Los iconos de las barras se oscurecen o aclaran según el color. */
    @PluginMethod
    public void barras(PluginCall call) {
        final Activity act = getActivity();
        final String arriba = call.getString("arriba", "#0b0b0d"), abajo = call.getString("abajo", "#0b0b0d");
        act.runOnUiThread(() -> {
            try {
                int ca = Color.parseColor(arriba), cb = Color.parseColor(abajo);
                Window w = act.getWindow();
                LayerDrawable ld = new LayerDrawable(new Drawable[] { new ColorDrawable(cb), new ColorDrawable(ca) });
                ld.setLayerGravity(1, Gravity.TOP);
                ld.setLayerHeight(1, act.getResources().getDisplayMetrics().heightPixels / 2); // lo que tape el WebView no se ve
                w.getDecorView().setBackground(ld);
                WindowInsetsControllerCompat c = WindowCompat.getInsetsController(w, w.getDecorView());
                c.setAppearanceLightStatusBars(ColorUtils.calculateLuminance(ca) > 0.5);
                c.setAppearanceLightNavigationBars(ColorUtils.calculateLuminance(cb) > 0.5);
                call.resolve();
            } catch (Exception e) {
                call.reject("Color no válido", e);
            }
        });
    }
}
