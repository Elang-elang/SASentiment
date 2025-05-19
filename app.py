import os
import numpy as np
import logging
from datetime import datetime, timedelta
import json
import apsw
import joblib
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import plotly
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Untuk server tanpa GUI
import tflite_runtime.interpreter as tflite
from textblob import TextBlob
from googletrans import Translator
import pandas as pd
from better_profanity import profanity
from profanityfilter import ProfanityFilter
import csv
import requests
import time
pf_extended = ProfanityFilter()
# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("sentimen_analisis.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Inisialisasi Flask dan SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'rahasia_sentimen_analisis'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Konfigurasi database
DB_PATH = './sentimen_data.db'
PLOT_PATH = 'static/plots'
os.makedirs(PLOT_PATH, exist_ok=True)

# Set timeout koneksi database (dalam milidetik)
DB_TIMEOUT = 5000  # 5 detik

# Fungsi untuk mendapatkan koneksi database
def get_db_connection():
    """Mendapatkan koneksi database dengan APSW"""
    try:
        # Buat koneksi tanpa parameter timeout
        conn = apsw.Connection(DB_PATH)
        
        # Set timeout menggunakan PRAGMA
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA busy_timeout = {DB_TIMEOUT}")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        
        return conn
    except Exception as e:
        logger.error(f"Gagal membuat koneksi database: {str(e)}")
        raise

# -------------- BAGIAN MODEL SENTIMENT --------------

