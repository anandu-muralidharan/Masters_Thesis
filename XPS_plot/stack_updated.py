import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, colorchooser
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import re

class XPSPlotter:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive XPS Stacker (Pro)")
        
        self.data_list = []
        self.plot_configs = []
        self.fig = None 
        
        # Immediate Startup Prompt
        self.root.withdraw() 
        self.show_shift = messagebox.askyesno("Shift Analysis", 
            "Do you want to see the Binding Energy difference (ΔBE) and vertical shift lines?")
        self.root.deiconify()

        self.setup_ui()

    def setup_ui(self):
        # Left Sidebar
        self.sidebar = tk.Frame(self.root, width=300, bg="#f0f0f0")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Main Plot Area
        self.plot_frame = tk.Frame(self.root, bg="white")
        self.plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Global Controls
        controls = tk.Frame(self.sidebar, bg="#f0f0f0")
        controls.pack(fill=tk.X, pady=5)
        
        tk.Button(controls, text="1. Load Excel Files", command=self.load_files, width=22, bg="#e1e1e1").pack(pady=2)
        tk.Button(controls, text="2. Save Current Plot", command=self.save_plot, width=22, bg="#d1e7dd").pack(pady=2)

        self.scroll_canvas = tk.Canvas(self.sidebar, bg="#f0f0f0")
        self.scrollbar = tk.Scrollbar(self.sidebar, orient="vertical", command=self.scroll_canvas.yview)
        self.control_container = tk.Frame(self.scroll_canvas, bg="#f0f0f0")

        self.scroll_canvas.create_window((0, 0), window=self.control_container, anchor="nw")
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def load_files(self):
        num_files = simpledialog.askinteger("Input", "How many files to stack?", minvalue=1, maxvalue=10)
        if not num_files: return
        
        self.data_list = []
        self.plot_configs = []
        
        for i in range(num_files):
            path = filedialog.askopenfilename(title=f"Select Excel for Plot {i+1}")
            if path:
                label = simpledialog.askstring("Label", f"Formula for {i+1}:")
                df = pd.read_excel(path, header=None)
                n_cols = df.shape[1]
                peak_indices = list(range(2, n_cols - 3))
                
                self.data_list.append({'df': df, 'label': self.get_subscript(label or f"S{i+1}")})
                
                default_colors = ['#d62728', '#1f77b4', '#9467bd', '#2ca02c', '#ff7f0e']
                config = {
                    'included': {idx: tk.BooleanVar(value=True) for idx in peak_indices},
                    'colors': {idx: default_colors[j % len(default_colors)] for j, idx in enumerate(peak_indices)},
                    'show_baseline': tk.BooleanVar(value=True)
                }
                self.plot_configs.append(config)

        self.refresh_sidebar_controls()
        self.update_plot()

    def get_subscript(self, name):
        return re.sub(r'(\d+)', r'$_{\1}$', name)

    def refresh_sidebar_controls(self):
        for widget in self.control_container.winfo_children():
            widget.destroy()

        for i, config in enumerate(self.plot_configs):
            frame = tk.LabelFrame(self.control_container, text=f"Plot {i+1} Controls", padx=5, pady=5)
            frame.pack(fill=tk.X, padx=5, pady=5)

            tk.Checkbutton(frame, text="Show Baseline", variable=config['show_baseline'], 
                           command=self.update_plot, fg="blue", font=('Arial', 9, 'bold')).pack(anchor="w")
            
            tk.Label(frame, text="Peaks:", font=('Arial', 8, 'italic')).pack(anchor="w")
            
            for col_idx, var in config['included'].items():
                row = tk.Frame(frame)
                row.pack(fill=tk.X)
                tk.Checkbutton(row, text=f"P {col_idx-1}", variable=var, command=self.update_plot).pack(side=tk.LEFT)
                btn = tk.Button(row, bg=config['colors'][col_idx], width=2, height=0,
                                command=lambda c=col_idx, p=i: self.pick_color(p, c))
                btn.pack(side=tk.RIGHT)

        self.control_container.update_idletasks()
        self.scroll_canvas.config(scrollregion=self.scroll_canvas.bbox("all"))

    def pick_color(self, plot_idx, col_idx):
        color = colorchooser.askcolor(initialcolor=self.plot_configs[plot_idx]['colors'][col_idx])[1]
        if color:
            self.plot_configs[plot_idx]['colors'][col_idx] = color
            self.refresh_sidebar_controls()
            self.update_plot()

    def save_plot(self):
        if self.fig is None:
            messagebox.showwarning("Warning", "No plot to save!")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("PNG files", "*.png"), ("SVG files", "*.svg"), ("All files", "*.*")])
        if file_path:
            self.fig.savefig(file_path, bbox_inches='tight', dpi=300)
            messagebox.showinfo("Success", f"Plot saved to:\n{file_path}")

    def update_plot(self):
        if not self.data_list: return
        for widget in self.plot_frame.winfo_children(): widget.destroy()

        num_plots = len(self.data_list)
        self.fig, axes = plt.subplots(num_plots, 1, figsize=(6, 3.5 * num_plots), sharex=True)
        if num_plots == 1: axes = [axes]
        plt.subplots_adjust(hspace=0)

        anchor_be = None

        for i, (ax, data_item) in enumerate(zip(axes, self.data_list)):
            df = data_item['df']
            config = self.plot_configs[i]
            n_cols = df.shape[1]
            
            be_full, raw_full = df.iloc[:, 0].values, df.iloc[:, 1].values
            bg_full = df.iloc[:, n_cols - 3].values
            env_full = df.iloc[:, n_cols - 2].values
            
            peaks_only = df.iloc[:, 2 : n_cols - 3]
            active_fit = np.where(peaks_only.sum(axis=1).values > 0.5)[0]
            s, e = (active_fit[0], active_fit[-1]) if len(active_fit) > 0 else (0, len(be_full)-1)

            be, raw, bg, env = be_full[s:e], raw_full[s:e], bg_full[s:e], env_full[s:e]

            first_peak_col = df.iloc[s:e, 2].values
            curr_pos = be[np.argmax(first_peak_col)]
            if i == 0: anchor_be = curr_pos

            # --- DRAWING ---
            ax.scatter(be, raw, s=15, facecolors='none', edgecolors='silver', alpha=0.6, zorder=1)
            
            if config['show_baseline'].get():
                ax.plot(be, bg, color='gray', linestyle='--', linewidth=1.2, zorder=2)
            
            for col_idx, is_included in config['included'].items():
                if is_included.get():
                    p_val = df.iloc[s:e, col_idx].values
                    color = config['colors'][col_idx]
                    ax.plot(be, p_val, color=color, linewidth=2, zorder=3)
                    ax.fill_between(be, bg, p_val, color=color, alpha=0.15, zorder=2)

            ax.plot(be, env, 'k-', linewidth=2.5, zorder=4)
            
            if self.show_shift:
                ax.axvline(x=anchor_be, color='red', linestyle='--', alpha=0.4, zorder=5)
                if i > 0:
                    ax.axvline(x=curr_pos, color='blue', linestyle=':', alpha=0.7, zorder=5)
                    shift = curr_pos - anchor_be
                    ax.text(0.97, 0.92, f"$\Delta$BE: {shift:+.2f} eV", transform=ax.transAxes, 
                            ha='right', va='top', color='blue', fontweight='bold', 
                            fontsize=10, bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

            # Aesthetics
            ax.text(0.03, 0.88, data_item['label'], transform=ax.transAxes, fontsize=15, fontweight='bold')
            ax.invert_xaxis()
            
            # --- UPDATED Y-AXIS (No Values) ---
            ax.set_ylabel("Intensity (a.u.)", fontweight='bold', fontsize=11)
            ax.set_yticks([]) # This removes the numerical values from the Y-axis
            
            ax.tick_params(direction='in', top=True, right=True, width=1.2)
            for spine in ax.spines.values(): spine.set_linewidth(1.2)

        axes[-1].set_xlabel("Binding Energy (eV)", fontweight='bold', fontsize=12)
        self.fig.tight_layout(rect=[0, 0.03, 1, 0.98])
        
        canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1100x800")
    app = XPSPlotter(root)
    root.mainloop()