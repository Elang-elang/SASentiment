import urllib.request

url = "https://storage.googleapis.com/download.tensorflow.org/models/tflite/text_classification/text_classification.tflite"
urllib.request.urlretrieve(url, "model/sentimen_model.tflite")
