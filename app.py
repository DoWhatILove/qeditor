import json
import os
from flask import Flask, request, render_template, redirect, url_for, flash, send_file, session
from src.data import QueryData
from src.utils import (
    setup_logging, ensure_folders_exist, get_tsv_files, load_file, reset_session_and_globals,
    get_search_params, filter_data, sort_data, prepare_table_data, get_sort_indicators,
    generate_charts, process_form_fields, save_data_to_file, append_data_to_file, get_file_paths
)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'supersecretkey')
app.config['DATA_FOLDER'] = 'data'
app.config['MODIFIED_FOLDER'] = 'modified'
app.config['ADDED_FOLDER'] = 'added'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# In-memory storage
data = []
selected_file_name = None

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle file selection and loading."""
    global data, selected_file_name
    setup_logging(app)
    ensure_folders_exist(app)
    
    tsv_files = get_tsv_files(app)
    
    if request.method == 'POST':
        selected_file = request.form.get('tsv_file')
        if not selected_file:
            app.logger.warning("No file selected")
            flash('Please select a .tsv file', 'error')
            return render_template(
                'index.html',
                tsv_files=tsv_files,
                data_loaded=session.get('data_loaded', False)
            )
        
        if selected_file not in tsv_files:
            app.logger.warning(f"Invalid file selected: {selected_file}")
            flash('Invalid file selected', 'error')
            return render_template(
                'index.html',
                tsv_files=tsv_files,
                data_loaded=session.get('data_loaded', False)
            )
        
        filepath = os.path.join(app.config['DATA_FOLDER'], selected_file)
        app.logger.info(f"Loading file: {selected_file}")
        try:
            data = load_file(filepath, app)
            reset_session_and_globals()
            selected_file_name = selected_file
            flash('File loaded successfully!', 'success')
            return redirect(url_for('data_table'))
        except Exception as e:
            session['data_loaded'] = False
            flash(f'Failed to load file: {str(e)}', 'error')
            return render_template(
                'index.html',
                tsv_files=tsv_files,
                data_loaded=session.get('data_loaded', False)
            )
    
    app.logger.debug("Rendering index page")
    return render_template(
        'index.html',
        tsv_files=tsv_files,
        data_loaded=session.get('data_loaded', False)
    )

@app.route('/data')
def data_table():
    """Display filtered and sorted data table."""
    global data
    if not data:
        app.logger.warning("No data loaded for data table")
        return redirect(url_for('index'))
    
    search_params = get_search_params()
    filtered_data = filter_data(data, search_params, app)
    
    app.logger.info(f"Search terms: question_intent='{search_params['question_intent']}', "
                   f"sub_intent='{search_params['sub_intent']}', segment='{search_params['segment']}'")
    app.logger.info(f"Filtered {len(filtered_data)} of {len(data)} rows")
    if not filtered_data and data:
        app.logger.debug(f"Sample metadata (first 3 rows): {[item.metadata for item in data[:3]]}")
    
    column = request.args.get('sort')
    filtered_data = sort_data(filtered_data, column, app)
    
    table_data = prepare_table_data(filtered_data)
    sort_indicators = get_sort_indicators()
    
    app.logger.debug("Rendering data table page")
    return render_template(
        'data.html',
        data=table_data,
        sort_indicators=sort_indicators,
        search_params=search_params,
        total_rows=len(data),
        filtered_rows=len(filtered_data)
    )

@app.route('/charts')
def charts():
    """Render charts page with pie and stacked bar charts."""
    global data
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
    global data
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
            
            save_data_to_file(os.path.join(app.config['DATA_FOLDER'], 'temp.tsv'), data)
            
            app.logger.info(f"Data point {index} updated successfully")
            flash('Changes saved!', 'success')
            return redirect(url_for('data_table'))
        except Exception as e:
            app.logger.error(f"Failed to save changes: {str(e)}")
            flash(f'Failed to save changes: {str(e)}', 'error')
    
    query_data = {k: json.dumps(v, indent=2) if isinstance(v, (dict, list)) else str(v) for k, v in data_point.query[0].items()}
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
    global data, selected_file_name
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
            
            original_name = os.path.splitext(selected_file_name)[0]
            added_filename, added_filepath = get_file_paths(original_name, 'ADDED_FOLDER', app)
            append_data_to_file(added_filepath, new_data_point)
            
            save_data_to_file(os.path.join(app.config['DATA_FOLDER'], 'temp.tsv'), data)
            
            session['has_added_data'] = True
            app.logger.info(f"New data point added, saved to {added_filename}")
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
    global data, selected_file_name
    if not data:
        app.logger.warning("No data available for download")
        flash('No data to download', 'error')
        return redirect(url_for('index'))
    
    if not selected_file_name:
        app.logger.warning("No file selected for download")
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    original_name = os.path.splitext(selected_file_name)[0]
    output_filename, filepath = get_file_paths(original_name, 'MODIFIED_FOLDER', app)
    
    save_data_to_file(filepath, data)
    
    app.logger.info(f"Serving download file: {output_filename}")
    return send_file(filepath, as_attachment=True, download_name=output_filename)

@app.route('/download_added')
def download_added():
    """Serve the added data file for download."""
    global selected_file_name
    if not selected_file_name:
        app.logger.warning("No file selected for downloading added data")
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    original_name = os.path.splitext(selected_file_name)[0]
    added_filename, filepath = get_file_paths(original_name, 'ADDED_FOLDER', app)
    
    if not os.path.exists(filepath):
        app.logger.warning(f"No added data file exists: {added_filename}")
        flash('No added data available to download', 'error')
        return redirect(url_for('data_table'))
    
    app.logger.info(f"Serving added data file: {added_filename}")
    return send_file(filepath, as_attachment=True, download_name=added_filename)

if __name__ == '__main__':
    app.run(debug=True)
