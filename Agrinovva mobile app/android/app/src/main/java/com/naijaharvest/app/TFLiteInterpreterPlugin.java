package com.naijaharvest.app;

import android.content.res.AssetFileDescriptor;
import android.util.Base64;
import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONArray;
import org.tensorflow.lite.Interpreter;
import org.tensorflow.lite.Tensor;

import java.io.ByteArrayOutputStream;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;

/**
 * Native TFLite bridge for Naija Harvest.
 *
 * Contract (matches src/js/diagnosis.js):
 *   window.NaijaHarvestDiagnosis.runInference(base64Uint8Array) -> { logits: number[30] }
 *
 * INPUT tensor  : Uint8 [1, 224, 224, 3] = 150,528 bytes NHWC, raw pixels 0-255.
 *   JS sends Uint8Array (NOT Float32Array). TFLite applies scale/zero_point internally.
 *   Do NOT pre-normalize: that causes 602,112 vs 150,528 byte mismatch.
 *
 * OUTPUT tensor : Uint8 [1, 30] — the INT8 quantized output is ALSO uint8.
 *   TFLite CANNOT auto-cast uint8 output into a Java float[] ([F).
 *   We collect output as byte[][], then manually dequantize:
 *     dequantized = (byteVal & 0xFF  -  zeroPoint) * scale
 *   This converts the raw quantized byte back to a real float logit.
 *
 * Resolves with { logits: number[30] } — 30 dequantized float logits.
 */
@CapacitorPlugin(name = "NaijaHarvestDiagnosis")
public class TFLiteInterpreterPlugin extends Plugin {

    private static final String TAG = "NaijaHarvestTFLite";
    private static final String MODEL_ASSET = "model/plant_disease_model.tflite";
    private static final String FALLBACK_MODEL_ASSET = "model/naijastables_mobilenetv3_int8.tflite";
    private static final int INPUT_BYTES = 1 * 224 * 224 * 3; // 150,528 bytes (raw RGB 0-255)

    private Interpreter interpreter;

    @PluginMethod
    public void runInference(PluginCall call) {
        try {
            if (interpreter == null) {
                loadModel();
            }
            String inputBase64 = call.getString("input");
            if (inputBase64 == null) {
                call.reject("Missing 'input': base64-encoded Uint8Array of " + INPUT_BYTES + " bytes (RGB raw pixels)");
                return;
            }
            byte[] inputBytes = Base64.decode(inputBase64, Base64.DEFAULT);
            if (inputBytes.length < INPUT_BYTES) {
                call.reject("Input too small: expected " + INPUT_BYTES + " bytes, got " + inputBytes.length
                        + ". Send Uint8Array (raw pixels 0-255).");
                return;
            }

            Tensor inTensor = interpreter.getInputTensor(0);
            org.tensorflow.lite.DataType inType = inTensor.dataType();
            int[] inShape = inTensor.shape();

            ByteBuffer inputBuffer;
            if (inType == org.tensorflow.lite.DataType.FLOAT32) {
                // Float32 model (e.g. plant_disease_model.tflite)
                // Shape: [1, 3, 224, 224] (NCHW)
                // Normalization: ImageNet mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                int plane = 224 * 224;
                inputBuffer = ByteBuffer.allocateDirect(1 * 3 * 224 * 224 * 4).order(ByteOrder.nativeOrder());
                
                boolean isNCHW = (inShape != null && inShape.length == 4 && inShape[1] == 3);
                if (isNCHW) {
                    // Channel 0: R
                    for (int i = 0; i < plane; i++) {
                        float r = (inputBytes[i * 3] & 0xFF) / 255.0f;
                        inputBuffer.putFloat((r - 0.485f) / 0.229f);
                    }
                    // Channel 1: G
                    for (int i = 0; i < plane; i++) {
                        float g = (inputBytes[i * 3 + 1] & 0xFF) / 255.0f;
                        inputBuffer.putFloat((g - 0.456f) / 0.224f);
                    }
                    // Channel 2: B
                    for (int i = 0; i < plane; i++) {
                        float b = (inputBytes[i * 3 + 2] & 0xFF) / 255.0f;
                        inputBuffer.putFloat((b - 0.406f) / 0.225f);
                    }
                } else {
                    // NHWC Float32 (MobileNetV3: [-1.0, 1.0])
                    for (int i = 0; i < plane; i++) {
                        float r = (inputBytes[i * 3] & 0xFF) / 255.0f;
                        float g = (inputBytes[i * 3 + 1] & 0xFF) / 255.0f;
                        float b = (inputBytes[i * 3 + 2] & 0xFF) / 255.0f;
                        inputBuffer.putFloat((r * 2.0f) - 1.0f);
                        inputBuffer.putFloat((g * 2.0f) - 1.0f);
                        inputBuffer.putFloat((b * 2.0f) - 1.0f);
                    }
                }
                inputBuffer.rewind();
            } else {
                // INT8 / UINT8 quantized model
                inputBuffer = ByteBuffer.allocateDirect(INPUT_BYTES).order(ByteOrder.LITTLE_ENDIAN);
                inputBuffer.put(inputBytes, 0, INPUT_BYTES);
                inputBuffer.rewind();
            }

            // Output tensor inspection
            Tensor outTensor = interpreter.getOutputTensor(0);
            org.tensorflow.lite.DataType outType = outTensor.dataType();
            int[] outShape = outTensor.shape();
            int numClasses = 38;
            if (outShape != null && outShape.length > 0) {
                numClasses = outShape[outShape.length - 1];
            }

            float[] logitsArr = new float[numClasses];
            if (outType == org.tensorflow.lite.DataType.FLOAT32) {
                float[][] floatOutput = new float[1][numClasses];
                interpreter.run(inputBuffer, floatOutput);
                logitsArr = floatOutput[0];
            } else {
                // UINT8 quantized output
                float outScale = 1.0f;
                int outZeroPoint = 0;
                try {
                    outScale = outTensor.quantizationParams().getScale();
                    outZeroPoint = outTensor.quantizationParams().getZeroPoint();
                } catch (Exception ignored) {}

                byte[][] rawOutput = new byte[1][numClasses];
                interpreter.run(inputBuffer, rawOutput);
                for (int i = 0; i < numClasses; i++) {
                    logitsArr[i] = ((rawOutput[0][i] & 0xFF) - outZeroPoint) * outScale;
                }
            }

            // Debug log top-3 values
            float maxLogit = -Float.MAX_VALUE;
            int maxIdx = 0;
            for (int i = 0; i < numClasses; i++) {
                if (logitsArr[i] > maxLogit) {
                    maxLogit = logitsArr[i];
                    maxIdx = i;
                }
            }
            float second = -Float.MAX_VALUE, third = -Float.MAX_VALUE;
            int secIdx = 0, thrIdx = 0;
            for (int i = 0; i < numClasses; i++) {
                if (i == maxIdx) continue;
                if (logitsArr[i] > second) {
                    third = second; thrIdx = secIdx;
                    second = logitsArr[i]; secIdx = i;
                } else if (logitsArr[i] > third) {
                    third = logitsArr[i]; thrIdx = i;
                }
            }
            Log.d(TAG, String.format("Inference (%d classes) top-3: [%d]=%.4f  [%d]=%.4f  [%d]=%.4f",
                    numClasses, maxIdx, maxLogit, secIdx, second, thrIdx, third));

            JSONArray logits = new JSONArray();
            for (float v : logitsArr) {
                logits.put((double) v);
            }
            JSObject ret = new JSObject();
            ret.put("logits", logits);
            call.resolve(ret);
        } catch (Exception e) {
            Log.e(TAG, "runInference failed", e);
            call.reject("Inference failed: " + e.getMessage(), e);
        }
    }

