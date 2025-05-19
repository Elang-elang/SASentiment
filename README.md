# Sentiment Analysis System: Multilingual Text Classifier

## What is the Sentiment Analysis System?

The Sentiment Analysis System is an advanced Flask-based web application that performs real-time sentiment classification on text input in multiple languages. It combines machine learning models with lexicon-based analysis to determine whether text expresses positive, negative, or neutral sentiment.

## Key Features

- **Multilingual Support**: Analyzes text in various languages with automatic translation
- **Hybrid Analysis**: Combines machine learning (TensorFlow Lite) with lexicon-based approaches
- **Profanity Detection**: Identifies and handles inappropriate language
- **Real-time Visualization**: Interactive charts showing sentiment trends
- **Database Integration**: Stores results in SQLite for historical analysis
- **WebSocket Support**: Live updates for connected clients

## How It Works

1. **Text Processing**:
   - Detects input language and translates to English (if needed)
   - Checks for profanity using custom word lists
   - Normalizes text for analysis

2. **Sentiment Analysis**:
   - Uses a pre-trained TensorFlow Lite model for primary classification
   - Augments with lexicon-based scoring (positive/negative word matching)
   - Combines results for final sentiment determination

3. **Result Handling**:
   - Stores analysis in SQLite database
   - Generates visualizations of sentiment trends
   - Provides API and WebSocket interfaces

## System Components

| Component | Purpose |
|-----------|---------|
| `app.py` | Main application with Flask routes and WebSocket handlers |
| `load_models.py` | Downloads the pre-trained TensorFlow model |
| `create_html.py` | Create directory `templates` and create index.html for template |
| `positive_words.csv` | Custom lexicon of positive sentiment words |
| `negative_words.csv` | Custom lexicon of negative sentiment words |

## Example Usage

1. **Create templates**:
   ```bash
   python create_html.py
   ```

2. **Run the application**:
   ```bash
   python app.py
   ```

3. **Access the web interface** at `http://localhost:5000`

4. **Submit text** for analysis through:
   - Web form
   - REST API (`POST /api/sentimen`)
   - WebSocket (`request_analisis` event)

5. **View results** including:
   - Sentiment label (positive/negative/neutral)
   - Confidence score
   - Positive words detected
   - Translations of positive words
   - Historical sentiment trends

## Technical Implementation Highlights

### Hybrid Analysis Engine
```python
def predict(self, text):
    # Lexicon analysis first
    lexicon_result = self.analyze_sentiment_lexicon(text)
    
    # Then machine learning prediction
    inputs = self.preprocess_text(text)
    self.interpreter.set_tensor(input_details['index'], inputs)
    self.interpreter.invoke()
    output = self.interpreter.get_tensor(output_details[0]['index'])
    
    # Combine results intelligently
    if model_label == lexicon_result['label']:
        final_score = max(model_score, lexicon_result['skor'])
    else:
        final_score = model_score if model_score > lexicon_result['skor'] else lexicon_result['skor']
```

### Real-time Visualization
```python
def buat_visualisasi_plotly(statistik):
    # Create interactive line chart
    trace_positif = go.Scatter(x=tanggal, y=positif_counts, name='Positive')
    trace_negatif = go.Scatter(x=tanggal, y=negatif_counts, name='Negative')
    
    # Create pie chart
    pie_chart = go.Pie(labels=['Positive','Neutral','Negative'], values=counts)
    
    return {
        'line_chart': line_fig.to_json(),
        'pie_chart': pie_fig.to_json()
    }
```
## Requirements
- Directory clone
```bash
apt-get install git
git clone https://github.com/Elang-elang/SASentiment.git
```
- Python 3.7+
```bash
apt-get install python
```
- Flask
- Flask-SocketIO
- TensorFlow Lite
- pandas
- plotly
- APSW (for SQLite)
- TextBlob
- googletrans

Install with:
```bash
pip install flask flask-socketio tflite-runtime pandas plotly apsw textblob googletrans
```

## Future Enhancements

- Add user authentication
- Support for batch processing
- Enhanced visualization dashboard
- Sentiment analysis by topic/category
- Mobile app integration
- Custom model training interface
