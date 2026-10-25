package life.nana.space;

import android.os.Bundle;
import android.content.Intent;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override public void onCreate(Bundle savedInstanceState) {
        registerPlugin(NanaHostPlugin.class);
        super.onCreate(savedInstanceState);
        getWindow().setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        if (bridge != null) {
            bridge.getWebView().getSettings().setCacheMode(android.webkit.WebSettings.LOAD_NO_CACHE);
            bridge.getWebView().clearCache(true);
        }
    }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);setIntent(intent);
        if (bridge != null) bridge.getWebView().evaluateJavascript("window.dispatchEvent(new Event('nana-native-route'))", null);
    }
}
