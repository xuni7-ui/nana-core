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
    private static final int MESSAGE_TIMEOUT_MS = 4 * 600000 + 30000;
    private static final int SEQUENCE_TIMEOUT_MS = 2 * 4 * 600000 + 30000;
    private static final Set<String> PAGES = new HashSet<>(Arrays.asList(
        "home", "chat", "memories", "goals", "journal", "world", "growth", "devices", "runtime", "settings"));
    private final java.util.concurrent.atomic.AtomicBoolean streamingActive = new java.util.concurrent.atomic.AtomicBoolean(false);
    private volatile HttpsURLConnection liveMessageConnection = null;
    private String accessBinding = null;
    private String access = null;
    private long accessAt = 0;
    private android.app.AlertDialog credentialDialog = null;

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
        access=null;accessAt=0;accessBinding=null;
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
        try { NanaNotificationJob.configure(getContext(), false); } catch (Exception ignored) { }
        access = null; accessAt = 0; accessBinding=null;
        HttpsURLConnection active=liveMessageConnection;if(active!=null)active.disconnect();
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
        connection.setConnectTimeout(10000);
        // Independent max600s phases: single queue2 + own2, finite sequence2*4.
        connection.setReadTimeout("messages/sequence".equals(path) ? SEQUENCE_TIMEOUT_MS : "messages".equals(path) ? MESSAGE_TIMEOUT_MS : 15000);
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
                finally { Arrays.fill(bytes, (byte)0); }
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
    static String sessionBinding(String base,String device,String subject,String lineage) throws Exception {
        if(device==null || !device.matches("[a-f0-9]{32}") || subject==null || subject.length()>96
            || lineage==null || !lineage.matches("[a-f0-9]{64}"))throw new Exception("INVALID_IDENTITY");
        return origin(base)+"|"+device+"|"+subject.length()+":"+subject+"|"+lineage;
    }
    private String sessionBinding(JSONObject b) throws Exception {
        return sessionBinding(b.getString("base"),b.getString("device_id"),b.getString("subject_id"),b.getString("lineage_binding"));
    }
    private synchronized String session(JSONObject b) throws Exception {
        String target=sessionBinding(b);
        if(!target.equals(sessionBinding(binding())))throw new Exception("SESSION_REVOKED");
        if (access != null && target.equals(accessBinding) && SystemClock.elapsedRealtime() - accessAt < 500000) return access;
        JSONObject body = new JSONObject();
        body.put("device_id", b.getString("device_id")); body.put("refresh_token", b.getString("refresh_token"));
        body.put("subject_id", b.getString("subject_id"));
        try {
            JSONObject r = http(b.getString("base"), "session/native", "POST", body, null);
            access = r.getString("access_token"); accessAt = SystemClock.elapsedRealtime();accessBinding=target;
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
    @PluginMethod public void login(PluginCall call) {
        final String base, name;
        try {
            base = origin(call.getString("base")); name = call.getString("device_name");
            if (name == null || name.trim().isEmpty() || name.length() > 64) throw new Exception("PAIRING_INPUT_INVALID");
        } catch (Exception ex) { reject(call, ex); return; }
        getActivity().runOnUiThread(() -> {
            if (getActivity().isFinishing() || getActivity().isDestroyed()) { call.reject("SECRET_INPUT_CANCELLED"); return; }
            if (credentialDialog != null && credentialDialog.isShowing()) { call.reject("SECRET_INPUT_ALREADY_OPEN"); return; }
            android.widget.EditText input = new android.widget.EditText(getContext());
            input.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
            input.setSaveEnabled(false); input.setSingleLine(true);
            input.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(128)});
            input.setImeOptions(android.view.inputmethod.EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING);
            if (Build.VERSION.SDK_INT >= 26) input.setImportantForAutofill(android.view.View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
            android.app.AlertDialog dialog = new android.app.AlertDialog.Builder(getActivity())
                .setTitle("登录 Nana Space")
                .setMessage("服务器：" + base + "\n输入服务器登录口令。手机仅保存加密设备凭据；口令不会进入网页或被保存。")
                .setView(input)
                .setNegativeButton("取消", (d,w) -> { input.setText(""); call.reject("SECRET_INPUT_CANCELLED"); })
                .setPositiveButton("登录并连接", (d,w) -> {
                    final String password = input.getText().toString(); input.setText("");
                    getBridge().execute(() -> {
                        JSONObject body = new JSONObject();
                        try {
                            if (password.length() < 12) throw new Exception("SESSION_DENIED");
                            body.put("password", password); body.put("device_name", name.trim());
                            JSONObject reply = http(base, "device/login", "POST", body, null);
                            String realm = reply.getString("realm");
                            if (!("OWNED_DEVELOPMENT_ONLY".equals(realm) || "PRODUCTION_SINGLE_SUBJECT".equals(realm))
                                || !reply.getString("lineage_binding").matches("[a-f0-9]{64}") || reply.getString("subject_id").isEmpty())
                                throw new Exception("INVALID_IDENTITY");
                            JSONObject stored = new JSONObject();
                            for (String k : new String[]{"device_id","refresh_token","subject_id","lineage_binding","realm"}) stored.put(k, reply.getString(k));
                            stored.put("base", base); save(stored); access = null;
                            JSONObject current = http(base, "bootstrap", "GET", null, session(stored));
                            validateIdentity(current, stored); call.resolve(JSObject.fromJSONObject(current));
                        } catch (Exception ex) { reject(call, ex); }
                        finally { body.remove("password"); }
                    });
                }).create();
            dialog.setOnCancelListener(d -> { input.setText(""); call.reject("SECRET_INPUT_CANCELLED"); });
            dialog.setOnDismissListener(d -> { input.setText(""); if (credentialDialog == dialog) credentialDialog = null; });
            dialog.getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
            credentialDialog = dialog; dialog.show();
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
                String realm=reply.getString("realm");
                if (!"OWNED_DEVELOPMENT_ONLY".equals(realm) && !"PRODUCTION_SINGLE_SUBJECT".equals(realm)) throw new Exception("INVALID_IDENTITY");
                JSONObject stored=new JSONObject();
                for(String k:new String[]{"device_id","refresh_token","subject_id","lineage_binding","realm"}) stored.put(k,reply.getString(k));
                stored.put("base",base);save(stored);
                JSONObject b = binding();
                JSONObject current = http(base, "bootstrap", "GET", null, session(b));
                validateIdentity(current, b);call.resolve(JSObject.fromJSONObject(current));
            } catch (Exception ex) { clearBinding();reject(call, ex); }
        });
    }
    private void validateIdentity(JSONObject reply, JSONObject b) throws Exception {
        if (!b.getString("subject_id").equals(reply.optString("subject_id"))
            || !b.getString("lineage_binding").equals(reply.optString("lineage_binding"))
            || !b.getString("realm").equals(reply.optString("realm"))) {
            clearBinding();throw new Exception("INVALID_IDENTITY");
        }
    }
    private JSONObject httpMessageStream(JSONObject bound, JSONObject body, String token) throws Exception {
        HttpsURLConnection connection = (HttpsURLConnection)new URL(origin(bound.getString("base")) + PREFIX + "messages/stream").openConnection();
        long started=SystemClock.elapsedRealtime();
        liveMessageConnection=connection;
        connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(10000);connection.setReadTimeout(MESSAGE_TIMEOUT_MS);
        connection.setRequestMethod("POST");connection.setRequestProperty("Accept", "application/x-ndjson");
        connection.setRequestProperty("Cache-Control", "no-store");connection.setRequestProperty("Authorization", "Bearer " + token);
        connection.setRequestProperty("Content-Type", "application/json");
        try {
            byte[] request=body.toString().getBytes(StandardCharsets.UTF_8);
            if(request.length>32768)throw new Exception("REQUEST_BOUND");
            connection.setDoOutput(true);connection.setFixedLengthStreamingMode(request.length);
            try(java.io.OutputStream out=connection.getOutputStream()){out.write(request);}
            finally{Arrays.fill(request,(byte)0);}
            int status=connection.getResponseCode();
            if(status>=300 && status<400)throw new Exception("REDIRECT_DENIED");
            if(status>=400)throw new Exception("STREAM_INTERRUPTED_VERIFY_ONLY");
            String contentType=connection.getContentType();
            if(contentType==null || !contentType.startsWith("application/x-ndjson"))throw new Exception("INVALID_STREAM");
            int total=0,frames=0;
            ByteArrayOutputStream line=new ByteArrayOutputStream();
            try(InputStream input=connection.getInputStream()){
                byte[] buffer=new byte[4096];int count;
                while((count=input.read(buffer))!=-1){
                    total+=count;
                    if(total>8388608 || SystemClock.elapsedRealtime()-started>MESSAGE_TIMEOUT_MS)throw new Exception("STREAM_RESPONSE_BOUND");
                    for(int i=0;i<count;i++){
                        if(buffer[i]=='\n'){
                            if(++frames>1024)throw new Exception("STREAM_FRAME_BOUND");
                            String raw=StandardCharsets.UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
                                .decode(java.nio.ByteBuffer.wrap(line.toByteArray())).toString();line.reset();
                            JSONObject frame=new JSONObject(raw);
                            if("error".equals(frame.optString("event")))throw new Exception("STREAM_INTERRUPTED_VERIFY_ONLY");
                            if(!body.getString("client_request_id").equals(frame.optString("message_id")))throw new Exception("INVALID_STREAM");
                            JSONObject current=binding();
                            if(!current.getString("base").equals(bound.getString("base"))
                                || !current.getString("device_id").equals(bound.getString("device_id")))throw new Exception("SESSION_REVOKED");
                            JSONObject envelope=frame.getJSONObject("data");validateIdentity(envelope,bound);
                            if("receipt".equals(frame.optString("event")))return envelope;
                            if(!"progress".equals(frame.optString("event")))throw new Exception("INVALID_STREAM");
                            notifyListeners("nanaChatProgress",JSObject.fromJSONObject(frame));
                        }else{
                            if(line.size()>=262144)throw new Exception("STREAM_FRAME_BOUND");
                            line.write(buffer[i]);
                        }
                    }
                }
            }
            throw new Exception("STREAM_INTERRUPTED_VERIFY_ONLY");
        } finally {connection.disconnect();if(liveMessageConnection==connection)liveMessageConnection=null;}
    }
    private void messageStream(PluginCall call) {
        if(!streamingActive.compareAndSet(false,true)){call.reject("STREAM_BUSY");return;}
        Thread worker=new Thread(() -> {
            try {
                JSONObject b=binding();JSONObject data=new JSONObject(call.getObject("data",new JSObject()).toString());
                JSONObject reply=httpMessageStream(b,data,session(b));validateIdentity(reply,b);
                call.resolve(JSObject.fromJSONObject(reply));
            } catch(Exception ex){reject(call,ex);}
            finally {streamingActive.set(false);}
        },"nana-chat-https");
        worker.setDaemon(true);worker.start();
    }
    @PluginMethod public void call(PluginCall call) {
        if("message.stream".equals(call.getString("operation"))){messageStream(call);return;}
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
                else if ("backup.status".equals(op)) route = "backup/status";
                else if ("conversation.history".equals(op)) route = "conversation/history";
                else if ("bilibili.history".equals(op)) route = "platform/bilibili";
                else if ("platform.status".equals(op)) route = "platform/status";
                else if ("platform.command".equals(op)) { route = "platform/commands";method = "POST"; }
                else if ("platform.credential.revoke".equals(op) && "REVOKE".equals(data.optString("action"))) { route = "platform/credential";method = "POST"; }
                else if ("life.shares".equals(op)) route = "life/shares";
                else if ("providers.credentials".equals(op)) route = "providers/credentials";
                else if ("providers.runtime.status".equals(op)) route = "providers/runtime";
                else if ("providers.runtime".equals(op)) { route = "providers/runtime";method = "POST"; }
                else if ("providers.models".equals(op)) {
                    String pid = data.optString("provider_profile_id");
                    int revision = data.optInt("profile_revision", -1);
                    if (!pid.matches("[a-z][a-z0-9_-]{0,31}\\.[a-z][a-z0-9._-]{0,95}") || revision < 1 || revision > 999999999)
                        throw new Exception("PROVIDER_CATALOG_QUERY_REQUIRED");
                    route = "providers/models?provider_profile_id=" + pid + "&profile_revision=" + revision;
                }
                else if ("providers.credential.revoke".equals(op) && "REVOKE".equals(data.optString("action"))) { route = "providers/credential";method = "POST"; }
                else if ("providers.command".equals(op)) { route = "providers/commands";method = "POST"; }
                else if ("memories.search".equals(op)) { route = "memories/search";method = "POST"; }
                else if ("memories.note".equals(op)) { route = "memories/notes";method = "POST"; }
                else if ("conversation.feedback".equals(op)) { route = "conversation/feedback";method = "POST"; }
                else if ("host.status".equals(op)) route = "host/operations";
                else if ("message".equals(op)) { route = "messages";method = "POST"; }
                else if ("message.sequence".equals(op)) { route = "messages/sequence";method = "POST"; }
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
    @PluginMethod public void bindProviderCredential(PluginCall call) {
        // JS supplies only public profile/revision metadata. The value is typed
        // into a native secure dialog and is never returned to the WebView.
        JSObject metadata = call.getObject("data", new JSObject());
        if (!metadata.optString("provider_profile_id").matches("[a-z][a-z0-9_-]{0,31}\\.[a-z][a-z0-9._-]{0,95}")) {
            call.reject("INVALID_PROVIDER_PROFILE"); return;
        }
        bindHostCredential(call, metadata, "providers/credential", "安全绑定模型凭据");
    }
    @PluginMethod public void bindPlatformCredential(PluginCall call) {
        JSObject metadata = call.getObject("data", new JSObject());
        String platform = metadata.optString("platform"), slot = metadata.optString("slot");
        if (!metadata.optString("channel_id").matches("[a-z][a-z0-9._-]{0,63}")
            || !("qq".equals(platform) && "AUTH".equals(slot)
                || "bilibili".equals(platform) && ("COOKIE".equals(slot) || "CSRF".equals(slot)))) {
            call.reject("INVALID_PLATFORM_BINDING"); return;
        }
        bindHostCredential(call, metadata, "platform/credential", "安全绑定平台凭据");
    }
    private void bindHostCredential(PluginCall call, JSObject metadata, String route, String title) {
        getActivity().runOnUiThread(() -> {
            if (getActivity().isFinishing() || getActivity().isDestroyed()) {
                call.reject("SECRET_INPUT_CANCELLED"); return;
            }
            if (credentialDialog != null && credentialDialog.isShowing()) {
                call.reject("SECRET_INPUT_ALREADY_OPEN"); return;
            }
            android.widget.EditText input = new android.widget.EditText(getContext());
            input.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
            input.setSaveEnabled(false);
            input.setSingleLine(true);
            input.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(4096)});
            input.setImeOptions(android.view.inputmethod.EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING);
            if (Build.VERSION.SDK_INT >= 26) input.setImportantForAutofill(android.view.View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
            android.app.AlertDialog dialog = new android.app.AlertDialog.Builder(getActivity())
                .setTitle(title)
                .setMessage(Boolean.TRUE.equals(call.getBoolean("persistent", false))
                    ? "仅通过已配对 HTTPS 发往宿主加密保险库。网页不会接触密钥，手机不保存此值；服务重启可按宿主策略恢复。此操作不授予付费额度。"
                    : "仅通过已配对的 HTTPS 发往服务器内存。不保存在手机、网页或数据库；服务器重启后需重新绑定。此操作不授予付费额度。")
                .setView(input)
                .setNegativeButton("取消", (d, w) -> { input.setText(""); call.reject("SECRET_INPUT_CANCELLED"); })
                .setPositiveButton("安全绑定", (d, w) -> {
                    final String value = input.getText().toString(); input.setText("");
                    getBridge().execute(() -> {
                        JSONObject body = null;
                        try {
                            JSONObject b = binding();
                            body = new JSONObject(metadata.toString()); body.put("credential", value);
                            JSONObject reply = http(b.getString("base"), route, "POST", body, session(b));
                            validateIdentity(reply, b);
                            call.resolve(JSObject.fromJSONObject(reply));
                        } catch (Exception ex) { reject(call, ex); }
                        finally { if (body != null) body.remove("credential"); }
                    });
                }).create();
            dialog.setOnCancelListener(d -> { input.setText(""); call.reject("SECRET_INPUT_CANCELLED"); });
            dialog.setOnDismissListener(d -> { input.setText(""); if (credentialDialog == dialog) credentialDialog = null; });
            dialog.getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
            credentialDialog = dialog;
            dialog.show();
        });
    }
    @Override protected void handleOnPause() {
        if (credentialDialog != null && credentialDialog.isShowing()) credentialDialog.cancel();
    }
    @Override protected void handleOnDestroy() {
        if (credentialDialog != null && credentialDialog.isShowing()) credentialDialog.cancel();
        credentialDialog = null; access = null; accessAt = 0;accessBinding=null;
        HttpsURLConnection active=liveMessageConnection;if(active!=null)active.disconnect();
    }
    @PluginMethod public void notificationPermission(PluginCall call) {
        if (Build.VERSION.SDK_INT < 33 || getPermissionState("notifications") == PermissionState.GRANTED) {
            JSObject out = new JSObject();out.put("granted", true);out.put("background_push", "NOT_QUALIFIED");call.resolve(out);
        } else requestPermissionForAlias("notifications", call, "permissionResult");
    }
    @PluginMethod public void backgroundNotifications(PluginCall call) {
        try {
            Boolean enabled = call.getBoolean("enabled");
            if (enabled != null) NanaNotificationJob.configure(getContext(), enabled);
            call.resolve(JSObject.fromJSONObject(NanaNotificationJob.status(getContext())));
        } catch (Exception ex) { reject(call, ex); }
    }
    @PluginMethod public void notificationQuiet(PluginCall call) {
        Boolean quiet = call.getBoolean("quiet");
        if (quiet == null) { call.reject("NOTIFICATION_INPUT_DENIED"); return; }
        synchronized (NanaNotificationJob.LOCK) {
            NanaNotificationJob.prefs(getContext()).edit().putBoolean("quiet", quiet).commit();
            if (quiet) ((NotificationManager)getContext().getSystemService(Context.NOTIFICATION_SERVICE)).cancel(NanaNotificationJob.JOB);
        }
        call.resolve();
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
            if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(new NotificationChannel("nana_presence", "生活动态", NotificationManager.IMPORTANCE_DEFAULT));
            Intent intent = new Intent(getContext(), MainActivity.class);intent.putExtra("nana_page", page);
            intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent pending = PendingIntent.getActivity(getContext(), 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            manager.notify(1, new NotificationCompat.Builder(getContext(), "nana_presence")
                .setSmallIcon(R.drawable.nana_notification).setContentTitle("Nana Space · 新动态")
                .setContentText("打开查看有来源的最新状态。").setContentIntent(pending).setAutoCancel(true).build());
            seen.edit().putString("last_event", event).apply();call.resolve();
        } catch (Exception ex) {reject(call, ex);}
    }
    @PluginMethod public void launchRoute(PluginCall call) {
        String page = getActivity().getIntent().getStringExtra("nana_page");
        JSObject out = new JSObject();out.put("page", PAGES.contains(page) ? page : "home");call.resolve(out);
    }
}
