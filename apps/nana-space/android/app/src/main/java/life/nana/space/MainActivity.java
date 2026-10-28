package life.nana.space;

import android.os.Bundle;
import android.content.Intent;
import com.getcapacitor.BridgeActivity;
import androidx.activity.OnBackPressedCallback;

public class MainActivity extends BridgeActivity {
    @Override public void onCreate(Bundle savedInstanceState) {
        registerPlugin(NanaHostPlugin.class);
        registerPlugin(NanaSpeechPlugin.class);
        super.onCreate(savedInstanceState);
        getWindow().setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        if (bridge != null) {
            bridge.getWebView().getSettings().setCacheMode(android.webkit.WebSettings.LOAD_NO_CACHE);
            bridge.getWebView().clearCache(true);
        }
        // Packaged UI route history only; does not expose any new native operation.
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override public void handleOnBackPressed() {
                if (bridge == null) { finish(); return; }
                bridge.getWebView().evaluateJavascript(
                    "Boolean(document.querySelector('.v3-sidebar.open'))", result -> {
                        if ("true".equals(result)) {
                            bridge.getWebView().evaluateJavascript(
                                "window.dispatchEvent(new Event('nana-android-back'))", null);
                        } else if (bridge.getWebView().canGoBack()) {
                            bridge.getWebView().goBack();
                        } else {
                            finish();
                        }
                    });
            }
        });
    }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);setIntent(intent);
        if (bridge != null) bridge.getWebView().evaluateJavascript("window.dispatchEvent(new Event('nana-native-route'))", null);
    }
}
