import json
from collections import Counter
import numpy as np

def generate_colors(n):
    """Generate n distinct colors in HSL format, converted to hex."""
    colors = []
    for i in range(n):
        # Use HSL with varying hue (0-360), fixed saturation (70%), and lightness (50%)
        hue = (i * 360 / n) % 360
        saturation = 70
        lightness = 50
        # Convert HSL to RGB and then to hex
        h = hue / 360
        s = saturation / 100
        l = lightness / 100
        if s == 0:
            r = g = b = l
        else:
            def hue2rgb(p, q, t):
                if t < 0:
                    t += 1
                if t > 1:
                    t -= 1
                if t < 1/6:
                    return p + (q - p) * 6 * t
                if t < 1/2:
                    return q
                if t < 2/3:
                    return p + (q - p) * (2/3 - t) * 6
                return p
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue2rgb(p, q, h + 1/3)
            g = hue2rgb(p, q, h)
            b = hue2rgb(p, q, h - 1/3)
        r = int(round(r * 255))
        g = int(round(g * 255))
        b = int(round(b * 255))
        hex_color = f'#{r:02x}{g:02x}{b:02x}'
        colors.append(hex_color)
    return colors

def plot_pie(counts):
    """Create JSON data for a Chart.js pie chart showing segment distribution."""
    labels = list(counts.keys())
    values = list(counts.values())
    total = sum(values)
    colors = generate_colors(len(labels))
    # Calculate percentages for tooltips
    percentages = [(count / total * 100) for count in values]
    return {
        'labels': labels,
        'datasets': [{
            'data': values,
            'backgroundColor': colors,
            'borderColor': colors,
            'borderWidth': 1
        }],
        'percentages': percentages
    }

def plot_stacked_bar(data):
    """Create JSON data for a Chart.js stacked bar chart showing sub-intent by question intent."""
    intent_subintent_map = {}
    for item in data:
        q_intent = item.metadata.get('question_intent', 'Unknown')
        sub_intent = item.metadata.get('sub_intent', 'Unknown')
        if q_intent not in intent_subintent_map:
            intent_subintent_map[q_intent] = Counter()
        intent_subintent_map[q_intent][sub_intent] += 1

    question_intents = sorted(intent_subintent_map.keys())
    all_sub_intents = sorted(set(sub_intent for counter in intent_subintent_map.values() for sub_intent in counter))
    colors = generate_colors(len(all_sub_intents))
    
    datasets = []
    for i, sub_intent in enumerate(all_sub_intents):
        data_values = [intent_subintent_map[q_intent].get(sub_intent, 0) for q_intent in question_intents]
        datasets.append({
            'label': sub_intent,
            'data': data_values,
            'backgroundColor': colors[i],
            'borderColor': colors[i],
            'borderWidth': 1
        })

    return {
        'labels': question_intents,
        'datasets': datasets
    }
    