import json
import os
import shutil
import logging
from flask import Flask, request, render_template, redirect, url_for, flash, send_file, session, g
from src.data import QueryData
from src.utils import (
    ensure_folders_exist, load_file, reset_session_and_globals,
    get_search_params, filter_data, sort_data, prepare_table_data, get_sort_indicators,
    generate_charts, process_form_fields, save_data_to_file, append_data_to_file, get_file_paths
)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'replace_with_strong_random_key_in_production')
app.config['DATA_FOLDER'] = 'data'
app.config['MODIFIED_FOLDER'] = 'modified'
app.config['ADDED_FOLDER'] = 'added'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

def setup_logging():
    """Configure logging with file and console handlers."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
    app.logger.setLevel(logging.INFO)

def custom_json_dumps(obj):
    """Custom JSON serializer for QueryData objects."""
    def default_serializer(o):
        if isinstance(o, QueryData):
            return o.to_dict()
        raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")
    return json.dumps(obj, default=default_serializer, ensure_ascii=False)

def get_session_id():
    """Get or generate a unique session ID."""
    if 'sid' not in session:
        session['sid'] = os.urandom(16).hex()
    return session['sid']

def cleanup_session_files(session_id):
    """Delete temporary files for the given session ID."""
    if session_id:
        for folder in [app.config['DATA_FOLDER'], app.config['MODIFIED_FOLDER'], app.config['ADDED_FOLDER']]:
            user_folder = os.path.join(folder, session_id)
            if os.path.exists(user_folder):
                shutil.rmtree(user_folder)

@app.teardown_appcontext
def cleanup_on_shutdown(exception=None):
    """Clean up session files on app shutdown or session expiry."""
    session_id = g.get('session_id')
    if session_id:
        cleanup_session_files(session_id)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle file upload and loading."""
    setup_logging()
    
    session_id = get_session_id()
    user_data_folder = os.path.normpath(os.path.join(app.config['DATA_FOLDER'], session_id))
    user_modified_folder = os.path.normpath(os.path.join(app.config['MODIFIED_FOLDER'], session_id))
    user_added_folder = os.path.normpath(os.path.join(app.config['ADDED_FOLDER'], session_id))
    ensure_folders_exist(app, folders=[user_data_folder, user_modified_folder, user_added_folder])
    g.session_id = session_id
    
    if request.method == 'POST':
        cleanup_session_files(session_id)
        session.pop('data', None)
        session.pop('selected_file_name', None)
        session.pop('data_loaded', None)
        session.pop('has_added_data', None)
        session.pop('sort_column', None)
        session.pop('sort_reverse', None)
        
        if 'tsv_file' not in request.files:
            app.logger.warning("No file uploaded")
            flash('Please upload a .tsv file', 'error')
            return render_template('index.html', data_loaded=session.get('data_loaded', False))
        
        file = request.files['tsv_file']
        if file.filename == '':
            app.logger.warning("No file selected")
            flash('Please upload a .tsv file', 'error')
            return render_template('index.html', data_loaded=session.get('data_loaded', False))
        
        if not file.filename.lower().endswith('.tsv'):
            app.logger.warning(f"Invalid file type: {file.filename}")
            flash('Only .tsv files are allowed', 'error')
            return render_template('index.html', data_loaded=session.get('data_loaded', False))
        
        filename = ''.join(c for c in file.filename if c.isalnum() or c in ('.', '_', '-'))
        filepath = os.path.normpath(os.path.join(user_data_folder, filename))
        
        app.logger.info(f"Attempting to save uploaded file for session {session_id}: {filepath}")
        try:
            os.makedirs(user_data_folder, exist_ok=True)
            file.save(filepath)
            if not os.path.exists(filepath):
                app.logger.error(f"File save failed: {filepath} does not exist")
                raise OSError(f"Failed to save file: {filepath}")
            app.logger.info(f"File saved successfully: {filepath}")
            session['data'] = [d.to_dict() for d in load_file(filepath, app)]
            reset_session_and_globals()
            session['selected_file_name'] = filename
            flash('File uploaded and loaded successfully!', 'success')
            return redirect(url_for('data_table'))
        except Exception as e:
            session['data_loaded'] = False
            app.logger.error(f"Failed to process file: {str(e)}")
            flash(f'Failed to load file: {str(e)}', 'error')
            return render_template('index.html', data_loaded=session.get('data_loaded', False))
    
    app.logger.debug("Rendering index page")
    return render_template('index.html', data_loaded=session.get('data_loaded', False))

