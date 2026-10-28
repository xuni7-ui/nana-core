package life.nana.space;

import android.Manifest;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.speech.tts.Voice;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;
import java.util.ArrayList;
import java.util.Locale;

/** User-triggered local device speech. No audio upload, recording file, background
 * microphone, online recognizer fallback or independent cognition/model call. */
@CapacitorPlugin(name = "NanaSpeech", permissions = {
    @Permission(alias = "microphone", strings = { Manifest.permission.RECORD_AUDIO })
})
public class NanaSpeechPlugin extends Plugin {
    private final Handler main = new Handler(Looper.getMainLooper());
    private SpeechRecognizer recognizer;
    private TextToSpeech speaker;
    private PluginCall pending;
    private Runnable deadline;
    private int generation;

    private boolean localRecognition() {
        return Build.VERSION.SDK_INT >= 31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(getContext());
    }
    @PluginMethod public void capabilities(PluginCall call) {
        JSObject result = new JSObject();
        result.put("asr", localRecognition() ? "DEVICE_LOCAL_AVAILABLE" : "DEVICE_LOCAL_UNAVAILABLE");
        result.put("tts", "DEVICE_LOCAL_VOICE_REQUIRED");
        result.put("audio_uploaded", false);
        call.resolve(result);
    }
    private void release() {
        if (deadline != null) main.removeCallbacks(deadline);
        deadline = null;
        SpeechRecognizer oldRecognizer = recognizer; recognizer = null;
        TextToSpeech oldSpeaker = speaker; speaker = null;
        if (oldRecognizer != null) { oldRecognizer.cancel(); oldRecognizer.destroy(); }
        if (oldSpeaker != null) { oldSpeaker.stop(); oldSpeaker.shutdown(); }
    }
    private void fail(String code) {
        PluginCall call = pending; pending = null;
        generation++;
        release();
        if (call != null) call.reject(code);
    }
    private void complete(JSObject value) {
        PluginCall call = pending; pending = null;
        generation++;
        release();
        if (call != null) call.resolve(value);
    }
    @PluginMethod public void listen(PluginCall call) {
        if (!localRecognition()) { call.reject("DEVICE_LOCAL_ASR_UNAVAILABLE"); return; }
        if (getPermissionState("microphone") != PermissionState.GRANTED)
            requestPermissionForAlias("microphone", call, "microphoneResult");
        else listenGranted(call);
    }
    @PermissionCallback private void microphoneResult(PluginCall call) {
        if (getPermissionState("microphone") != PermissionState.GRANTED) call.reject("MICROPHONE_PERMISSION_REQUIRED");
        else listenGranted(call);
    }
    private void listenGranted(PluginCall call) {
        main.post(() -> {
            if (pending != null) { call.reject("DEVICE_SPEECH_BUSY"); return; }
            pending = call;
            final int attempt = ++generation;
            try {
                if (!localRecognition()) { fail("DEVICE_LOCAL_ASR_UNAVAILABLE"); return; }
                recognizer = SpeechRecognizer.createOnDeviceSpeechRecognizer(getContext());
                recognizer.setRecognitionListener(new RecognitionListener() {
                    public void onReadyForSpeech(Bundle b) { }
                    public void onBeginningOfSpeech() { }
                    public void onRmsChanged(float f) { }
                    public void onBufferReceived(byte[] bytes) { }
                    public void onEndOfSpeech() { }
                    public void onPartialResults(Bundle b) { }
                    public void onEvent(int i, Bundle b) { }
                    public void onError(int error) { if (attempt == generation) fail("DEVICE_ASR_NO_RESULT"); }
                    public void onResults(Bundle data) {
                        if (attempt != generation || pending == null) return;
                        ArrayList<String> results = data.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                        if (results == null || results.isEmpty() || results.get(0).isEmpty()) { fail("DEVICE_ASR_NO_RESULT"); return; }
                        JSObject result = new JSObject();
                        String value = results.get(0);
                        result.put("text", value.substring(0, Math.min(2048, value.length())));
                        result.put("source", "DEVICE_LOCAL_ASR"); result.put("audio_uploaded", false);
                        complete(result);
                    }
                });
                Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "zh-CN");
                intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
                intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
                intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true);
                recognizer.startListening(intent);
                deadline = () -> { if (attempt == generation) fail("DEVICE_ASR_TIMEOUT_NO_RETRY"); };
                main.postDelayed(deadline, 15000);
            } catch (Exception ignored) { fail("DEVICE_LOCAL_ASR_UNAVAILABLE"); }
        });
    }
    @PluginMethod public void speak(PluginCall call) {
        final String text = call.getString("text");
        if (text == null || text.isEmpty() || text.length() > 2048) { call.reject("DEVICE_SPEECH_TEXT_BOUND"); return; }
        main.post(() -> {
            if (pending != null) { call.reject("DEVICE_SPEECH_BUSY"); return; }
            pending = call;
            final int attempt = ++generation;
            try {
                speaker = new TextToSpeech(getContext(), status -> main.post(() -> {
                    if (attempt != generation || pending == null || speaker == null) return;
                    if (status != TextToSpeech.SUCCESS || speaker.getVoices() == null) { fail("DEVICE_LOCAL_TTS_UNAVAILABLE"); return; }
                    Voice selected = null;
                    for (Voice voice : speaker.getVoices()) {
                        if (!voice.isNetworkConnectionRequired() && voice.getLocale().getLanguage().equals(Locale.CHINESE.getLanguage())) {
                            selected = voice; break;
                        }
                    }
                    if (selected == null || speaker.setVoice(selected) != TextToSpeech.SUCCESS) { fail("DEVICE_LOCAL_TTS_UNAVAILABLE"); return; }
                    speaker.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                        public void onStart(String id) { }
                        public void onDone(String id) { main.post(() -> {
                            if (attempt != generation || pending == null) return;
                            JSObject result = new JSObject(); result.put("state", "PLAYBACK_FINISHED");
                            result.put("source", "DEVICE_LOCAL_TTS"); complete(result);
                        }); }
                        @Deprecated public void onError(String id) { main.post(() -> { if (attempt == generation) fail("DEVICE_TTS_FAILED"); }); }
                    });
                    if (speaker.speak(text, TextToSpeech.QUEUE_FLUSH, null, "nana-explicit-reply") != TextToSpeech.SUCCESS)
                        fail("DEVICE_TTS_FAILED");
                }));
                deadline = () -> { if (attempt == generation) fail("DEVICE_TTS_TIMEOUT"); }; main.postDelayed(deadline, 120000);
            } catch (Exception ignored) { fail("DEVICE_LOCAL_TTS_UNAVAILABLE"); }
        });
    }
    @PluginMethod public void stop(PluginCall call) {
        main.post(() -> { fail("DEVICE_SPEECH_CANCELLED"); call.resolve(); });
    }
    @Override protected void handleOnPause() { main.post(() -> fail("DEVICE_SPEECH_CANCELLED")); }
    @Override protected void handleOnDestroy() { main.post(() -> fail("DEVICE_SPEECH_CANCELLED")); }
}
