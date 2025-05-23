import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
import tempfile
import os
from src.data import QueryData, load_query_data

@pytest.fixture
def sample_data():
    """Sample QueryData instance."""
    query = [{'text': 'query1'}]
    metadata = {'segment': 'regular', 'question_intent': 'intent1', 'sub_intent': 'sub1'}
    return QueryData(query, metadata)

def test_query_data_to_dict(sample_data):
    """Test QueryData.to_dict serialization."""
    result = sample_data.to_dict()
    assert result == {
        'query': [{'text': 'query1'}],
        'metadata': {'segment': 'regular', 'question_intent': 'intent1', 'sub_intent': 'sub1'}
    }

def test_query_data_from_dict():
    """Test QueryData.from_dict deserialization."""
    data = {
        'query': [{'text': 'query1'}],
        'metadata': {'segment': 'regular', 'question_intent': 'intent1', 'sub_intent': 'sub1'}
    }
    result = QueryData.from_dict(data)
    assert result.query == [{'text': 'query1'}]
    assert result.metadata == {'segment': 'regular', 'question_intent': 'intent1', 'sub_intent': 'sub1'}

def test_load_query_data():
    """Test load_query_data with valid TSV."""
    content = f"{json.dumps([{'text': 'query1'}])}\t{json.dumps({'segment': 'regular'})}\n"
    fd, path = tempfile.mkstemp(suffix='.tsv')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    
    data = load_query_data(path)
    assert len(data) == 1
    assert data[0].query == [{'text': 'query1'}]
    assert data[0].metadata == {'segment': 'regular'}
    
    os.remove(path)

def test_load_query_data_empty():
    """Test load_query_data with empty TSV."""
    fd, path = tempfile.mkstemp(suffix='.tsv')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        pass
    
    data = load_query_data(path)
    assert len(data) == 0
    os.remove(path)

def test_load_query_data_invalid_json():
    """Test load_query_data with invalid JSON."""
    content = "invalid_json\t{}\n"
    fd, path = tempfile.mkstemp(suffix='.tsv')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_query_data(path)
    
    os.remove(path)

def test_load_query_data_invalid_format():
    """Test load_query_data with invalid TSV format."""
    content = "single_column\n"
    fd, path = tempfile.mkstemp(suffix='.tsv')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    
    with pytest.raises(ValueError, match="Invalid line format"):
        load_query_data(path)
    
    os.remove(path)
