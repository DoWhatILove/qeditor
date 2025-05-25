import pytest
from collections import Counter
from src.plots import generate_colors, plot_pie, plot_stacked_bar
from src.data import QueryData

@pytest.fixture
def sample_data():
    """Sample QueryData instances for chart tests."""
    return [
        QueryData([{'text': 'query1'}], {'segment': 'regular', 'question_intent': 'intent1', 'sub_intent': 'sub1'}),
        QueryData([{'text': 'query2'}], {'segment': 'premium', 'question_intent': 'intent1', 'sub_intent': 'sub2'}),
        QueryData([{'text': 'query3'}], {'segment': 'regular', 'question_intent': 'intent2', 'sub_intent': 'sub1'})
    ]

def test_generate_colors():
    """Test generate_colors produces distinct hex colors."""
    colors = generate_colors(3)
    assert len(colors) == 3
    assert all(color.startswith('#') and len(color) == 7 for color in colors)
    assert len(set(colors)) == 3  # Distinct colors

def test_plot_pie():
    """Test plot_pie generates correct pie chart data."""
    counts = Counter(['regular', 'regular', 'premium'])
    result = plot_pie(counts)
    assert result['labels'] == ['regular', 'premium']
    assert result['datasets'][0]['data'] == [2, 1]
    assert len(result['datasets'][0]['backgroundColor']) == 2
    assert result['percentages'] == pytest.approx([66.66666666666667, 33.33333333333333])

def test_plot_pie_empty():
    """Test plot_pie handles empty counts."""
    counts = Counter()
    result = plot_pie(counts)
    assert result['labels'] == []
    assert result['datasets'][0]['data'] == []
    assert result['percentages'] == []

def test_plot_stacked_bar(sample_data):
    """Test plot_stacked_bar generates correct bar chart data."""
    result = plot_stacked_bar(sample_data)
    assert result['labels'] == ['intent1', 'intent2']
    assert len(result['datasets']) == 2  # sub1, sub2
    assert result['datasets'][0]['label'] == 'sub1'
    assert result['datasets'][0]['data'] == [1, 1]  # sub1 in intent1, intent2
    assert result['datasets'][1]['data'] == [1, 0]  # sub2 in intent1, intent2
    