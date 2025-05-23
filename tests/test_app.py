import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import tempfile
import shutil
from flask import session
from app import app, get_session_id, cleanup_session_files
from io import BytesIO
import json

@pytest.fixture
def client():
    """Create a Flask test client with temporary session directory."""
    app.config['TESTING'] = True
    app.secret_key = 'test_secret_key'
    app.config['SESSION_FILE_DIR'] = tempfile.mkdtemp()
    app.config['DATA_FOLDER'] = tempfile.mkdtemp()
    app.config['MODIFIED_FOLDER'] = tempfile.mkdtemp()
    app.config['ADDED_FOLDER'] = tempfile.mkdtemp()
    
    with app.test_client() as client:
        with app.app_context():
            yield client
    
    # Cleanup
    for folder in [app.config['SESSION_FILE_DIR'], app.config['DATA_FOLDER'], 
                   app.config['MODIFIED_FOLDER'], app.config['ADDED_FOLDER']]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

@pytest.fixture
def sample_tsv():
    """Create a sample TSV file with 2 rows."""
    data = [
        {'text': 'query1'},
        {'segment': 'regular', 'question_intent': 'intent1', 'sub_intent': 'sub1'}
    ]
    data2 = [
        {'text': 'query2'},
        {'segment': 'premium', 'question_intent': 'intent2', 'sub_intent': 'sub2'}
    ]
    content = f"{json.dumps([data[0]])}\t{json.dumps(data[1])}\n{json.dumps([data2[0]])}\t{json.dumps(data2[1])}"
    fd, path = tempfile.mkstemp(suffix='.tsv')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    yield path
    os.remove(path)

def test_index_get(client):
    """Test GET / renders index page."""
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Upload a .tsv file' in rv.data

def test_index_post_upload(client, sample_tsv):
    """Test POST / with valid TSV upload."""
    with open(sample_tsv, 'rb') as f:
        data = {'tsv_file': (f, 'test.tsv')}
        rv = client.post('/', data=data, content_type='multipart/form-data')
    
    assert rv.status_code == 302
    assert rv.location.endswith('/data')
    with client.session_transaction() as sess:
        assert len(sess['data']) == 2
        assert sess['selected_file_name'] == 'test.tsv'
        assert sess['data_loaded'] is True

