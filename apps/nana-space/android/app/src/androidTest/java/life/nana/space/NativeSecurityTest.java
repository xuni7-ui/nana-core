package life.nana.space;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.core.app.ActivityScenario;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.json.JSONObject;
import java.lang.reflect.Method;
import android.content.Context;
import static org.junit.Assert.*;

/** Owned emulator only. Fake device credential; no actual server or paid calls. */
@RunWith(AndroidJUnit4.class)
public class NativeSecurityTest {
    @Test public void keystoreEncryptionLogoutAndPackagedUi() throws Exception {
        try(ActivityScenario<MainActivity> activity=ActivityScenario.launch(MainActivity.class)) {
            Throwable[] failure={null};
            activity.onActivity(a->{
                try {
                    assertEquals("https",new java.net.URI(a.getBridge().getServerUrl()==null?"https://localhost":a.getBridge().getServerUrl()).getScheme());
                    NanaHostPlugin plugin=(NanaHostPlugin)a.getBridge().getPlugin("NanaHost").getInstance();
                    Method save=NanaHostPlugin.class.getDeclaredMethod("save",JSONObject.class);save.setAccessible(true);
                    Method read=NanaHostPlugin.class.getDeclaredMethod("binding");read.setAccessible(true);
                    Method clear=NanaHostPlugin.class.getDeclaredMethod("clearBinding");clear.setAccessible(true);
                    JSONObject b=new JSONObject();b.put("base","https://space.test");b.put("subject_id","TEST_ONLY_NOT_SECRET_subject");
                    b.put("device_id","TEST_ONLY_NOT_SECRET_device");b.put("refresh_token","TEST_ONLY_NOT_SECRET_refresh");
                    b.put("lineage_binding","a".repeat(64));save.invoke(plugin,b);
                    Context context=InstrumentationRegistry.getInstrumentation().getTargetContext();
                    String stored=context.getSharedPreferences("nana_secure_binding",Context.MODE_PRIVATE).getString("encrypted","");
                    assertFalse(stored.isEmpty());assertFalse(stored.contains("TEST_ONLY_NOT_SECRET"));
                    assertEquals("TEST_ONLY_NOT_SECRET_refresh",((JSONObject)read.invoke(plugin)).getString("refresh_token"));
                    assertNotNull(java.security.KeyStore.getInstance("AndroidKeyStore"));
                    clear.invoke(plugin);
                    assertFalse(context.getSharedPreferences("nana_secure_binding",Context.MODE_PRIVATE).contains("encrypted"));
                    assertFalse(a.getBridge().getWebView().getSettings().getAllowUniversalAccessFromFileURLs());
                } catch(Throwable e){failure[0]=e;}
            });
            if(failure[0]!=null)throw new AssertionError(failure[0]);
        }
    }
}
