package life.nana.space;

import android.Manifest;
import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.util.Base64;
import androidx.core.app.NotificationCompat;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.net.ssl.HttpsURLConnection;
import org.json.JSONArray;
import org.json.JSONObject;

/** Explicit device subscription, bounded OS scheduling, no semantic/model calls.
 * Reads the existing Keystore binding; no new token or provider key is persisted.
 * Android may delay a job in Doze or suppress it after force-stop. This is not
 * instant cloud push, and local submission is not proof the human saw a notice.
 */
public class NanaNotificationJob extends JobService {
    static final int JOB = 4402;
    static final Object LOCK = new Object();
    static final String PREFS = "nana_notification_subscription";
    private volatile boolean stopped;
    private volatile int generation;

    static SharedPreferences prefs(Context c) { return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE); }
    static boolean permission(Context c) {
        return Build.VERSION.SDK_INT < 33 || c.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED;
    }
    static String configure(Context c, boolean enabled) throws Exception {
        synchronized (LOCK) {
            JobScheduler jobs = (JobScheduler)c.getSystemService(Context.JOB_SCHEDULER_SERVICE);
            if (!enabled) {
                prefs(c).edit().putBoolean("enabled", false).putString("state", "DISABLED").commit();
                jobs.cancel(JOB);
                ((NotificationManager)c.getSystemService(Context.NOTIFICATION_SERVICE)).cancel(JOB);
                return "DISABLED";
            }
            if (!permission(c)) throw new Exception("NOTIFICATION_PERMISSION_REQUIRED");
            if (!c.getSharedPreferences("nana_secure_binding", Context.MODE_PRIVATE).contains("encrypted"))
                throw new Exception("PAIRING_REQUIRED");
            JobInfo job = new JobInfo.Builder(JOB, new ComponentName(c, NanaNotificationJob.class))
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setPersisted(true)
                .setPeriodic(15 * 60 * 1000L).build();
            if (jobs.schedule(job) != JobScheduler.RESULT_SUCCESS) throw new Exception("BACKGROUND_SCHEDULE_UNAVAILABLE");
            prefs(c).edit().putBoolean("enabled", true).putString("state", "SCHEDULED_ANDROID_MAY_DELAY").commit();
            return "SCHEDULED_ANDROID_MAY_DELAY";
        }
    }
    static JSONObject status(Context c) throws Exception {
        SharedPreferences p = prefs(c);
        return new JSONObject().put("enabled", p.getBoolean("enabled", false))
            .put("state", p.getString("state", "DISABLED"))
            .put("interval_minutes", 15).put("private_body_in_notification", false)
            .put("instant_push", false).put("physical_delivery_qualified", false);
    }
    private static JSONObject binding(Context c, String encrypted) throws Exception {
        byte[] all = Base64.decode(encrypted, Base64.NO_WRAP);
        if (all.length < 29 || all.length > 8192) throw new Exception("PAIRING_REQUIRED");
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        SecretKey key = (SecretKey)store.getKey("nana.space.session.aes.v1", null);
        if (key == null) throw new Exception("PAIRING_REQUIRED");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, Arrays.copyOfRange(all, 0, 12)));
        byte[] plain = cipher.doFinal(Arrays.copyOfRange(all, 12, all.length));
        try { return new JSONObject(new String(plain, StandardCharsets.UTF_8)); }
        finally { Arrays.fill(plain, (byte)0); Arrays.fill(all, (byte)0); }
    }
    private static JSONObject http(String base, String route, JSONObject body, String token) throws Exception {
        if (!("session/native".equals(route) || "notifications/inbox".equals(route))) throw new Exception("BACKGROUND_ROUTE_DENIED");
        HttpsURLConnection conn = (HttpsURLConnection)new URL(NanaHostPlugin.origin(base) + "/api/nana-space/v2/" + route).openConnection();
        conn.setInstanceFollowRedirects(false); conn.setConnectTimeout(5000); conn.setReadTimeout(5000);
        conn.setRequestMethod(body == null ? "GET" : "POST");
        conn.setRequestProperty("Accept", "application/json"); conn.setRequestProperty("Cache-Control", "no-store");
        if (token != null) conn.setRequestProperty("Authorization", "Bearer " + token);
        try {
            if (body != null) {
                byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
                if (bytes.length > 4096) throw new Exception("BACKGROUND_REQUEST_BOUND");
                conn.setDoOutput(true); conn.setFixedLengthStreamingMode(bytes.length);
                conn.setRequestProperty("Content-Type", "application/json");
                try (java.io.OutputStream out = conn.getOutputStream()) { out.write(bytes); }
                finally { Arrays.fill(bytes, (byte)0); }
            }
            int code = conn.getResponseCode();
            if (code != 200) throw new Exception(code == 401 ? "SESSION_DENIED" : "BACKGROUND_SERVER_UNAVAILABLE");
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            try (InputStream in = conn.getInputStream()) {
                byte[] part = new byte[2048]; int size;
                while ((size = in.read(part)) != -1) {
                    if (output.size() + size > 32768) throw new Exception("BACKGROUND_RESPONSE_BOUND");
                    output.write(part, 0, size);
                }
            }
            JSONObject value = new JSONObject(output.toString(StandardCharsets.UTF_8.name()));
            if (!"nana-space-live/v2".equals(value.optString("contract"))) throw new Exception("CONTRACT_MISMATCH");
            return value;
        } finally { conn.disconnect(); }
    }
    @Override public boolean onStartJob(JobParameters params) {
        stopped = false;
        final int attempt = ++generation;
        new Thread(() -> {
            try { poll(attempt); }
            catch (Exception error) {
                String code = error.getMessage();
                String safe = code != null && code.matches("[A-Z_]{1,96}") ? code : "BACKGROUND_CHECK_UNAVAILABLE";
                synchronized (LOCK) {
                    if (attempt != generation || stopped) return;
                    prefs(this).edit().putString("state", safe).commit();
                    if ("SESSION_DENIED".equals(safe) || "INVALID_IDENTITY".equals(safe) || "PAIRING_REQUIRED".equals(safe)) {
                        try { configure(this, false); } catch (Exception ignored) { }
                    }
                }
            } finally { jobFinished(params, false); }
        }, "nana-notification-read").start();
        return true;
    }
    @Override public boolean onStopJob(JobParameters params) { stopped = true; generation++; return false; }
    private void poll(int attempt) throws Exception {
        if (stopped || attempt != generation || !prefs(this).getBoolean("enabled", false) || prefs(this).getBoolean("quiet", false) || !permission(this)) return;
        SharedPreferences secure = getSharedPreferences("nana_secure_binding", MODE_PRIVATE);
        String encrypted = secure.getString("encrypted", null);
        if (encrypted == null) throw new Exception("PAIRING_REQUIRED");
        JSONObject b = binding(this, encrypted);
        JSONObject request = new JSONObject().put("device_id", b.getString("device_id"))
            .put("refresh_token", b.getString("refresh_token")).put("subject_id", b.getString("subject_id"));
        JSONObject session = http(b.getString("base"), "session/native", request, null);
        JSONObject envelope = http(b.getString("base"), "notifications/inbox", null, session.getString("access_token"));
        if (!b.getString("subject_id").equals(envelope.optString("subject_id"))
            || !b.getString("lineage_binding").equals(envelope.optString("lineage_binding"))
            || !b.getString("realm").equals(envelope.optString("realm"))
            || envelope.optBoolean("execution_authority", true)) throw new Exception("INVALID_IDENTITY");
        JSONArray items = envelope.getJSONObject("data").getJSONArray("items");
        if (items.length() > 8) throw new Exception("BACKGROUND_RESPONSE_BOUND");
        synchronized (LOCK) {
            if (stopped || attempt != generation || !prefs(this).getBoolean("enabled", false) || prefs(this).getBoolean("quiet", false)
                || !encrypted.equals(secure.getString("encrypted", null))) return;
            String day = Long.toString(System.currentTimeMillis() / 86400000L);
            SharedPreferences p = prefs(this);
            int today = day.equals(p.getString("day", "")) ? p.getInt("today", 0) : 0;
            Set<String> seen = new HashSet<>(p.getStringSet("seen", new HashSet<>()));
            SharedPreferences.Editor cleanup = p.edit();
            long cutoff = System.currentTimeMillis() - 8 * 86400000L;
            seen.removeIf(id -> {
                if (p.getLong("seen_at." + id, 0) >= cutoff) return false;
                cleanup.remove("seen_at." + id); return true;
            });
            cleanup.putStringSet("seen", seen).commit();
            String event = null;
            for (int i = 0; i < items.length(); i++) {
                String id = items.getJSONObject(i).optString("event_id");
                if (!id.matches("[A-Za-z0-9._:-]{1,96}")) throw new Exception("BACKGROUND_RESPONSE_BOUND");
                String scoped = b.getString("subject_id") + ":" + b.getString("lineage_binding") + ":" + id;
                if (!seen.contains(scoped)) { event = scoped; break; }
            }
            if (event == null || today >= 3 || System.currentTimeMillis() - p.getLong("last_at", 0) < 3600000L) return;
            if (seen.size() >= 128) return; // Explicit disable/re-enable does not clear dedupe.
            // Mark before local notification: a crash may lose a hint, never spam
            // the same original C candidate after process or device restart.
            seen.add(event);
            if (!p.edit().putStringSet("seen", seen).putString("day", day).putInt("today", today+1)
                .putLong("seen_at." + event, System.currentTimeMillis())
                .putLong("last_at", System.currentTimeMillis()).putString("state", "LOCAL_HINT_SUBMITTED_NOT_HUMAN_ACK").commit()) return;
            NotificationManager manager = (NotificationManager)getSystemService(NOTIFICATION_SERVICE);
            if (Build.VERSION.SDK_INT >= 26)
                manager.createNotificationChannel(new NotificationChannel("nana_presence", "生活动态", NotificationManager.IMPORTANCE_DEFAULT));
            Intent intent = new Intent(this, MainActivity.class).putExtra("nana_page", "home")
                .setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent pending = PendingIntent.getActivity(this, JOB, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            manager.notify(JOB, new NotificationCompat.Builder(this, "nana_presence").setSmallIcon(R.drawable.nana_notification)
                .setContentTitle("Nana Space · 有新的动态").setContentText("有新的生活动态，方便时打开看看。")
                .setVisibility(NotificationCompat.VISIBILITY_PRIVATE).setContentIntent(pending).setAutoCancel(true).build());
        }
    }
}