def test_index_post_no_file(client):
    """Test POST / with no file."""
    rv = client.post('/', data={}, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert b'Please upload a .tsv file' in rv.data

def test_index_post_invalid_file(client):
    """Test POST / with non-TSV file."""
    data = {'tsv_file': (BytesIO(b'test'), 'test.txt')}
    rv = client.post('/', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert b'Only .tsv files are allowed' in rv.data

def test_data_table(client, sample_tsv):
    """Test /data displays data after upload."""
    with open(sample_tsv, 'rb') as f:
        client.post('/', data={'tsv_file': (f, 'test.tsv')}, content_type='multipart/form-data')
    
    rv = client.get('/data')
    assert rv.status_code == 200
    assert b'query1' in rv.data
    assert b'query2' in rv.data
    assert b'regular' in rv.data
    assert b'intent1' in rv.data

def test_data_table_no_data(client):
    """Test /data redirects when no data."""
    rv = client.get('/data')
    assert rv.status_code == 302
    assert rv.location.endswith('/')

def test_edit_get(client, sample_tsv):
    """Test GET /edit/0 shows edit form."""
    with open(sample_tsv, 'rb') as f:
        client.post('/', data={'tsv_file': (f, 'test.tsv')}, content_type='multipart/form-data')
    
    rv = client.get('/edit/0')
    assert rv.status_code == 200
    assert b'text' in rv.data
    assert b'segment' in rv.data
    assert b'query1' in rv.data

def test_edit_post(client, sample_tsv):
    """Test POST /edit/0 updates data."""
    with open(sample_tsv, 'rb') as f:
        client.post('/', data={'tsv_file': (f, 'test.tsv')}, content_type='multipart/form-data')
    
    data = {
        'query_text': 'updated_query',
        'metadata_segment': 'updated_segment',
        'metadata_question_intent': 'updated_intent',
        'metadata_sub_intent': 'updated_sub'
    }
    rv = client.post('/edit/0', data=data)
    assert rv.status_code == 302
    assert rv.location.endswith('/data')
    
    with client.session_transaction() as sess:
        data = sess['data'][0]
        assert data['query'][0]['text'] == 'updated_query'
        assert data['metadata']['segment'] == 'updated_segment'

def test_add_get(client, sample_tsv):
    """Test GET /add shows add form."""
    with open(sample_tsv, 'rb') as f:
        client.post('/', data={'tsv_file': (f, 'test.tsv')}, content_type='multipart/form-data')
    
    rv = client.get('/add')
    assert rv.status_code == 200
    assert b'text' in rv.data
    assert b'segment' in rv.data

def test_add_post(client, sample_tsv):
    """Test POST /add adds new data."""
    with open(sample_tsv, 'rb') as f:
        client.post('/', data={'tsv_file': (f, 'test.tsv')}, content_type='multipart/form-data')
    
    data = {
        'query_text': 'new_query',
        'metadata_segment': 'new_segment',
        'metadata_question_intent': 'new_intent',
        'metadata_sub_intent': 'new_sub'
    }
    rv = client.post('/add', data=data)
    assert rv.status_code == 302
    assert rv.location.endswith('/data')
    
    with client.session_transaction() as sess:
        assert len(sess['data']) == 3
        new_data = sess['data'][-1]
        assert new_data['query'][0]['text'] == 'new_query'
        assert new_data['metadata']['segment'] == 'new_segment'

def test_charts(client, sample_tsv):
    """Test /charts renders charts."""
    with open(sample_tsv, 'rb') as f:
        client.post('/', data={'tsv_file': (f, 'test.tsv')}, content_type='multipart/form-data')
    
    rv = client.get('/charts')
    assert rv.status_code == 200
    assert b'regular' in rv.data
    assert b'premium' in rv.data

def test_download(client, sample_tsv):
    """Test /download serves modified TSV."""
    with open(sample_tsv, 'rb') as f:
        client.post('/', data={'tsv_file': (f, 'test.tsv')}, content_type='multipart/form-data')
    
    rv = client.get('/download')
    assert rv.status_code == 200
    assert rv.headers['Content-Disposition'].startswith('attachment; filename=test_modified.tsv')
    assert b'query1' in rv.data

def test_download_added(client, sample_tsv):
    """Test /download_added serves added TSV after adding data."""
    with open(sample_tsv, 'rb') as f:
        client.post('/', data={'tsv_file': (f, 'test.tsv')}, content_type='multipart/form-data')
    
    client.post('/add', data={
        'query_text': 'new_query',
        'metadata_segment': 'new_segment',
        'metadata_question_intent': 'new_intent',
        'metadata_sub_intent': 'new_sub'
    })
    
    rv = client.get('/download_added')
    assert rv.status_code == 200
    assert rv.headers['Content-Disposition'].startswith('attachment; filename=test_added.tsv')
    assert b'new_query' in rv.data

def test_session_isolation(client, sample_tsv):
    """Test session isolation between two clients."""
    client1 = client
    client2 = app.test_client()
    
    with open(sample_tsv, 'rb') as f:
        client1.post('/', data={'tsv_file': (f, 'test1.tsv')}, content_type='multipart/form-data')
    
    with open(sample_tsv, 'rb') as f:
        client2.post('/', data={'tsv_file': (f, 'test2.tsv')}, content_type='multipart/form-data')
    
    with client1.session_transaction() as sess1:
        sid1 = sess1['sid']
        assert sess1['selected_file_name'] == 'test1.tsv'
    
    with client2.session_transaction() as sess2:
        sid2 = sess2['sid']
        assert sess2['selected_file_name'] == 'test2.tsv'
        assert sid1 != sid2
