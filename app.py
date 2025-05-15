import os
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
import json
from src.data import load_query_set

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for flash messages
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory storage for data (for simplicity; use a database for production)
data = []
sort_column = None
sort_reverse = False

# UI configuration constants
PLOT_FIGSIZE = (15, 6)
PLOT_WSPACE = 0.4
PLOT_BOTTOM_MARGIN = 0.3

def plot_pie(counts):
    """Create a pie chart and return as base64-encoded image."""
    fig, ax = plt.subplots(figsize=(7.5, 6))
    labels = list(counts.keys())
    sizes = list(counts.values())
    total = sum(sizes)
    colors = plt.cm.Paired(range(len(labels)))
    explode = [0.1] * len(labels)
    wedges, _, autotexts = ax.pie(
        sizes, explode=explode, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=140, textprops={'fontsize': 10}
    )
    ax.set_title("Segment Distribution")
    ax.axis('equal')
    legend_labels = [f"{label} ({(count/total)*100:.1f}%)" for label, count in counts.items()]
    ax.legend(wedges, legend_labels, title="Categories", loc="upper center",
              bbox_to_anchor=(0.5, -0.1), ncol=2)
    
    # Save to BytesIO and encode as base64
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return img_base64

def plot_stacked_bar():
    """Plot stacked bar chart and return as base64-encoded image."""
    fig, ax = plt.subplots(figsize=(7.5, 6))
    
    # Collect question_intent and sub_intent data
    intent_subintent_map = {}
    for item in data:
        q_intent = item.metadata.get('question_intent', 'Unknown')
        sub_intent = item.metadata.get('sub_intent', 'Unknown')
        if q_intent not in intent_subintent_map:
            intent_subintent_map[q_intent] = Counter()
        intent_subintent_map[q_intent][sub_intent] += 1

    # Prepare data for plotting
    question_intents = sorted(intent_subintent_map.keys())
    all_sub_intents = sorted(set(sub_intent for counter in intent_subintent_map.values() for sub_intent in counter))
    plot_data = np.zeros((len(all_sub_intents), len(question_intents)))

    for i, sub_intent in enumerate(all_sub_intents):
        for j, q_intent in enumerate(question_intents):
            plot_data[i, j] = intent_subintent_map[q_intent].get(sub_intent, 0)

    # Plot stacked bars
    bottom = np.zeros(len(question_intents))
    colors = plt.cm.Paired(np.linspace(0, 1, len(all_sub_intents)))
    max_height = np.max(bottom + np.sum(plot_data, axis=0))
    labeled_sub_intents = set()
    patches = []

    for i, sub_intent in enumerate(all_sub_intents):
        bars = ax.bar(question_intents, plot_data[i], bottom=bottom, color=colors[i])
        patches.append(bars[0])
        for j, bar in enumerate(bars):
            height = plot_data[i, j]
            if height > 0.05 * max_height:
                x = bar.get_x() + bar.get_width() / 2
                y = bottom[j] + height / 2
                ax.text(x, y, sub_intent, ha='center', va='center', fontsize=8, color='white',
                        bbox=dict(facecolor='black', alpha=0.5, pad=1))
                labeled_sub_intents.add(sub_intent)
        bottom += plot_data[i]

    # Add legend for unlabeled sub_intents on the right
    unlabeled_sub_intents = [sub_intent for sub_intent in all_sub_intents if sub_intent not in labeled_sub_intents]
    if unlabeled_sub_intents:
        unlabeled_patches = [p for p, sub_intent in zip(patches, all_sub_intents) if sub_intent in unlabeled_sub_intents]
        ax.legend(unlabeled_patches, unlabeled_sub_intents, title="Unlabeled Sub-Intents",
                  loc="center left", bbox_to_anchor=(1.0, 0.5), ncol=1, fontsize=8)

    # Customize plot
    ax.set_title("Sub-Intent Distribution by Question Intent")
    ax.set_xlabel("Question Intent")
    ax.set_ylabel("Count")
    ax.tick_params(axis='x', rotation=45)
    
    # Save to BytesIO and encode as base64
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return img_base64

@app.route('/', methods=['GET', 'POST'])
def index():
    global data
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.tsv'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            try:
                data = load_query_set(filepath)
                flash('File uploaded successfully!', 'success')
            except Exception as e:
                flash(f'Failed to load file: {str(e)}', 'error')
            os.remove(filepath)  # Clean up
        else:
            flash('Please upload a valid .tsv file', 'error')
        return redirect(url_for('index'))
    
    return render_template('index.html')