@app.route('/data')
def data_table():
    """Display filtered and sorted data table."""
    data = [QueryData.from_dict(d) for d in session.get('data', [])]
    if not data:
        app.logger.warning("No data loaded for data table")
        return redirect(url_for('index'))
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
    except ValueError:
        page = 1
        per_page = 10
    if per_page not in [10, 25, 50]:
        per_page = 10
    
    search_params = get_search_params()
    filtered_data = filter_data(data, search_params, app)
    
    app.logger.info(f"Search terms: question_intent='{search_params['question_intent']}', "
                   f"sub_intent='{search_params['sub_intent']}', segment='{search_params['segment']}'")
    app.logger.info(f"Filtered {len(filtered_data)} of {len(data)} rows")
    if not filtered_data and data:
        app.logger.debug(f"Sample metadata (first 3 rows): {[item.metadata for item in data[:3]]}")
    
    column = request.args.get('sort')
    filtered_data = sort_data(filtered_data, column, app)
    
    total_rows = len(filtered_data)
    total_pages = (total_rows + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_rows)
    
    paginated_data = filtered_data[start_idx:end_idx]
    
    table_data = prepare_table_data(paginated_data, start_idx)
    sort_indicators = get_sort_indicators()
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_rows': total_rows,
        'start_row': start_idx + 1,
        'end_row': end_idx
    }
    
    app.logger.debug("Rendering data table page")
    return render_template(
        'data.html',
        data=table_data,
        sort_indicators=sort_indicators,
        search_params=search_params,
        total_rows=len(data),
        filtered_rows=len(filtered_data),
        pagination=pagination
    )

@app.route('/charts')
def charts():
    """Render charts page with pie and stacked bar charts."""
    data = [QueryData.from_dict(d) for d in session.get('data', [])]
    if not data:
        app.logger.warning("No data available for charts")
        return render_template('charts.html', error="No data available")
    
    pie_chart, bar_chart = generate_charts(data, app)
    app.logger.debug("Rendering charts page")
    return render_template(
        'charts.html',
        pie_chart=pie_chart,
        bar_chart=bar_chart
    )

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def edit(index):
    """Handle editing of a data point."""
    data = [QueryData.from_dict(d) for d in session.get('data', [])]
    if index >= len(data):
        app.logger.error(f"Invalid data point index: {index}")
        flash('Invalid data point', 'error')
        return redirect(url_for('data_table'))
    
    data_point = data[index]
    query_fields = sorted(data_point.query[0].keys()) if data_point.query else []
    metadata_fields = sorted(data_point.metadata.keys())
    
    if request.method == 'POST':
        try:
            data_point.query[0] = process_form_fields(query_fields, 'query')
            data_point.metadata = process_form_fields(metadata_fields, 'metadata')
            
            session['data'] = [d.to_dict() for d in data]
            app.logger.info(f"Data point {index} updated successfully for session {get_session_id()}")
            flash('Changes saved!', 'success')
            return redirect(url_for('data_table'))
        except Exception as e:
            app.logger.error(f"Failed to save changes: {str(e)}")
            flash(f'Failed to save changes: {str(e)}', 'error')
    
    query_data = {k: json.dumps(v, indent=2) if isinstance(v, (dict, list)) else str(v) for k, v in data_point.query[0].items()} if data_point.query else {}
    metadata_data = {k: json.dumps(v, indent=2) if isinstance(v, (dict, list)) else str(v) for k, v in data_point.metadata.items()}
    
    app.logger.debug(f"Rendering edit page for index {index}")
    return render_template(
        'edit.html',
        index=index,
        query_fields=query_fields,
        metadata_fields=metadata_fields,
        query_data=query_data,
        metadata_data=metadata_data
    )