    private void loadModel() throws IOException {
        long t0 = System.currentTimeMillis();
        String assetPath = MODEL_ASSET;

        // Try primary MODEL_ASSET first, then FALLBACK_MODEL_ASSET
        try (InputStream testStream = getContext().getAssets().open(MODEL_ASSET)) {
            assetPath = MODEL_ASSET;
        } catch (IOException e) {
            Log.w(TAG, "Primary model " + MODEL_ASSET + " not found, falling back to " + FALLBACK_MODEL_ASSET);
            assetPath = FALLBACK_MODEL_ASSET;
        }

        try {
            // Zero-copy memory-mapped I/O
            AssetFileDescriptor afd = getContext().getAssets().openFd(assetPath);
            FileInputStream fis = new FileInputStream(afd.getFileDescriptor());
            FileChannel fileChannel = fis.getChannel();
            MappedByteBuffer modelBuffer = fileChannel.map(
                FileChannel.MapMode.READ_ONLY,
                afd.getStartOffset(),
                afd.getDeclaredLength()
            );
            interpreter = new Interpreter(modelBuffer);
            Log.i(TAG, "Model loaded via memory-map from " + assetPath + " in " + (System.currentTimeMillis() - t0) + " ms");
        } catch (IOException e) {
            Log.w(TAG, "openFd failed for " + assetPath + ", falling back to streaming read", e);
            try (InputStream is = getContext().getAssets().open(assetPath)) {
                byte[] modelBytes = readAllBytes(is);
                ByteBuffer modelBuffer = ByteBuffer.allocateDirect(modelBytes.length);
                modelBuffer.put(modelBytes);
                modelBuffer.rewind();
                interpreter = new Interpreter(modelBuffer);
                Log.i(TAG, "Model loaded via fallback stream: " + modelBytes.length + " bytes in "
                        + (System.currentTimeMillis() - t0) + " ms");
            }
        }
    }

    private static byte[] readAllBytes(InputStream is) throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while ((n = is.read(buf)) != -1) {
            bos.write(buf, 0, n);
        }
        return bos.toByteArray();
    }
}