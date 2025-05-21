import os
import json
import logging
from collections import Counter
from flask import request, session
from src.data import load_query_data
from src.plots import plot_pie, plot_stacked_bar

# Global sort variables (managed externally)
sort_column = None
sort_reverse = False

def setup_logging(app):
    """Configure logging for the application."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    app.logger.setLevel(logging.INFO)

def ensure_folders_exist(app):
    """Create necessary folders if they don't exist."""
    for folder in [app.config['DATA_FOLDER'], app.config['MODIFIED_FOLDER'], app.config['ADDED_FOLDER']]:
        os.makedirs(folder, exist_ok=True)

def get_tsv_files(app):
    """Return list of .tsv files in the data folder."""
    return [f for f in os.listdir(app.config['DATA_FOLDER']) if f.endswith('.tsv')]

def load_file(filepath, app):
    """Load data from a TSV file and return it."""
    try:
        loaded_data = load_query_data(filepath)
        app.logger.info(f"Loaded {len(loaded_data)} data points")
        if loaded_data:
            app.logger.debug(f"Sample metadata: {[item.metadata for item in loaded_data[:3]]}")
        return loaded_data
    except Exception as e:
        app.logger.error(f"Error loading file: {str(e)}")
        raise

def reset_session_and_globals():
    """Reset session and global sort variables when loading a new file."""
    global sort_column, sort_reverse
    session['data_loaded'] = True
    session['has_added_data'] = False
    sort_column = None
    sort_reverse = False

def get_search_params():
    """Extract search parameters from request arguments."""
    return {
        'question_intent': request.args.get('question_intent', '').strip().lower(),
        'sub_intent': request.args.get('sub_intent', '').strip().lower(),
        'segment': request.args.get('segment', '').strip().lower()
    }

def filter_data(data, search_params, app):
    """Filter data based on search parameters."""
    return [
        item for item in data
        if (not search_params['question_intent'] or
            search_params['question_intent'] in str(item.metadata.get('question_intent', 'Unknown')).strip().lower())
        and (not search_params['sub_intent'] or
             search_params['sub_intent'] in str(item.metadata.get('sub_intent', 'Unknown')).strip().lower())
        and (not search_params['segment'] or
             search_params['segment'] in str(item.metadata.get('segment', 'Unknown')).strip().lower())
    ]

def sort_data(filtered_data, column, app):
    """Sort filtered data by specified column."""
    global sort_column, sort_reverse
    if column not in ['Question Intent', 'Sub Intent']:
        return filtered_data
    
    app.logger.info(f"Sorting by {column}, reverse={sort_reverse}")
    if sort_column == column:
        sort_reverse = not sort_reverse
    else:
        sort_column = column
        sort_reverse = False
    
    key_map = {
        'Question Intent': lambda x: str(x.metadata.get('question_intent', 'Unknown')).lower(),
        'Sub Intent': lambda x: str(x.metadata.get('sub_intent', 'Unknown')).lower()
    }
    filtered_data.sort(key=key_map[column], reverse=sort_reverse)
    return filtered_data

def prepare_table_data(filtered_data):
    """Prepare data for table rendering."""
    return [
        {
            'index': idx,
            'text': item.query[0].get('text', 'No text available'),
            'segment': str(item.metadata.get('segment', 'Unknown')),
            'question_intent': str(item.metadata.get('question_intent', 'Unknown')),
            'sub_intent': str(item.metadata.get('sub_intent', 'Unknown'))
        }
        for idx, item in enumerate(filtered_data)
    ]

def get_sort_indicators():
    """Return sort indicators for table headers."""
    return {
        'Question Intent': ' ▲' if sort_column == 'Question Intent' and not sort_reverse else ' ▼' if sort_column == 'Question Intent' else '',
        'Sub Intent': ' ▲' if sort_column == 'Sub Intent' and not sort_reverse else ' ▼' if sort_column == 'Sub Intent' else ''
    }

def generate_charts(data, app):
    """Generate JSON data for Chart.js pie and stacked bar charts."""
    segment_counter = Counter(item.metadata['segment'] for item in data)
    app.logger.info("Generating segment pie chart data")
    pie_chart = plot_pie(segment_counter)
    app.logger.info("Generating stacked bar chart data")
    bar_chart = plot_stacked_bar(data)
    return json.dumps(pie_chart), json.dumps(bar_chart)

def process_form_fields(fields, prefix):
    """Process form fields into a dictionary, handling JSON parsing."""
    result = {}
    for field in fields:
        value = request.form.get(f'{prefix}_{field}', '').strip()
        try:
            result[field] = json.loads(value) if value else ''
        except json.JSONDecodeError:
            result[field] = value
    return result

def save_data_to_file(filepath, data_to_save):
    """Save data to a TSV file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for dp in data_to_save:
            query_json = json.dumps(dp.query, ensure_ascii=False)
            metadata_json = json.dumps(dp.metadata, ensure_ascii=False)
            f.write(f"{query_json}\t{metadata_json}\n")

def append_data_to_file(filepath, data_point):
    """Append a single data point to a TSV file."""
    with open(filepath, 'a', encoding='utf-8') as f:
        query_json = json.dumps(data_point.query, ensure_ascii=False)
        metadata_json = json.dumps(dp.metadata, ensure_ascii=False)
        f.write(f"{query_json}\t{metadata_json}\n")

def get_file_paths(original_name, folder_key, app):
    """Generate file paths and names for saving or downloading."""
    filename = f"{original_name}_added.tsv" if folder_key == 'ADDED_FOLDER' else f"{original_name}_modified.tsv"
    filepath = os.path.join(app.config[folder_key], filename)
    return filename, filepath
