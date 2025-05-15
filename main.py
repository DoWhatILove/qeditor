import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import Counter
import json
from src.data import load_query_set
import numpy as np

# UI configuration constants
WINDOW_SIZE = "1200x800"
POPUP_FONT = ("Arial", 12)
TREEVIEW_ROW_HEIGHT = 40
MIN_TEXT_ROWS = 2
MAX_TEXT_ROWS = 20
PLOT_FIGSIZE = (15, 6)
PLOT_WSPACE = 0.4
PLOT_BOTTOM_MARGIN = 0.3

class QueryEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Query Set Editor")
        self.root.geometry(WINDOW_SIZE)
        self.data = []
        self.sort_column_ = None
        self.sort_reverse = False
        self._setup_window()
        self._create_widgets()

    def _setup_window(self):
        """Configure window properties and event bindings."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _create_widgets(self):
        """Initialize main UI components."""
        tk.Button(self.main_frame, text="Select Query Set", command=self.load_file).pack(pady=5)
        self._setup_plots()
        tk.Label(self.main_frame, text="Queries: ").pack(pady=5)
        self.create_treeview()
        self.update_charts()

    def _setup_plots(self):
        """Create matplotlib figure and canvas."""
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=PLOT_FIGSIZE)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(pady=10, fill=tk.BOTH, expand=True)

    def create_treeview(self):
        """Create and configure the Treeview widget."""
        self.tree = ttk.Treeview(
            self.main_frame,
            columns=("Text", "Segment", "Question Intent", "Sub Intent"),
            show="headings",
            height=5
        )
        self._configure_treeview_columns()
        self._configure_treeview_style()
        self.tree.pack(pady=5, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self.show_details)

    def _configure_treeview_columns(self):
        """Set up Treeview column headers and properties."""
        self.tree.heading("Text", text="Query Text")
        self.tree.heading("Segment", text="Segment")
        self.tree.heading("Question Intent", text="Question Intent",
                        command=lambda: self.sort_column("Question Intent"))
        self.tree.heading("Sub Intent", text="Sub Intent",
                        command=lambda: self.sort_column("Sub Intent"))
        self.tree.column("Text", width=600, anchor="w", stretch=True)
        self.tree.column("Segment", width=150, anchor="w")
        self.tree.column("Question Intent", width=150, anchor="w")
        self.tree.column("Sub Intent", width=200, anchor="w")

    def _configure_treeview_style(self):
        """Configure Treeview visual style."""
        style = ttk.Style()
        style.configure("Treeview", rowheight=TREEVIEW_ROW_HEIGHT)

    def update_column_headers(self):
        """Update Treeview column headers with sort indicators."""
        for col in ["Question Intent", "Sub Intent"]:
            indicator = (" ▲" if self.sort_column_ == col and not self.sort_reverse else
                        " ▼" if self.sort_column_ == col else "")
            self.tree.heading(col, text=col + indicator)

    def sort_column(self, column):
        """Sort data by specified column."""
        self._update_sort_state(column)
        self._sort_data(column)
        self.update_table()
        self.update_column_headers()

    def _update_sort_state(self, column):
        """Update sort column and direction."""
        if self.sort_column_ == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column_ = column
            self.sort_reverse = False

    def _sort_data(self, column):
        """Sort data based on column."""
        key_map = {
            "Question Intent": lambda x: x.metadata.get('question_intent', 'Unknown').lower(),
            "Sub Intent": lambda x: x.metadata.get('sub_intent', 'Unknown').lower()
        }
        if column in key_map:
            self.data.sort(key=key_map[column], reverse=self.sort_reverse)

    def load_file(self):
        """Load data from a file."""
        file_path = filedialog.askopenfilename(filetypes=[("tsv files", "*.tsv"), ("All files", "*.*")])
        if file_path:
            try:
                self.data = load_query_set(file_path)
                self.sort_column_ = None
                self.sort_reverse = False
                self.update_table()
                self.update_charts()
                self.update_column_headers()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")

    def update_table(self):
        """Update Treeview with current data."""
        self.tree.delete(*self.tree.get_children())
        for idx, item in enumerate(self.data):
            values = (
                item.query[0].get('text', 'No text available'),
                item.metadata.get('segment', 'Unknown'),
                item.metadata.get('question_intent', 'Unknown'),
                item.metadata.get('sub_intent', 'Unknown')
            )
            self.tree.insert("", tk.END, iid=idx, values=values)

    def update_charts(self):
        """Update the pie chart for segment and stacked bar chart for question_intent/sub_intent."""
        self._clear_plots()
        if not self.data:
            self._show_empty_charts()
            return
        self._plot_distribution_charts()
        self._finalize_plots()

    def _clear_plots(self):
        """Clear existing plots."""
        for ax in [self.ax1, self.ax2]:
            ax.clear()

    def _show_empty_charts(self):
        """Display empty chart message."""
        for ax in [self.ax1, self.ax2]:
            ax.text(0.5, 0.5, 'No data available', horizontalalignment='center', verticalalignment='center')
        self.canvas.draw()

    def _plot_distribution_charts(self):
        """Plot segment pie chart and question_intent/sub_intent stacked bar chart."""
        # Plot segment pie chart
        segment_counter = Counter(item.metadata['segment'] for item in self.data)
        self.plot_pie(self.ax1, segment_counter, "Segment Distribution")
        
        # Plot question_intent/sub_intent stacked bar chart
        self.plot_stacked_bar(self.ax2)

    def _finalize_plots(self):
        """Adjust plot layout and redraw canvas."""
        self.fig.subplots_adjust(left=0.05, right=0.85, wspace=PLOT_WSPACE, bottom=PLOT_BOTTOM_MARGIN)
        self.canvas.draw()

    def plot_pie(self, ax, counts, title):
        """Create a pie chart."""
        labels = list(counts.keys())
        sizes = list(counts.values())
        total = sum(sizes)
        colors = plt.cm.Paired(range(len(labels)))
        explode = [0.1] * len(labels)
        wedges, _, autotexts = ax.pie(
            sizes, explode=explode, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=140, textprops={'fontsize': 10}
        )
        ax.set_title(title)
        ax.axis('equal')
        legend_labels = [f"{label} ({(count/total)*100:.1f}%)" for label, count in counts.items()]
        ax.legend(wedges, legend_labels, title="Categories", loc="upper center",
                 bbox_to_anchor=(0.5, -0.1), ncol=2)

    def plot_stacked_bar(self, ax):
        """Plot stacked bar chart for sub_intent distribution by question_intent with labels on segments and legend for unlabeled categories on the right."""
        # Collect question_intent and sub_intent data
        intent_subintent_map = {}
        for item in self.data:
            q_intent = item.metadata.get('question_intent', 'Unknown')
            sub_intent = item.metadata.get('sub_intent', 'Unknown')
            if q_intent not in intent_subintent_map:
                intent_subintent_map[q_intent] = Counter()
            intent_subintent_map[q_intent][sub_intent] += 1

        # Prepare data for plotting
        question_intents = sorted(intent_subintent_map.keys())
        all_sub_intents = sorted(set(sub_intent for counter in intent_subintent_map.values() for sub_intent in counter))
        data = np.zeros((len(all_sub_intents), len(question_intents)))

        for i, sub_intent in enumerate(all_sub_intents):
            for j, q_intent in enumerate(question_intents):
                data[i, j] = intent_subintent_map[q_intent].get(sub_intent, 0)

        # Plot stacked bars and track labeled/unlabeled sub_intents
        bottom = np.zeros(len(question_intents))
        colors = plt.cm.Paired(np.linspace(0, 1, len(all_sub_intents)))
        max_height = np.max(bottom + np.sum(data, axis=0))  # Max bar height for label threshold
        labeled_sub_intents = set()
        patches = []  # Store patches for legend

        for i, sub_intent in enumerate(all_sub_intents):
            bars = ax.bar(question_intents, data[i], bottom=bottom, color=colors[i])
            patches.append(bars[0])  # Store patch for potential legend
            # Add labels to non-zero segments
            for j, bar in enumerate(bars):
                height = data[i, j]
                if height > 0.05 * max_height:  # Label significant segments
                    x = bar.get_x() + bar.get_width() / 2
                    y = bottom[j] + height / 2
                    ax.text(x, y, sub_intent, ha='center', va='center', fontsize=8, color='white',
                            bbox=dict(facecolor='black', alpha=0.5, pad=1))
                    labeled_sub_intents.add(sub_intent)
            bottom += data[i]

        # Add legend for unlabeled sub_intents on the right
        unlabeled_sub_intents = [sub_intent for sub_intent in all_sub_intents if sub_intent not in labeled_sub_intents]
        if unlabeled_sub_intents:
            unlabeled_patches = [p for p, sub_intent in zip(patches, all_sub_intents) if sub_intent in unlabeled_sub_intents]
            ax.legend(unlabeled_patches, unlabeled_sub_intents, title="Unlabeled Sub-Intents",
                     loc="center left", bbox_to_anchor=(1.0, 0.5), ncol=1, fontsize=8)

        # Customize plot
        ax.set_title("Sub-Intent Distribution by Question Intent")
        ax.set_xlabel("Question Intent")
        ax.set_ylabel("Count")
        ax.tick_params(axis='x', rotation=45)

    def get_all_fields(self):
        """Collect unique fields from query and metadata."""
        query_fields = set()
        metadata_fields = set()
        for data_point in self.data:
            if data_point.query and isinstance(data_point.query[0], dict):
                query_fields.update(data_point.query[0].keys())
            if isinstance(data_point.metadata, dict):
                metadata_fields.update(data_point.metadata.keys())
        return sorted(query_fields), sorted(metadata_fields)

    def save_data_to_file(self, file_path):
        """Save data to a file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for data_point in self.data:
                    query_json = json.dumps(data_point.query, ensure_ascii=False)
                    metadata_json = json.dumps(data_point.metadata, ensure_ascii=False)
                    f.write(f"{query_json}\t{metadata_json}\n")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
            raise

    def show_details(self, event):
        """Display and edit details for selected data point."""
        selected_item = self.tree.selection()
        if not selected_item:
            return
        idx = int(selected_item[0])
        data_point = self.data[idx]
        query_fields, metadata_fields = self.get_all_fields()
        popup = self._create_popup_window()
        scrollable_frame, canvas = self._setup_popup_scrollable_area(popup)
        query_entries = self._create_field_entries(scrollable_frame, query_fields, data_point.query[0], "Query Fields")
        metadata_entries = self._create_field_entries(scrollable_frame, metadata_fields, data_point.metadata, "Metadata Fields")
        self._add_popup_buttons(scrollable_frame, popup, data_point, query_fields, metadata_fields, query_entries, metadata_entries)

    def _create_popup_window(self):
        """Create popup window for editing."""
        popup = tk.Toplevel(self.root)
        popup.title("Edit Data Point")
        popup.state('zoomed')
        return popup

    def _setup_popup_scrollable_area(self, popup):
        """Set up scrollable area in popup."""
        outer_frame = ttk.Frame(popup)
        outer_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(outer_frame)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=canvas.winfo_width()))
        return scrollable_frame, canvas

    def _create_field_entries(self, parent, fields, data, title):
        """Create text entry fields for data."""
        style = ttk.Style()
        style.configure("Colored.TLabel", background="#ADD8E6")
        ttk.Label(parent, text=title, style="Colored.TLabel").pack(pady=10, fill=tk.X)
        entries = {}
        for field in fields:
            ttk.Label(parent, text=field.capitalize() + ":", style="Colored.TLabel").pack(anchor="w", padx=10, pady=5, fill=tk.X)
            value = data.get(field, '')
            if isinstance(value, (list, dict)):
                value = json.dumps(value, indent=2)
            value = str(value)
            line_count = value.count('\n') + 1
            text_height = min(max(line_count, MIN_TEXT_ROWS), MAX_TEXT_ROWS)
            text_widget = tk.Text(parent, height=text_height, wrap=tk.WORD, font=POPUP_FONT)
            text_widget.insert("1.0", str(value))
            text_widget.pack(anchor="w", padx=10, pady=5, fill=tk.BOTH, expand=True)
            entries[field] = text_widget
        return entries

    def _add_popup_buttons(self, parent, popup, data_point, query_fields, metadata_fields, query_entries, metadata_entries):
        """Add save and close buttons to popup."""
        def save_changes():
            try:
                new_query = self._process_entries(query_fields, query_entries)
                data_point.query[0] = new_query
                new_metadata = self._process_entries(metadata_fields, metadata_entries)
                data_point.metadata = new_metadata
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".tsv",
                    filetypes=[("tsv text files", "*.tsv"), ("All files", "*.*")],
                    title="Save Data File",
                    initialfile="query_set_modified.tsv"
                )
                if file_path:
                    self.save_data_to_file(file_path)
                else:
                    messagebox.showinfo("Info", "Changes saved in memory but not to file.")
                self.update_table()
                self.update_charts()
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save changes: {str(e)}")

        ttk.Button(parent, text="Save", command=save_changes).pack(pady=10)
        ttk.Button(parent, text="Close", command=popup.destroy).pack(pady=5)

    def _process_entries(self, fields, entries):
        """Process text entries and return updated data."""
        new_data = {}
        for field in fields:
            value = entries[field].get("1.0", tk.END).strip()
            if value:
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            else:
                value = ''
            new_data[field] = value
        return new_data

    def on_closing(self):
        """Handle window closing event."""
        plt.close(self.fig)
        self.root.destroy()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = QueryEditorApp(root)
    root.mainloop()