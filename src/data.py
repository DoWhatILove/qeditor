import json

class QueryData:
    def __init__(self, query, metadata):
        self.query = query
        self.metadata = metadata

def load_query_set(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Split line by tab
            columns = line.strip().split('\t')
            if len(columns) != 2:
                raise ValueError(f"Invalid line format: {line}")
            # Parse each column as JSON
            query_json = json.loads(columns[0])
            metadata_json = json.loads(columns[1])
            # Create QueryData object
            query_data = QueryData(query_json, metadata_json)
            data.append(query_data)

    return data
