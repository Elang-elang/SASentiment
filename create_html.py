teplates="""
<!DOCTYPE html>
<html>
<head>
    <title>Sistem Analisis Sentimen Real-time</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .dashboard {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 30px;
            margin-top: 20px;
        }
        
        .input-area {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 15px rgba(0,0,0,0.1);
        }
        
        textarea {
            width: 100%;
            height: 120px;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            resize: vertical;
        }
        
        button {
            padding: 12px 25px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
            margin-top: 15px;
        }
        
        button:hover {
            background: #45a049;
            transform: translateY(-2px);
            box-shadow: 0 3px 12px rgba(0,0,0,0.2);
        }
        
        .result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 8px;
            animation: fadeIn 0.5s ease;
        }
        
        .positif { 
            background: #e8f5e9; 
            border-left: 5px solid #4CAF50;
        }
        .netral { 
            background: #e3f2fd; 
            border-left: 5px solid #2196F3;
        }
        .negatif { 
            background: #ffebee; 
            border-left: 5px solid #f44336;
        }
        
        .stats-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .stat-box {
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .stat-box h4 {
            margin: 0 0 10px 0;
            color: #666;
        }
        
        .stat-box p {
            font-size: 24px;
            font-weight: bold;
            margin: 0;
        }
        
        .chart-container {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 15px rgba(0,0,0,0.1);
        }

        .positive-words {
            margin-top: 15px;
            padding: 10px;
            background: #f1f8e9;
            border-radius: 6px;
            border-left: 3px solid #8bc34a;
        }

        .positive-words span {
            display: inline-block;
            margin: 4px;
            padding: 4px 8px;
            background: #c5e1a5;
            border-radius: 4px;
            font-size: 14px;
        }

        .translation {
            color: #666;
            font-style: italic;
            font-size: 12px;
        }

        .loader {
            border: 4px solid #f3f3f3;
            border-radius: 50%;
            border-top: 4px solid #3498db;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-left: 10px;
            vertical-align: middle;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <h1 style="color: #333; text-align: center; margin-bottom: 30px;">📊 Dashboard Analisis Sentimen</h1>
    
    <div class="input-area">
        <h2 style="color: #444; margin-top: 0;">🔍 Analisis Teks</h2>
        <textarea 
            id="input-text" 
            placeholder="Ketik atau tempel teks yang ingin dianalisis di sini..."
        ></textarea>
        <button id="analyze-btn">
            🚀 Analisis Sekarang
        </button>
        <span id="loader" class="loader" style="display: none;"></span>
        <div id="result" class="result" style="display: none;">
            <p style="margin: 0;">
                <strong style="color: #666;">Sentimen:</strong> 
                <span id="sentiment-label" style="font-size: 18px;"></span>
            </p>
            <p style="margin: 10px 0 0 0;">
                <strong style="color: #666;">Skor Kepastian:</strong> 
                <span id="sentiment-score" style="font-weight: 600;"></span>
            </p>
            <div id="positive-words-container" class="positive-words" style="display: none;">
                <strong style="color: #558b2f;">Kata Positif Terdeteksi:</strong>
                <div id="positive-words"></div>
            </div>
        </div>
    </div>

    <div class="dashboard">
        <div>
            <div class="stats-container" id="today-stats">
                <!-- Statistik akan diisi oleh JavaScript -->
            </div>
            
            <div class="chart-container">
                <h3 style="margin-top: 0; color: #444;">📈 Distribusi Sentimen</h3>
                <div id="pie-chart" class="chart"></div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3 style="margin-top: 0; color: #444;">📅 Tren 30 Hari Terakhir</h3>
            <div id="line-chart" class="chart"></div>
        </div>
    </div>

    <script>
        // Inisialisasi variabel global
        let socket;
        let reconnectAttempts = 0;
        const MAX_RECONNECT_ATTEMPTS = 5;
        
        // Fungsi untuk inisialisasi koneksi Socket.IO dengan strategi reconnect
        function initSocketConnection() {
            try {
                socket = io();
                
                // Event handlers untuk socket
                socket.on('connect', function() {
                    console.log('Terhubung ke server Socket.IO');
                    reconnectAttempts = 0;
                    showAlert('🔌 Terhubung ke server', 'success');
                });
                
                socket.on('disconnect', function() {
                    console.log('Terputus dari server Socket.IO');
                    attemptReconnect();
                });
                
                socket.on('connect_error', function(err) {
                    console.error('Koneksi error:', err);
                    attemptReconnect();
                });
                
                // Handler untuk hasil analisis dari server
                socket.on('hasil_analisis', handleAnalysisResult);
                
                // Handler untuk update visualisasi
                socket.on('update_visualisasi', handleVisualizationUpdate);
                
                return true;
            } catch (err) {
                console.error('Gagal inisialisasi socket:', err);
                return false;
            }
        }
        
        // Fungsi untuk mencoba koneksi ulang
        function attemptReconnect() {
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                console.log(`Mencoba koneksi ulang... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
                
                setTimeout(() => {
                    if (!socket || !socket.connected) {
                        initSocketConnection();
                    }
                }, 2000 * reconnectAttempts); // Backoff eksponensial
            } else {
                showAlert('⚠️ Gagal terhubung ke server. Coba muat ulang halaman.', 'error');
            }
        }
        
        // Inisialisasi koneksi saat halaman dimuat
        document.addEventListener('DOMContentLoaded', function() {
            if (!initSocketConnection()) {
                showAlert('⚠️ Gagal terhubung ke server analisis sentimen', 'error');
            }
            
            // Setup event listener untuk form analisis
            setupAnalysisForm();
        });
        
        // Setup form analisis
        function setupAnalysisForm() {
            const analyzeBtn = document.getElementById('analyze-btn');
            const inputText = document.getElementById('input-text');
            const loader = document.getElementById('loader');
            
            // Handle submit dengan klik tombol
            analyzeBtn.addEventListener('click', function() {
                submitAnalysisRequest();
            });
            
            // Handle submit dengan Enter (shift+enter untuk line break)
            inputText.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    submitAnalysisRequest();
                }
            });
        }
        
        // Fungsi untuk submit request analisis
        function submitAnalysisRequest() {
            const text = document.getElementById('input-text').value.trim();
            
            if (!text) {
                showAlert('⚠️ Mohon masukkan teks terlebih dahulu!', 'warning');
                return;
            }
            
            if (text.length > 1000) {
                showAlert('⛔ Teks terlalu panjang! Maksimal 1000 karakter.', 'error');
                return;
            }
            
            // Tampilkan loader
            document.getElementById('loader').style.display = 'inline-block';
            document.getElementById('result').style.display = 'none';
            
            // Kirim request ke server jika socket terhubung
            if (socket && socket.connected) {
                socket.emit('request_analisis', { teks: text });
            } else {
                // Fallback ke REST API jika socket tidak terhubung
                fetch('/api/sentimen', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ teks: text })
                })
                .then(response => response.json())
                .then(data => {
                    // Format data sesuai dengan hasil socket untuk kompatibilitas
                    const formattedData = {
                        label: data.sentimen.label,
                        skor: data.sentimen.skor,
                        positive_words: data.kata_positif || [],
                        translations: data.terjemahan || []
                    };
                    handleAnalysisResult(formattedData);
                    
                    // Jika ada statistik dalam respon, update visualisasi
                    if (data.statistik) {
                        updateVisualizationFromStats(data.statistik);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert('⛔ Terjadi kesalahan saat memproses teks', 'error');
                    document.getElementById('loader').style.display = 'none';
                });
            }
        }
        
        // Handler hasil analisis
        function handleAnalysisResult(data) {
            // Sembunyikan loader
            document.getElementById('loader').style.display = 'none';
            
            const resultDiv = document.getElementById('result');
            const positiveWordsContainer = document.getElementById('positive-words-container');
            const positiveWordsDiv = document.getElementById('positive-words');
            
            // Jika terjadi error
            if (data.error) {
                showAlert(`⛔ Error: ${data.error}`, 'error');
                return;
            }
            
            resultDiv.style.display = 'block';
            
            // Reset kelas dan animasi
            resultDiv.className = 'result';
            resultDiv.style.animation = 'none';
            void resultDiv.offsetWidth; // Trigger reflow
            resultDiv.style.animation = 'fadeIn 0.5s ease';
            
            if (data.label) {
                // Update label dan skor
                resultDiv.classList.add(data.label.toLowerCase());
                document.getElementById('sentiment-label').textContent = data.label.toUpperCase();
                document.getElementById('sentiment-score').textContent = (data.skor * 100).toFixed(2) + '%';
                
                // Warna berdasarkan sentimen
                const colors = {
                    positif: '#4CAF50',
                    netral: '#2196F3',
                    negatif: '#f44336'
                };
                document.getElementById('sentiment-label').style.color = colors[data.label.toLowerCase()];
                
                // Tampilkan kata positif jika ada
                if (data.positive_words && data.positive_words.length > 0) {
                    positiveWordsContainer.style.display = 'block';
                    positiveWordsDiv.innerHTML = '';
                    
                    data.positive_words.forEach((word, index) => {
                        const translation = data.translations && data.translations[index] ? data.translations[index] : '';
                        
                        const wordSpan = document.createElement('span');
                        wordSpan.textContent = word;
                        
                        if (translation && translation !== word) {
                            const translationSpan = document.createElement('span');
                            translationSpan.className = 'translation';
                            translationSpan.textContent = ` (${translation})`;
                            wordSpan.appendChild(translationSpan);
                        }
                        
                        positiveWordsDiv.appendChild(wordSpan);
                    });
                } else {
                    positiveWordsContainer.style.display = 'none';
                }
            }
        }
        
        // Handler update visualisasi
        function handleVisualizationUpdate(data) {
            try {
                // Update line chart
                if (data.line_chart) {
                    Plotly.newPlot('line-chart', data.line_chart.data, {
                        ...data.line_chart.layout,
                        height: 400,
                        margin: { t: 40, b: 80, l: 60, r: 40 },
                        xaxis: { tickangle: -45 },
                        transition: { duration: 500 },
                        responsive: true
                    });
                }
                
                // Update pie chart
                if (data.pie_chart) {
                    Plotly.newPlot('pie-chart', [{
                        ...data.pie_chart.data[0],
                        hole: 0.4,
                        marker: {
                            colors: ['#4CAF50', '#2196F3', '#f44336'],
                            line: { color: '#fff', width: 2 }
                        },
                        textinfo: 'percent+label'
                    }], {
                        ...data.pie_chart.layout,
                        height: 400,
                        margin: { t: 40, b: 20, l: 20, r: 20 },
                        showlegend: false,
                        responsive: true
                    });
                }
                
                // Update statistik hari ini dari data terbaru
                if (data.line_chart && data.line_chart.data && data.line_chart.data.length > 0) {
                    const latestData = data.line_chart.data[0].y.slice(-1)[0];
                    updateTodayStats(latestData);
                } else if (data.latest_stats) {
                    // Alternatif jika format berbeda
                    updateTodayStatsFromObject(data.latest_stats);
                }
            } catch (err) {
                console.error('Error updating visualization:', err);
            }
        }
        
        // Update statistik hari ini dari array
        function updateTodayStats(latestData) {
            try {
                const statsContainer = document.getElementById('today-stats');
                statsContainer.innerHTML = `
                    <div class="stat-box">
                        <h4>😊 Positif</h4>
                        <p style="color: #4CAF50;">${latestData[0] || 0}</p>
                    </div>
                    <div class="stat-box">
                        <h4>😐 Netral</h4>
                        <p style="color: #2196F3;">${latestData[1] || 0}</p>
                    </div>
                    <div class="stat-box">
                        <h4>😠 Negatif</h4>
                        <p style="color: #f44336;">${latestData[2] || 0}</p>
                    </div>
                `;
            } catch (err) {
                console.error('Error updating stats:', err);
            }
        }
        
        // Update statistik hari ini dari objek
        function updateTodayStatsFromObject(stats) {
            try {
                const statsContainer = document.getElementById('today-stats');
                statsContainer.innerHTML = `
                    <div class="stat-box">
                        <h4>😊 Positif</h4>
                        <p style="color: #4CAF50;">${stats.positif || 0}</p>
                    </div>
                    <div class="stat-box">
                        <h4>😐 Netral</h4>
                        <p style="color: #2196F3;">${stats.netral || 0}</p>
                    </div>
                    <div class="stat-box">
                        <h4>😠 Negatif</h4>
                        <p style="color: #f44336;">${stats.negatif || 0}</p>
                    </div>
                `;
            } catch (err) {
                console.error('Error updating stats from object:', err);
            }
        }
        
        // Fungsi untuk update visualisasi dari statistik API
        function updateVisualizationFromStats(statistikData) {
            try {
                // Format data untuk line chart
                const tanggal = statistikData.map(item => item.tanggal);
                const positifData = statistikData.map(item => item.positif);
                const netralData = statistikData.map(item => item.netral);
                const negatifData = statistikData.map(item => item.negatif);
                
                // Balik urutan untuk menampilkan dari tanggal terlama ke terbaru
                tanggal.reverse();
                positifData.reverse();
                netralData.reverse();
                negatifData.reverse();
                
                // Buat traces untuk line chart
                const lineData = [
                    {
                        x: tanggal,
                        y: positifData,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Positif',
                        line: {color: '#4CAF50', width: 2},
                        marker: {symbol: 'circle', size: 8}
                    },
                    {
                        x: tanggal,
                        y: netralData,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Netral',
                        line: {color: '#2196F3', width: 2},
                        marker: {symbol: 'square', size: 8}
                    },
                    {
                        x: tanggal,
                        y: negatifData,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Negatif',
                        line: {color: '#f44336', width: 2},
                        marker: {symbol: 'x', size: 8}
                    }
                ];
                
                // Total untuk pie chart
                const totalPositif = positifData.reduce((sum, val) => sum + val, 0);
                const totalNetral = netralData.reduce((sum, val) => sum + val, 0);
                const totalNegatif = negatifData.reduce((sum, val) => sum + val, 0);
                
                const pieData = [{
                    values: [totalPositif, totalNetral, totalNegatif],
                    labels: ['Positif', 'Netral', 'Negatif'],
                    type: 'pie',
                    hole: 0.4,
                    marker: {
                        colors: ['#4CAF50', '#2196F3', '#f44336'],
                        line: {color: '#fff', width: 2}
                    },
                    textinfo: 'percent+label'
                }];
                
                // Update charts
                Plotly.newPlot('line-chart', lineData, {
                    title: 'Tren Sentimen',
                    height: 400,
                    margin: { t: 40, b: 80, l: 60, r: 40 },
                    xaxis: { title: 'Tanggal', tickangle: -45 },
                    yaxis: { title: 'Jumlah' },
                    legend: { orientation: 'h', y: 1.1 },
                    responsive: true
                });
                
                Plotly.newPlot('pie-chart', pieData, {
                    title: 'Distribusi Sentimen',
                    height: 400,
                    margin: { t: 40, b: 20, l: 20, r: 20 },
                    showlegend: false,
                    responsive: true
                });
                
                // Update statistik hari ini
                const latestPositif = positifData[positifData.length - 1] || 0;
                const latestNetral = netralData[netralData.length - 1] || 0;
                const latestNegatif = negatifData[negatifData.length - 1] || 0;
                
                updateTodayStatsFromObject({
                    positif: latestPositif,
                    netral: latestNetral,
                    negatif: latestNegatif
                });
                
            } catch (err) {
                console.error('Error updating visualization from stats:', err);
            }
        }

        // Fungsi tampilkan alert
        function showAlert(message, type) {
            // Hapus alert lama jika ada
            const existingAlerts = document.querySelectorAll('.alert-box');
            existingAlerts.forEach(alert => {
                alert.remove();
            });
            
            const alertBox = document.createElement('div');
            alertBox.className = 'alert-box';
            
            // Set style berdasarkan tipe
            const bgColor = type === 'error' ? '#f44336' : 
                           type === 'warning' ? '#ff9800' : 
                           type === 'success' ? '#4caf50' : '#2196f3';
            
            alertBox.style = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 25px;
                border-radius: 8px;
                color: white;
                background: ${bgColor};
                box-shadow: 0 3px 15px rgba(0,0,0,0.2);
                animation: fadeIn 0.3s ease;
                z-index: 1000;
            `;
            alertBox.textContent = message;
            
            document.body.appendChild(alertBox);
            setTimeout(() => {
                alertBox.style.animation = 'fadeOut 0.5s ease forwards';
                setTimeout(() => {
                    alertBox.remove();
                }, 500);
            }, 3000);
        }

        // Tambahkan animasi fadeOut
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeOut {
                from { opacity: 1; transform: translateY(0); }
                to { opacity: 0; transform: translateY(-20px); }
            }
        `;
        document.head.appendChild(style);

        // Resize handler untuk responsivitas grafik
        window.addEventListener('resize', function() {
            Plotly.Plots.resize('line-chart');
            Plotly.Plots.resize('pie-chart');
        });
    </script>
</body>
</html>
"""
import os
os.makedirs("templates")
with open("templates/index.html", "w") as f
    f.write(templates)
