import os

os.environ["DB_USER"] = "pippo"
os.environ["DB_PASSWORD"] = "baudo"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "1234"
os.environ["DB_NAME"] = "sanremo"
os.environ["CLASSIFIER_MODEL_PATH"] = "/home/pippo/classifier.tflite"
os.environ["DETECTOR_MODEL_PATH"] = "/home/pippo/detector.tflite"
os.environ["S3_ENDPOINT_URL"] = "http://127.0.0.1:5000"
os.environ["S3_ACCESS_KEY"] = "test"
os.environ["S3_SECRET_KEY"] = "test"