@app.route('/add', methods=['GET', 'POST'])
def add():
    """Handle adding a new data point."""
    data = [QueryData.from_dict(d) for d in session.get('data', [])]
    selected_file_name = session.get('selected_file_name')
    if not data:
        app.logger.warning("No data loaded for adding new data point")
        flash('Please load a dataset first', 'error')
        return redirect(url_for('index'))
    
    data_point = data[0]
    query_fields = sorted(data_point.query[0].keys()) if data_point.query else []
    metadata_fields = sorted(data_point.metadata.keys())
    
    if request.method == 'POST':
        try:
            new_query = process_form_fields(query_fields, 'query')
            new_metadata = process_form_fields(metadata_fields, 'metadata')
            
            new_data_point = QueryData(query=[new_query], metadata=new_metadata)
            data.append(new_data_point)
            
            session_id = get_session_id()
            original_name = os.path.splitext(selected_file_name)[0]
            added_filename, added_filepath = get_file_paths(original_name, 'ADDED_FOLDER', app, session_id)
            append_data_to_file(added_filepath, new_data_point)
            
            session['data'] = [d.to_dict() for d in data]
            session['has_added_data'] = True
            app.logger.info(f"New data point added for session {session_id}, saved to {added_filename}")
            flash('New data point added!', 'success')
            return redirect(url_for('data_table'))
        except Exception as e:
            app.logger.error(f"Failed to add new data point: {str(e)}")
            flash(f'Failed to add new data point: {str(e)}', 'error')
    
    query_data = {field: '' for field in query_fields}
    metadata_data = {field: '' for field in metadata_fields}
    
    app.logger.debug("Rendering add page")
    return render_template(
        'add.html',
        query_fields=query_fields,
        metadata_fields=metadata_fields,
        query_data=query_data,
        metadata_data=metadata_data
    )

@app.route('/download')
def download():
    """Serve the modified data file for download."""
    data = [QueryData.from_dict(d) for d in session.get('data', [])]
    selected_file_name = session.get('selected_file_name')
    if not data:
        app.logger.warning("No data available for download")
        flash('No data to download', 'error')
        return redirect(url_for('index'))
    
    if not selected_file_name:
        app.logger.warning("No file selected for download")
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    session_id = get_session_id()
    original_name = os.path.splitext(selected_file_name)[0]
    output_filename, filepath = get_file_paths(original_name, 'MODIFIED_FOLDER', app, session_id)
    
    save_data_to_file(filepath, data)
    
    app.logger.info(f"Serving download file for session {session_id}: {output_filename}")
    return send_file(filepath, as_attachment=True, download_name=output_filename)

@app.route('/download_added')
def download_added():
    """Serve the added data file for download."""
    selected_file_name = session.get('selected_file_name')
    if not selected_file_name:
        app.logger.warning("No file selected for downloading added data")
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    session_id = get_session_id()
    original_name = os.path.splitext(selected_file_name)[0]
    added_filename, filepath = get_file_paths(original_name, 'ADDED_FOLDER', app, session_id)
    
    if not os.path.exists(filepath):
        app.logger.warning(f"No added data file exists for session {session_id}: {added_filename}")
        flash('No added data available to download', 'error')
        return redirect(url_for('data_table'))
    
    app.logger.info(f"Serving added data file for session {session_id}: {added_filename}")
    return send_file(filepath, as_attachment=True, download_name=added_filename)

if __name__ == '__main__':
    app.run()
    