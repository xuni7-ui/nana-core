package life.nana.space;

import android.Manifest;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.SystemClock;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import androidx.core.app.NotificationCompat;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.net.ssl.HttpsURLConnection;
import org.json.JSONObject;

/** Packaged-UI-only HTTPS bridge. Never returns device/session secrets to JS.
 * One fixed operation map; no arbitrary URL, header, shell, file or Core handle.
 * TLS uses Android's standard CA/hostname checks, no redirects or blind retry.
 */
@CapacitorPlugin(name = "NanaHost", permissions = {
    @Permission(alias = "notifications", strings = { Manifest.permission.POST_NOTIFICATIONS })
})
public class NanaHostPlugin extends Plugin {
    private static final String ALIAS = "nana.space.session.aes.v1";
    private static final String CONTRACT = "nana-space-live/v2";
    private static final String PREFIX = "/api/nana-space/v2/";
    private static final Set<String> PAGES = new HashSet<>(Arrays.asList(
        "home", "chat", "memories", "goals", "journal", "world", "growth", "devices", "runtime", "settings"));
    private String access = null;
    private long accessAt = 0;

    private SharedPreferences prefs() {
        return getContext().getSharedPreferences("nana_secure_binding", Context.MODE_PRIVATE);
    }
    private SecretKey key() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if (!store.containsAlias(ALIAS)) {
            KeyGenerator gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            gen.init(new KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).setRandomizedEncryptionRequired(true).build());
            gen.generateKey();
        }
        return (SecretKey)store.getKey(ALIAS, null);
    }
    private synchronized void save(JSONObject value) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key());
        byte[] ciphertext = cipher.doFinal(value.toString().getBytes(StandardCharsets.UTF_8));
        byte[] combined = new byte[cipher.getIV().length + ciphertext.length];
        System.arraycopy(cipher.getIV(), 0, combined, 0, cipher.getIV().length);
        System.arraycopy(ciphertext, 0, combined, cipher.getIV().length, ciphertext.length);
        if (!prefs().edit().putString("encrypted", Base64.encodeToString(combined, Base64.NO_WRAP)).commit())
            throw new Exception("SECURE_BINDING_WRITE_FAILED");
    }
    private synchronized JSONObject binding() throws Exception {
        String encrypted = prefs().getString("encrypted", null);
        if (encrypted == null) throw new Exception("PAIRING_REQUIRED");
        try {
            byte[] value = Base64.decode(encrypted, Base64.NO_WRAP);
            if (value.length < 29) throw new Exception("CORRUPT_BINDING");
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, Arrays.copyOfRange(value, 0, 12)));
            return new JSONObject(new String(cipher.doFinal(Arrays.copyOfRange(value, 12, value.length)), StandardCharsets.UTF_8));
        } catch (Exception ex) {
            clearBinding(); throw new Exception("PAIRING_REQUIRED");
        }
    }
    // Security transition must complete before acknowledging logout.
    @android.annotation.SuppressLint("ApplySharedPref")
    private synchronized void clearBinding() {
        access = null; accessAt = 0;
        prefs().edit().clear().commit();
    }
    static String origin(String value) throws Exception {
        if (value == null || value.length() > 256 || value.contains("\\") || value.contains("\n") || value.contains("\r"))
            throw new Exception("HTTPS_ORIGIN_REQUIRED");
        URI uri = new URI(value);
        if (!"https".equals(uri.getScheme()) || uri.getHost() == null || uri.getRawUserInfo() != null || uri.getRawQuery() != null
            || uri.getRawFragment() != null || !(uri.getPath().isEmpty() || "/".equals(uri.getPath()))
            || uri.getPort() == 0 || uri.getPort() > 65535)
            throw new Exception("HTTPS_ORIGIN_REQUIRED");
        return "https://" + uri.getRawAuthority().toLowerCase(java.util.Locale.ROOT);
    }
    private JSONObject http(String base, String path, String method, JSONObject body, String token) throws Exception {
        HttpsURLConnection connection = (HttpsURLConnection)new URL(origin(base) + PREFIX + path).openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(10000); connection.setReadTimeout(15000);
        connection.setRequestMethod(method); connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("Cache-Control", "no-store");
        if (token != null) connection.setRequestProperty("Authorization", "Bearer " + token);
        try {
            if (body != null) {
                byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
                if (bytes.length > 32768) throw new Exception("REQUEST_BOUND");
                connection.setDoOutput(true); connection.setFixedLengthStreamingMode(bytes.length);
                connection.setRequestProperty("Content-Type", "application/json");
                try (java.io.OutputStream out = connection.getOutputStream()) { out.write(bytes); }
            }
            int status = connection.getResponseCode();
            if (status >= 300 && status < 400) throw new Exception("REDIRECT_DENIED");
            InputStream input = status < 400 ? connection.getInputStream() : connection.getErrorStream();
            if (input == null) throw new Exception("RESPONSE_UNKNOWN");
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (InputStream in = input) {
                byte[] chunk = new byte[8192]; int count;
                while ((count = in.read(chunk)) != -1) {
                    if (bytes.size() + count > 524288) throw new Exception("RESPONSE_BOUND");
                    bytes.write(chunk, 0, count);
                }
            }
            JSONObject result = new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));
            if (!CONTRACT.equals(result.optString("contract"))) throw new Exception("CONTRACT_MISMATCH");
            if (status >= 400) {
                String code = result.optString("code", "REQUEST_REJECTED");
                if (!code.matches("[A-Z_]{1,96}")) code = "REQUEST_REJECTED";
                if (status == 401) access = null;
                throw new Exception(code);
            }
            return result;
        } finally { connection.disconnect(); }
    }
    private synchronized String session(JSONObject b) throws Exception {
        if (access != null && SystemClock.elapsedRealtime() - accessAt < 500000) return access;
        JSONObject body = new JSONObject();
        body.put("device_id", b.getString("device_id")); body.put("refresh_token", b.getString("refresh_token"));
        body.put("subject_id", b.getString("subject_id"));
        try {
            JSONObject r = http(b.getString("base"), "session/native", "POST", body, null);
            access = r.getString("access_token"); accessAt = SystemClock.elapsedRealtime();
            return access;
        } catch (Exception ex) {
            if ("SESSION_DENIED".equals(ex.getMessage())) clearBinding();
            throw ex;
        }
    }
    private void reject(PluginCall call, Exception ex) {
        String code = ex.getMessage();
        call.reject(code != null && code.matches("[A-Z_]{1,96}") ? code : "NETWORK_OR_EXECUTION_UNKNOWN");
    }
    @PluginMethod public void status(PluginCall call) {
        getBridge().execute(() -> {
            try {
                JSONObject b = binding();
                JSObject out = new JSObject();out.put("paired", true);out.put("base", b.getString("base"));
                out.put("subject_id", b.getString("subject_id"));out.put("lineage_binding", b.getString("lineage_binding"));
                out.put("background_push", "NOT_QUALIFIED");call.resolve(out);
            } catch (Exception ex) { JSObject out = new JSObject();out.put("paired", false);call.resolve(out); }
        });
    }
    @PluginMethod public void pair(PluginCall call) {
        getBridge().execute(() -> {
            try {
                String base = origin(call.getString("base"));
                String subject = call.getString("subject_id");String code = call.getString("code");
                String name = call.getString("device_name");
                if (subject == null || subject.length() > 96 || code == null || code.length() < 24 || code.length() > 128
                    || name == null || name.isEmpty() || name.length() > 64) throw new Exception("PAIRING_INPUT_INVALID");
                clearBinding();
                JSONObject request = new JSONObject();request.put("subject_id", subject);request.put("code", code);request.put("device_name", name);
                JSONObject reply = http(base, "device/pairing", "POST", request, null);
                if (!subject.equals(reply.getString("subject_id"))) throw new Exception("INVALID_IDENTITY");
                reply.put("base", base);reply.remove("contract");save(reply);
                JSONObject b = binding();
                JSONObject current = http(base, "bootstrap", "GET", null, session(b));
                validateIdentity(current, b);call.resolve(JSObject.fromJSONObject(current));
            } catch (Exception ex) { clearBinding();reject(call, ex); }
        });
    }
    private void validateIdentity(JSONObject reply, JSONObject b) throws Exception {
        if (!b.getString("subject_id").equals(reply.optString("subject_id"))
            || !b.getString("lineage_binding").equals(reply.optString("lineage_binding"))) {
            clearBinding();throw new Exception("INVALID_IDENTITY");
        }
    }
    @PluginMethod public void call(PluginCall call) {
        getBridge().execute(() -> {
            try {
                JSONObject b = binding();String op = call.getString("operation");String route;String method = "GET";
                JSObject data = call.getObject("data", new JSObject());
                if ("bootstrap".equals(op)) route = "bootstrap";
                else if ("view".equals(op) && PAGES.contains(data.optString("page"))) route = "views/" + data.getString("page");
                else if ("events".equals(op)) {
                    String cursor = data.optString("cursor", "");
                    if (!cursor.isEmpty() && !cursor.matches("[a-f0-9]{32}\\.[0-9]{1,20}")) throw new Exception("CURSOR_INVALID");
                    route = "events" + (cursor.isEmpty() ? "" : "?cursor=" + cursor);
                } else if ("receipt".equals(op) && data.optString("id").matches("[A-Za-z0-9._:-]{1,96}")) route = "receipts/" + data.getString("id");
                else if ("devices".equals(op)) route = "devices";
                else if ("notifications".equals(op)) route = "notifications";
                else if ("providers".equals(op)) route = "providers/status";
                else if ("host.status".equals(op)) route = "host/operations";
                else if ("message".equals(op)) { route = "messages";method = "POST"; }
                else if ("command".equals(op)) { route = "commands";method = "POST"; }
                else if ("host.confirm".equals(op)) { route = "host/confirmations";method = "POST"; }
                else if ("host.operation".equals(op)) { route = "host/operations";method = "POST"; }
                else if ("pair.offer".equals(op)) { route = "devices/offers";method = "POST"; }
                else if ("device.revoke".equals(op) && data.optString("device_id").matches("[a-f0-9]{32}")) { route = "devices/" + data.getString("device_id");method = "DELETE"; }
                else throw new Exception("NATIVE_OPERATION_DENIED");
                JSONObject reply = http(b.getString("base"), route, method, "POST".equals(method) ? data : null, session(b));
                validateIdentity(reply, b);call.resolve(JSObject.fromJSONObject(reply));
            } catch (Exception ex) { reject(call, ex); }
        });
    }
    @PluginMethod public void logout(PluginCall call) {
        getBridge().execute(() -> {
            String revoked = "UNKNOWN";
            try {
                JSONObject b = binding();
                http(b.getString("base"), "session", "DELETE", null, session(b));
                revoked = "VERIFIED";
            } catch (Exception ignored) {
                // No retry; clear local binding even offline. Remote revocation
                // can be completed by an independently authenticated controller.
            } finally { clearBinding(); }
            JSObject out = new JSObject();out.put("cleared", true);out.put("server_revocation", revoked);call.resolve(out);
        });
    }
    @PluginMethod public void notificationPermission(PluginCall call) {
        if (Build.VERSION.SDK_INT < 33 || getPermissionState("notifications") == PermissionState.GRANTED) {
            JSObject out = new JSObject();out.put("granted", true);out.put("background_push", "NOT_QUALIFIED");call.resolve(out);
        } else requestPermissionForAlias("notifications", call, "permissionResult");
    }
    @PermissionCallback private void permissionResult(PluginCall call) {
        JSObject out = new JSObject();out.put("granted", getPermissionState("notifications") == PermissionState.GRANTED);
        out.put("background_push", "NOT_QUALIFIED");call.resolve(out);
    }
    @PluginMethod public void notifyForeground(PluginCall call) {
        try {
            if (Build.VERSION.SDK_INT >= 33 && getPermissionState("notifications") != PermissionState.GRANTED) throw new Exception("NOTIFICATION_PERMISSION_REQUIRED");
            String event = call.getString("event_id");String page = call.getString("page", "chat");
            if (event == null || !event.matches("[A-Za-z0-9._:-]{1,96}") || !PAGES.contains(page)) throw new Exception("NOTIFICATION_INPUT_DENIED");
            SharedPreferences seen = getContext().getSharedPreferences("nana_notification_metadata", Context.MODE_PRIVATE);
            if (event.equals(seen.getString("last_event", ""))) {call.resolve();return;}
            NotificationManager manager = (NotificationManager)getContext().getSystemService(Context.NOTIFICATION_SERVICE);
            if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(new NotificationChannel("nana_presence", "奈奈的动态", NotificationManager.IMPORTANCE_DEFAULT));
            Intent intent = new Intent(getContext(), MainActivity.class);intent.putExtra("nana_page", page);
            intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent pending = PendingIntent.getActivity(getContext(), 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            manager.notify(1, new NotificationCompat.Builder(getContext(), "nana_presence")
                .setSmallIcon(R.drawable.nana_notification).setContentTitle("奈奈 · 新动态")
                .setContentText("打开查看有来源的最新状态。").setContentIntent(pending).setAutoCancel(true).build());
            seen.edit().putString("last_event", event).apply();call.resolve();
        } catch (Exception ex) {reject(call, ex);}
    }
    @PluginMethod public void launchRoute(PluginCall call) {
        String page = getActivity().getIntent().getStringExtra("nana_page");
        JSObject out = new JSObject();out.put("page", PAGES.contains(page) ? page : "home");call.resolve(out);
    }
}
