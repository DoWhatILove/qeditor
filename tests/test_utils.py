import os
import shutil
import pytest
import tempfile
import json
from flask import Flask, session
from src.utils import (
    ensure_folders_exist, load_file, reset_session_and_globals,
    get_search_params, filter_data, sort_data, prepare_table_data,
    get_sort_indicators, generate_charts, process_form_fields,
    save_data_to_file, append_data_to_file, get_file_paths
)
from src.data import QueryData

@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.secret_key = 'test_secret_key'
    app.config['DATA_FOLDER'] = tempfile.mkdtemp()
    app.config['MODIFIED_FOLDER'] = tempfile.mkdtemp()
    app.config['ADDED_FOLDER'] = tempfile.mkdtemp()
    yield app
    for folder in [app.config['DATA_FOLDER'], app.config['MODIFIED_FOLDER'], app.config['ADDED_FOLDER']]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

@pytest.fixture
def sample_data():
    """Sample QueryData instances."""
    return [
        QueryData([{'text': 'query1'}], {'segment': 'regular', 'question_intent': 'intent1', 'sub_intent': 'sub1'}),
        QueryData([{'text': 'query2'}], {'segment': 'premium', 'question_intent': 'intent2', 'sub_intent': 'sub2'})
    ]

def test_ensure_folders_exist(app):
    """Test ensure_folders_exist creates directories."""
    folder = os.path.join(app.config['DATA_FOLDER'], 'test')
    ensure_folders_exist(app, folders=[folder])
    assert os.path.exists(folder)

def test_load_file(app, sample_data):
    """Test load_file loads TSV data."""
    content = f"{json.dumps([{'text': 'query1'}])}\t{json.dumps({'segment': 'regular'})}\n"
    fd, path = tempfile.mkstemp(suffix='.tsv')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    
    data = load_file(path, app)
    assert len(data) == 1
    assert data[0].query == [{'text': 'query1'}]
    assert data[0].metadata == {'segment': 'regular'}
    
    os.remove(path)

def test_reset_session_and_globals(app):
    """Test reset_session_and_globals sets session variables."""
    with app.test_request_context():
        reset_session_and_globals()
        assert session['data_loaded'] is True
        assert session['has_added_data'] is False
        assert session['sort_column'] is None
        assert session['sort_reverse'] is False

def test_get_search_params(app):
    """Test get_search_params extracts query args."""
    with app.test_request_context('/?question_intent=intent1&sub_intent=sub1'):
        params = get_search_params()
        assert params == {
            'question_intent': 'intent1',
            'sub_intent': 'sub1',
            'segment': ''
        }

def test_filter_data(app, sample_data):
    """Test filter_data filters by search params."""
    params = {'question_intent': 'intent1', 'sub_intent': '', 'segment': ''}
    filtered = filter_data(sample_data, params, app)
    assert len(filtered) == 1
    assert filtered[0].metadata['question_intent'] == 'intent1'

def test_sort_data(app, sample_data):
    """Test sort_data sorts by column."""
    with app.test_request_context():
        sorted_data = sort_data(sample_data, 'Question Intent', app)
        assert sorted_data[0].metadata['question_intent'] == 'intent1'
        assert session['sort_column'] == 'Question Intent'
        assert session['sort_reverse'] is False

def test_prepare_table_data(sample_data):
    """Test prepare_table_data formats data for table."""
    table_data = prepare_table_data(sample_data, start_idx=0)
    assert len(table_data) == 2
    assert table_data[0] == {
        'index': 0,
        'text': 'query1',
        'segment': 'regular',
        'question_intent': 'intent1',
        'sub_intent': 'sub1'
    }

def test_get_sort_indicators(app):
    """Test get_sort_indicators returns sort arrows."""
    with app.test_request_context():
        session['sort_column'] = 'Question Intent'
        session['sort_reverse'] = False
        indicators = get_sort_indicators()
        assert indicators['Question Intent'] == ' ▲'
        assert indicators['Sub Intent'] == ''

def test_generate_charts(app, sample_data):
    """Test generate_charts produces chart JSON."""
    pie, bar = generate_charts(sample_data, app)
    pie_data = json.loads(pie)
    assert pie_data['labels'] == ['regular', 'premium']
    assert len(pie_data['datasets'][0]['data']) == 2

def test_process_form_fields(app):
    """Test process_form_fields handles form data."""
    with app.test_request_context('/', data={'query_text': '"value"', 'metadata_segment': 'regular'}):
        fields = ['text', 'segment']
        result = process_form_fields(fields, 'query')
        assert result == {'text': 'value', 'segment': ''}

def test_save_data_to_file(sample_data):
    """Test save_data_to_file writes TSV."""
    fd, path = tempfile.mkstemp(suffix='.tsv')
    os.close(fd)
    save_data_to_file(path, sample_data)
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert 'query1' in lines[0]
    os.remove(path)

def test_append_data_to_file(sample_data):
    """Test append_data_to_file appends to TSV."""
    fd, path = tempfile.mkstemp(suffix='.tsv')
    os.close(fd)
    append_data_to_file(path, sample_data[0])
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    assert len(lines) == 1
    assert 'query1' in lines[0]
    os.remove(path)

def test_get_file_paths(app):
    """Test get_file_paths generates correct paths."""
    session_id = 'test_session'
    filename, filepath = get_file_paths('test', 'MODIFIED_FOLDER', app, session_id)
    assert filename == 'test_modified.tsv'
    assert os.path.exists(os.path.dirname(filepath))
