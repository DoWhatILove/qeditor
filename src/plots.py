import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend before importing pyplot
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
from io import BytesIO
import base64

def plot_pie(counts):
    """Create a pie chart and return as base64-encoded image."""
    fig, ax = plt.subplots(figsize=(14, 7))
    labels = list(counts.keys())
    sizes = list(counts.values())
    total = sum(sizes)
    colors = plt.cm.Paired(range(len(labels)))
    explode = [0.1] * len(labels)
    wedges, _, autotexts = ax.pie(
        sizes, explode=explode, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=140, textprops={'fontsize': 10}
    )
    ax.set_title("Segment Distribution")
    ax.axis('equal')
    legend_labels = [f"{label} ({(count/total)*100:.1f}%)" for label, count in counts.items()]
    ax.legend(wedges, legend_labels, title="Categories", loc="upper center",
              bbox_to_anchor=(0.5, -0.1), ncol=2)
    
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    return img_base64

def plot_stacked_bar(data):
    """Plot stacked bar chart and return as base64-encoded image."""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    intent_subintent_map = {}
    for item in data:
        q_intent = item.metadata.get('question_intent', 'Unknown')
        sub_intent = item.metadata.get('sub_intent', 'Unknown')
        if q_intent not in intent_subintent_map:
            intent_subintent_map[q_intent] = Counter()
        intent_subintent_map[q_intent][sub_intent] += 1

    question_intents = sorted(intent_subintent_map.keys())
    all_sub_intents = sorted(set(sub_intent for counter in intent_subintent_map.values() for sub_intent in counter))
    plot_data = np.zeros((len(all_sub_intents), len(question_intents)))

    for i, sub_intent in enumerate(all_sub_intents):
        for j, q_intent in enumerate(question_intents):
            plot_data[i, j] = intent_subintent_map[q_intent].get(sub_intent, 0)

    bottom = np.zeros(len(question_intents))
    colors = plt.cm.Paired(np.linspace(0, 1, len(all_sub_intents)))
    max_height = np.max(bottom + np.sum(plot_data, axis=0))
    labeled_sub_intents = set()
    patches = []

    for i, sub_intent in enumerate(all_sub_intents):
        bars = ax.bar(question_intents, plot_data[i], bottom=bottom, color=colors[i])
        patches.append(bars[0])
        for j, bar in enumerate(bars):
            height = plot_data[i, j]
            if height > 0.05 * max_height:
                x = bar.get_x() + bar.get_width() / 2
                y = bottom[j] + height / 2
                ax.text(x, y, sub_intent, ha='center', va='center', fontsize=10, color='white',
                        bbox=dict(facecolor='black', alpha=0.8, pad=2))
                labeled_sub_intents.add(sub_intent)
        bottom += plot_data[i]

    unlabeled_sub_intents = [sub_intent for sub_intent in all_sub_intents if sub_intent not in labeled_sub_intents]
    if unlabeled_sub_intents:
        unlabeled_patches = [p for p, sub_intent in zip(patches, all_sub_intents) if sub_intent in unlabeled_sub_intents]
        ax.legend(unlabeled_patches, unlabeled_sub_intents, title="Unlabeled Sub-Intents",
                  loc="center left", bbox_to_anchor=(1.05, 0.5), ncol=1, fontsize=10)

    ax.set_title("Sub-Intent Distribution by Question Intent", fontsize=14)
    ax.set_xlabel("Question Intent", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax.tick_params(axis='x', rotation=45, labelsize=10)
    ax.tick_params(axis='y', labelsize=10)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    return img_base64