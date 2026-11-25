import os
import tensorflow as tf

model_path = r"Agrinovva mobile app/models/naijastables_mobilenetv3_int8.tflite"
interpreter = tf.lite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

print("Input details:")
for item in interpreter.get_input_details():
    print(item)

print("\nOutput details:")
for item in interpreter.get_output_details():
    print(item)