@app.route('/data')
def data_table():
    global data, sort_column, sort_reverse
    column = request.args.get('sort')
    if column in ['Question Intent', 'Sub Intent']:
        if sort_column == column:
            sort_reverse = not sort_reverse
        else:
            sort_column = column
            sort_reverse = False
        
        key_map = {
            'Question Intent': lambda x: x.metadata.get('question_intent', 'Unknown').lower(),
            'Sub Intent': lambda x: x.metadata.get('sub_intent', 'Unknown').lower()
        }
        data.sort(key=key_map[column], reverse=sort_reverse)
    
    table_data = [
        {
            'index': idx,
            'text': item.query[0].get('text', 'No text available'),
            'segment': item.metadata.get('segment', 'Unknown'),
            'question_intent': item.metadata.get('question_intent', 'Unknown'),
            'sub_intent': item.metadata.get('sub_intent', 'Unknown')
        }
        for idx, item in enumerate(data)
    ]
    
    sort_indicators = {
        'Question Intent': ' ▲' if sort_column == 'Question Intent' and not sort_reverse else ' ▼' if sort_column == 'Question Intent' else '',
        'Sub Intent': ' ▲' if sort_column == 'Sub Intent' and not sort_reverse else ' ▼' if sort_column == 'Sub Intent' else ''
    }
    
    return render_template('data.html', data=table_data, sort_indicators=sort_indicators)

@app.route('/charts')
def charts():
    if not data:
        return render_template('charts.html', error="No data available")
    
    # Generate pie chart
    segment_counter = Counter(item.metadata['segment'] for item in data)
    pie_chart = plot_pie(segment_counter)
    
    # Generate stacked bar chart
    bar_chart = plot_stacked_bar()
    
    return render_template('charts.html', pie_chart=pie_chart, bar_chart=bar_chart)

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def edit(index):
    if index >= len(data):
        flash('Invalid data point', 'error')
        return redirect(url_for('data_table'))
    
    data_point = data[index]
    query_fields = sorted(data_point.query[0].keys()) if data_point.query else []
    metadata_fields = sorted(data_point.metadata.keys())
    
    if request.method == 'POST':
        try:
            new_query = {}
            for field in query_fields:
                value = request.form.get(f'query_{field}', '').strip()
                try:
                    new_query[field] = json.loads(value) if value else ''
                except json.JSONDecodeError:
                    new_query[field] = value
            data_point.query[0] = new_query
            
            new_metadata = {}
            for field in metadata_fields:
                value = request.form.get(f'metadata_{field}', '').strip()
                try:
                    new_metadata[field] = json.loads(value) if value else ''
                except json.JSONDecodeError:
                    new_metadata[field] = value
            data_point.metadata = new_metadata
            
            # Save to temporary file
            with open(os.path.join(app.config['UPLOAD_FOLDER'], 'temp.tsv'), 'w', encoding='utf-8') as f:
                for dp in data:
                    query_json = json.dumps(dp.query, ensure_ascii=False)
                    metadata_json = json.dumps(dp.metadata, ensure_ascii=False)
                    f.write(f"{query_json}\t{metadata_json}\n")
            
            flash('Changes saved!', 'success')
            return redirect(url_for('data_table'))
        except Exception as e:
            flash(f'Failed to save changes: {str(e)}', 'error')
    
    query_data = {k: json.dumps(v, indent=2) if isinstance(v, (dict, list)) else str(v) for k, v in data_point.query[0].items()}
    metadata_data = {k: json.dumps(v, indent=2) if isinstance(v, (dict, list)) else str(v) for k, v in data_point.metadata.items()}
    
    return render_template('edit.html', index=index, query_fields=query_fields, metadata_fields=metadata_fields,
                          query_data=query_data, metadata_data=metadata_data)

@app.route('/download')
def download():
    if not data:
        flash('No data to download', 'error')
        return redirect(url_for('index'))
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'query_set_modified.tsv')
    with open(filepath, 'w', encoding='utf-8') as f:
        for dp in data:
            query_json = json.dumps(dp.query, ensure_ascii=False)
            metadata_json = json.dumps(dp.metadata, ensure_ascii=False)
            f.write(f"{query_json}\t{metadata_json}\n")
    
    return send_file(filepath, as_attachment=True, download_name='query_set_modified.tsv')

if __name__ == '__main__':
    app.run(debug=True)