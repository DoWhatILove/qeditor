import json
import logging

class QueryData:
    def __init__(self, query, metadata):
        self.query = query
        self.metadata = metadata
    
    def to_dict(self):
        """Convert QueryData to a JSON-serializable dictionary."""
        return {
            'query': self.query,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a QueryData instance from a dictionary."""
        return cls(data['query'], data['metadata'])

def load_query_data(file_path):
    """Load QueryData objects from a TSV file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            columns = line.strip().split('\t')
            if len(columns) != 2:
                raise ValueError(f"Invalid line format: {line}")
            try:
                query_json = json.loads(columns[0])
                metadata_json = json.loads(columns[1])
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in line: {line}") from e
            query_data = QueryData(query_json, metadata_json)
            data.append(query_data)
    if not data:
        logging.warning(f"No data loaded from {file_path}")
    return data