class SentimenModel:
    def __init__(self, model_path, vocab_path=None, max_length=256):
        try:
            # Inisialisasi parameter dasar
            self.max_length = max_length
            self.preprocessor = None  # Inisialisasi default
            
            # Verifikasi file model
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"File model tidak ditemukan: {model_path}")
            
            # Load model TFLite
            self.interpreter = tflite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            
            # Dapatkan input/output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            # Load preprocessor jika ada
            if vocab_path and os.path.exists(vocab_path):
                with open(vocab_path, 'rb') as f:
                    self.preprocessor = joblib.load(f)
                
            logger.info(f"Model berhasil dimuat. Max length: {self.max_length}")
            
            # Inisialisasi translator
            self.translator = Translator()
            
            # Load lexicon sentimen
            self.positive_words = self.load_positive_words()
            self.negative_words = self.load_negative_words()
            
            # Tambahkan kustom profanity filter
            self.setup_profanity_filter()
            
        except Exception as e:
            logger.error(f"Gagal memuat model: {str(e)}")
            raise
        
        logger.info(f"Input details: {self.input_details}")
        logger.info(f"Output details: {self.output_details}")
    
    def setup_profanity_filter(self):
        """Setup profanity filter dengan kata-kata kustom"""
        custom_badwords = ['idiot', 'stupid', 'hate', 'terrible', 'awful', 'worst', 
                          'jelek', 'buruk', 'bodoh', 'tolol', 'menyebalkan']
        profanity.load_censor_words(custom_badwords)
    
    def load_positive_words(self):
        """Load daftar kata positif dari file atau buat baru"""
        try:
            # Coba load dari file
            if os.path.exists('positive_words.csv'):
                df = pd.read_csv('positive_words.csv')
                word_set = set(df['word'].str.lower().tolist())
            else:
                # Buat file baru
                word_set = {
                    'good', 'great', 'excellent', 'awesome', 'wonderful', 'amazing', 'fantastic',
                    'terrific', 'outstanding', 'superb', 'perfect', 'fabulous', 'exceptional',
                    'marvelous', 'brilliant', 'spectacular', 'impressive', 'lovely', 'delightful',
                    'pleasant', 'enjoyable', 'magnificent', 'splendid', 'remarkable', 'phenomenal',
                    'baik', 'bagus', 'hebat', 'luar biasa', 'mantap', 'keren', 'istimewa',
                    'menyenangkan', 'memuaskan', 'sempurna', 'indah', 'menakjubkan', 'wow',
                    'love', 'happy', 'joy', 'glad', 'positive', 'suka', 'senang', 'gembira'
                }
                
                # Simpan ke file untuk penggunaan selanjutnya
                pd.DataFrame({'word': list(word_set)}).to_csv('positive_words.csv', index=False)
            
            return word_set
            
        except Exception as e:
            logger.error(f"Gagal memuat daftar kata positif: {str(e)}")
            # Return default fallback
            return {'good', 'great', 'excellent', 'amazing', 'wonderful', 'baik', 'bagus', 'hebat'}
    
    def load_negative_words(self):
        """Load daftar kata negatif dari file atau buat baru"""
        try:
            # Coba load dari file
            if os.path.exists('negative_words.csv'):
                df = pd.read_csv('negative_words.csv')
                word_set = set(df['word'].str.lower().tolist())
            else:
                # Buat file baru
                word_set = {
                    'bad', 'terrible', 'holy','awful', 'horrible', 'poor', 'disappointing', 'unpleasant',
                    'negative', 'dreadful', 'lousy', 'subpar', 'inferior', 'mediocre', 'inadequate',
                    'unsatisfactory', 'appalling', 'abysmal', 'atrocious', 'horrendous', 'pathetic',
                    'buruk', 'jelek', 'mengecewakan', 'menyebalkan', 'tidak bagus', 'payah', 'parah',
                    'hate', 'dislike', 'annoying', 'frustrating', 'irritating', 'benci', 'kesal',
                    'marah', 'sedih', 'kecewa', 'murung', 'geram', 'jengkel', 'sebal', 'berngsek', 'shit'
                }
                
                # Simpan ke file untuk penggunaan selanjutnya
                pd.DataFrame({'word': list(word_set)}).to_csv('negative_words.csv', index=False)
            
            return word_set
            
        except Exception as e:
            logger.error(f"Gagal memuat daftar kata negatif: {str(e)}")
            # Return default fallback
            return {'bad', 'terrible', 'awful', 'horrible', 'buruk', 'jelek', 'mengecewakan'}
    
    def translate_text(self, text, dest='en', src='auto'):
        """Terjemahkan teks ke bahasa target dengan error handling"""
        try:
            for _ in range(3):  # Coba 3 kali
                try:
                    result = self.translator.translate(text, dest=dest, src=src)
                    return result.text
                except Exception as e:
                    logger.warning(f"Gagal menerjemahkan, mencoba lagi: {str(e)}")
                    time.sleep(1)  # Tunggu sejenak sebelum coba lagi
            
            # Fallback: gunakan API alternatif atau hanya return teks asli
            return text
        except:
            return text
    
    def analyze_sentiment_lexicon(self, text):
        """Analisis sentimen berdasarkan lexicon (kamus kata)"""
        text_translate = self.translate_text(text)
        text_lower = text_translate.lower()
        words = text_lower.split()
        
        positive_count = 0
        negative_count = 0
        positive_found = []
        
        for word in words:
            word = word.strip(".,!?;:'\"()-")
            new_word=pf_extended.censor(word)
            if new_word in self.positive_words:
                positive_count += 1
                positive_found.append(word)
            if "*" in new_word:
                negative_count += 1
        
        # Deteksi profanity
        has_profanity = profanity.contains_profanity(text)
        if has_profanity:
            negative_count += 2  # Berikan bobot lebih untuk kata-kata kotor
        
        # Evaluasi TextBlob (sebagai faktor tambahan)
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Logika kombinasi
        if negative_count > positive_count or polarity < -0.3:
            label = "negatif"
            confidence = 0.6 +  (negative_count - positive_count) / 10
        elif positive_count > negative_count or polarity > 0.3:
            label = "positif"
            confidence = 0.6 + ((positive_count - negative_count))
        else:
            label = "netral"
            confidence = 0.7 + ((positive_count - negative_count))
        
        return {
            "label": label,
            "skor": min(0.99, confidence),
            "positive_words": positive_found,
            "translations": [self.translate_text(word, dest='id', src='en') 
                           if len(word) > 1 else word for word in positive_found]
        }
    
    def preprocess_text(self, text):
        """Implementasi yang sesuai dengan bentuk input model"""
        logger.info(f"Preprocessing text dengan max length: {self.max_length}")
        words = text.lower().split()
    
        # Sesuaikan dengan bentuk yang diharapkan model
        tokens = np.zeros((1, self.max_length), dtype=np.float32)
    
        for i, word in enumerate(words[:self.max_length]):
            tokens[0, i] = hash(word) % 10000 / 10000  # Hashing sederhana
        
        return [tokens]  # Kembalikan sebagai list tensor
    
    def predict(self, text):
        """
        Melakukan prediksi sentimen terhadap teks
        
        Args:
            text: Teks yang akan dianalisis
            
        Returns:
            Dictionary berisi hasil prediksi (label dan skor)
        """
        result = {
            'label': '',
            'skor': 0.0,
            'positive_words': [],
            'translations': []
        }
        
        # Cek apakah teks kosong
        if not text or text.strip() == '':
            result['label'] = 'netral'
            result['skor'] = 0.5
            return result
        
        try:
            # Terjemahkan teks ke bahasa Inggris jika bukan dalam bahasa Inggris
            original_text = text
            is_english = False
            
            try:
                detected = self.translator.detect(text)
                is_english = detected.lang == 'en'
                logger.info(f"Detected language: {detected.lang}, confidence: {detected.confidence}")
            except:
                logger.warning("Gagal mendeteksi bahasa, melanjutkan dengan teks asli")
            
            # Jika bukan bahasa Inggris, coba terjemahkan
            translated_text = text
            if not is_english:
                try:
                    translated_text = self.translate_text(text)
                    logger.info(f"Teks diterjemahkan: {translated_text}")
                except Exception as e:
                    logger.warning(f"Gagal menerjemahkan: {str(e)}")
            
            # Deteksi profanity (kata-kata kotor)
            if profanity.contains_profanity(text) or profanity.contains_profanity(translated_text):
                logger.info("Profanity terdeteksi dalam teks")
                return {
                    "label": "negatif",
                    "skor": 0.92,
                    "positive_words": [],
                    "translations": [],
                    "timestamp": datetime.now().isoformat()
                }
            
            # Analisis sentimen berbasis lexicon
            lexicon_result = self.analyze_sentiment_lexicon(translated_text)
            
            # Analisis kata positif
            result['positive_words'] = lexicon_result['positive_words']
            result['translations'] = lexicon_result['translations']
            
            # Coba gunakan model jika tersedia
            try:
                inputs = self.preprocess_text(translated_text)
                
                # Set input tensor
                for i, input_detail in enumerate(self.input_details):
                    input_shape = input_detail['shape']
                    if i < len(inputs):
                        input_data = inputs[i].astype(np.float32)
                        
                        # Reshape jika diperlukan
                        if input_data.shape != tuple(input_shape):
                            input_data = input_data.reshape(input_shape)
                        
                        self.interpreter.set_tensor(input_detail['index'], input_data)
                    else:
                        # Jika input hanya satu, dan model memerlukan input tambahan
                        self.interpreter.set_tensor(input_detail['index'], np.zeros(input_shape, dtype=np.float32))
                
                # Lakukan inferensi
                self.interpreter.invoke()
                
                # Dapatkan output
                output = self.interpreter.get_tensor(self.output_details[0]['index'])
                
                # Konversi output menjadi label dan skor
                if output.shape[-1] > 1:  # Multi-kelas
                    predicted_class = np.argmax(output[0])
                    confidence = output[0][predicted_class]
                    
                    # Map indeks kelas ke label sentimen
                    sentiment_map = {0: "negatif", 1: "netral", 2: "positif"}
                    model_label = sentiment_map.get(predicted_class, f"kelas_{predicted_class}")
                    model_score = float(confidence)
                else:  # Binary classification
                    score = output[0][0]
                    if score < 0.4:
                        model_label = "negatif"
                        model_score = 1 - score
                    elif score > 0.6:
                        model_label = "positif"
                        model_score = score
                    else:
                        model_label = "netral"
                        model_score = 0.5 + abs(score - 0.5)
                
                # Kombinasikan hasil model dengan lexicon
                if model_label == lexicon_result['label']:
                    # Jika kedua metode setuju, tingkatkan kepercayaan
                    final_label = model_label
                    final_score = max(model_score, lexicon_result['skor'])
                else:
                    # Jika berbeda, pilih yang memiliki skor lebih tinggi
                    if model_score > lexicon_result['skor']:
                        final_label = model_label
                        final_score = model_score
                    else:
                        final_label = lexicon_result['label']
                        final_score = lexicon_result['skor']
                
                return {
                    "label": final_label,
                    "skor": final_score,
                    "positive_words": result['positive_words'],
                    "translations": result['translations'],
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error model, fallback ke lexicon: {str(e)}", exc_info=True)
                return {
                    "label": lexicon_result['label'],
                    "skor": lexicon_result['skor'],
                    "positive_words": result['positive_words'],
                    "translations": result['translations'],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error umum: {str(e)}", exc_info=True)
            return {
                "label": "netral",
                "skor": 0.5,
                "error": str(e),
                "positive_words": [],
                "translations": [],
                "timestamp": datetime.now().isoformat()
            }

# -------------- BAGIAN DATABASE --------------

def init_db():
    """Inisialisasi database SQLite dengan APSW"""
    try:
        conn = apsw.Connection(DB_PATH)
        cursor = conn.cursor()
        
        # Set WAL mode di luar transaksi
        cursor.execute("PRAGMA busy_timeout = 5000")  # 5 detik timeout
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        
        # Buat tabel jika belum ada
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sentimen_hasil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teks TEXT NOT NULL,
            label TEXT NOT NULL,
            skor REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sentimen_statistik (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT NOT NULL UNIQUE,
            positif INTEGER DEFAULT 0,
            netral INTEGER DEFAULT 0,
            negatif INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0
        )
        ''')
        
        # Tambahkan data dummy jika tabel statistik kosong
        cursor.execute("SELECT COUNT(*) FROM sentimen_statistik")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Tambahkan data untuk 7 hari terakhir
            today = datetime.now()
            for i in range(7):
                date = (today - timedelta(days=6-i)).strftime('%Y-%m-%d')
                cursor.execute(
                    "INSERT INTO sentimen_statistik (tanggal, positif, netral, negatif, total) VALUES (?, ?, ?, ?, ?)",
                    (date, i+1, i+2, i, (i+1)+(i+2)+i)
                )
        
        logger.info("Database berhasil diinisialisasi")
        return True
    except Exception as e:
        logger.error(f"Error saat inisialisasi database: {str(e)}", exc_info=True)
        return False

def simpan_hasil(teks, hasil_prediksi):
    """Simpan hasil analisis ke database"""
    try:
        with apsw.Connection(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Gunakan transaksi eksplisit
            with conn:
                # Simpan hasil analisis individual
                cursor.execute(
                    "INSERT INTO sentimen_hasil (teks, label, skor, timestamp) VALUES (?, ?, ?, ?)",
                    (teks, hasil_prediksi['label'], hasil_prediksi['skor'], hasil_prediksi['timestamp'])
                )
                
                # Update statistik harian dengan UPSERT
                tanggal = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    INSERT INTO sentimen_statistik 
                    (tanggal, positif, netral, negatif, total) 
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(tanggal) DO UPDATE SET
                        positif = positif + ?,
                        netral = netral + ?,
                        negatif = negatif + ?,
                        total = total + 1
                ''', (
                    tanggal,
                    1 if hasil_prediksi['label'] == 'positif' else 0,
                    1 if hasil_prediksi['label'] == 'netral' else 0,
                    1 if hasil_prediksi['label'] == 'negatif' else 0,
                    1 if hasil_prediksi['label'] == 'positif' else 0,
                    1 if hasil_prediksi['label'] == 'netral' else 0,
                    1 if hasil_prediksi['label'] == 'negatif' else 0
                ))
            
            logger.info(f"Data tersimpan: {teks[:30]}...")
            return True
            
    except Exception as e:
        logger.error(f"Gagal menyimpan: {str(e)}", exc_info=True)
        return False

def dapatkan_statistik():
    """Ambil statistik sentimen dari database"""
    try:
        with apsw.Connection(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT tanggal, 
                       COALESCE(positif, 0) as positif, 
                       COALESCE(netral, 0) as netral, 
                       COALESCE(negatif, 0) as negatif,
                       COALESCE(total, 0) as total
                FROM sentimen_statistik 
                ORDER BY tanggal DESC 
                LIMIT 7
            """)
            
            return [{
                'tanggal': row[0],
                'positif': row[1],
                'netral': row[2],
                'negatif': row[3],
                'total': row[4]
            } for row in cursor.fetchall()]
            
    except Exception as e:
        logger.error(f"Error saat mengambil statistik: {str(e)}", exc_info=True)
        return []

# -------------- BAGIAN VISUALISASI --------------

def buat_visualisasi_plotly(statistik):
    """Buat visualisasi interaktif dengan Plotly"""
    try:
        # Balik urutan agar tanggal terlama di kiri
        statistik = statistik[::-1]
        
        tanggal = [stat['tanggal'] for stat in statistik]
        
        # Buat traces untuk masing-masing kategori sentimen
        trace_positif = go.Scatter(
            x=tanggal,
            y=[stat['positif'] for stat in statistik],
            mode='lines+markers',
            name='Positif',
            line=dict(color='green', width=2),
            marker=dict(symbol='circle', size=10)
        )
        
        trace_netral = go.Scatter(
            x=tanggal,
            y=[stat['netral'] for stat in statistik],
            mode='lines+markers',
            name='Netral',
            line=dict(color='blue', width=2),
            marker=dict(symbol='square', size=10)
        )
        
        trace_negatif = go.Scatter(
            x=tanggal,
            y=[stat['negatif'] for stat in statistik],
            mode='lines+markers',
            name='Negatif',
            line=dict(color='red', width=2),
            marker=dict(symbol='x', size=10)
        )
        
        # Buat pie chart untuk distribusi sentimen
        total_positif = sum(stat['positif'] for stat in statistik)
        total_netral = sum(stat['netral'] for stat in statistik)
        total_negatif = sum(stat['negatif'] for stat in statistik)
        
        pie_chart = go.Pie(
            labels=['Positif', 'Netral', 'Negatif'],
            values=[total_positif, total_netral, total_negatif],
            hole=0.4,
            marker=dict(colors=['green', 'blue', 'red']),
            textinfo='percent+label'
        )
        
        # Gabungkan grafik
        line_chart_data = [trace_positif, trace_netral, trace_negatif]
        pie_chart_data = [pie_chart]
        
        # Layout untuk line chart
        line_layout = go.Layout(
            title='Tren Sentimen 7 Hari Terakhir',
            xaxis=dict(title='Tanggal'),
            yaxis=dict(title='Jumlah'),
            legend=dict(x=0, y=1.1, orientation='h')
        )
        
        # Layout untuk pie chart
        pie_layout = go.Layout(
            title='Distribusi Sentimen',
            legend=dict(x=0, y=1.1, orientation='h')
        )
        
        # Buat figure dan konversi ke JSON
        line_fig = go.Figure(data=line_chart_data, layout=line_layout)
        pie_fig = go.Figure(data=pie_chart_data, layout=pie_layout)
        
        return {
            'line_chart': json.loads(plotly.io.to_json(line_fig)),
            'pie_chart': json.loads(plotly.io.to_json(pie_fig)),
            'latest_stats': {
                'positif': statistik[-1]['positif'] if statistik else 0,
                'netral': statistik[-1]['netral'] if statistik else 0,
                'negatif': statistik[-1]['negatif'] if statistik else 0,
                'total': statistik[-1]['total'] if statistik else 0
            }
        }
    except Exception as e:
        logger.error(f"Error saat membuat visualisasi plotly: {str(e)}")
        return None

# -------------- ROUTE DAN SOCKETIO --------------

@app.route('/')
def index():
    """Render halaman utama"""
    return render_template('index.html')

@app.route('/api/sentimen', methods=['POST'])
def analisis_sentimen():
    try:
        data = request.json
        teks = data['teks']
        
        hasil = model.predict(teks)
        simpan_hasil(teks, hasil)
        
        # Format response baru
        response = {
            'sentimen': {
                'label': hasil['label'],
                'skor': hasil['skor']
            },
            'kata_positif': hasil.get('positive_words', []),
            'terjemahan': hasil.get('translations', []),
            'statistik': dapatkan_statistik()
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handler saat client terhubung via WebSocket"""
    try:
        logger.info(f"Client terhubung: {request.sid}")
        
        # Kirim data visualisasi terbaru ke client baru
        statistik = dapatkan_statistik()
        visualisasi = buat_visualisasi_plotly(statistik)
        emit('update_visualisasi', visualisasi)
    except Exception as e:
        logger.error(f"Error saat menangani koneksi: {str(e)}")

@socketio.on('request_analisis')
def handle_analisis_request(data):
    """Handler untuk request analisis melalui WebSocket"""
    try:
        if not data or 'teks' not in data:
            emit('hasil_analisis', {'error': 'Teks tidak ditemukan dalam request'})
            return
        
        teks = data['teks']
        hasil = model.predict(teks)
        
        # Simpan hasil ke database
        simpan_hasil(teks, hasil)
        
        # Kirim hasil ke client yang meminta
        emit('hasil_analisis', hasil)
        
        # Update visualisasi untuk semua client
        statistik = dapatkan_statistik()
        visualisasi = buat_visualisasi_plotly(statistik)
        socketio.emit('update_visualisasi', visualisasi)
    except Exception as e:
        logger.error(f"Error saat memproses request analisis: {str(e)}")
        emit('hasil_analisis', {'error': str(e)})

# -------------- MAIN APPLICATION --------------

if __name__ == '__main__':
    try:
        # Path ke model tflite dan preprocessor
        MODEL_PATH = 'model/sentimen_model.tflite'
        VOCAB_PATH = 'model/preprocessor.joblib'  # Opsional
        
        # Inisialisasi database
        if not init_db():
            logger.error("Gagal menginisialisasi database. Aplikasi berhenti.")
            exit(1)
        
        # Load model
        try:
            model = SentimenModel(MODEL_PATH, VOCAB_PATH)
            logger.info("Model berhasil dimuat")
            
            # Verifikasi database
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sentimen_statistik")
                logger.info(f"Total data statistik: {cursor.fetchone()[0]}")
        
        except Exception as e:
            logger.error(f"Gagal memuat model: {str(e)}")
            exit(1)
        
        # Konfigurasi SocketIO
        socketio.run(app, 
                    host='0.0.0.0', 
                    port=5000, 
                    debug=True,
                    allow_unsafe_werkzeug=True,
                    use_reloader=False)  # Nonaktifkan reloader untuk menghindari locking
        
    except Exception as e:
        logger.critical(f"Error fatal: {str(e)}")
        exit(1)