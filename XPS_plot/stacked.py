import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import matplotlib.pyplot as plt
import re

def get_subscript_name(name):
    return re.sub(r'(\d+)', r'$_{\1}$', name)

def select_data():
    root = tk.Tk()
    root.withdraw()
    
    # --- TOGGLE LOGIC ---
    show_shift = messagebox.askyesno("Preference", "Show Binding Energy shift lines and ΔBE text?")
    
    num_files = simpledialog.askinteger("Input", "How many files to stack?", minvalue=1, maxvalue=10)
    if not num_files: return None, False
    
    data_list = []
    for i in range(num_files):
        path = filedialog.askopenfilename(title=f"Select Excel File for Plot {i+1}")
        if path:
            label = simpledialog.askstring("Label", f"Enter formula for sample {i+1}:")
            data_list.append({'path': path, 'label': get_subscript_name(label or f"Sample {i+1}")})
            
    return data_list, show_shift

def plot_stacked_radical_crop(data_list, show_shift):
    num_plots = len(data_list)
    # Reduced width slightly and kept height compact for better aspect ratio
    fig, axes = plt.subplots(num_plots, 1, figsize=(6.5, 3.2 * num_plots), sharex=True)
    if num_plots == 1: axes = [axes]
    
    plt.subplots_adjust(hspace=0)

    anchor_be = None 

    for i, (ax, item) in enumerate(zip(axes, data_list)):
        try:
            df = pd.read_excel(item['path'], header=None)
            n_cols = df.shape[1]
            
            be_full = df.iloc[:, 0].values
            raw_full = df.iloc[:, 1].values
            bg_full = df.iloc[:, n_cols - 3].values
            env_full = df.iloc[:, n_cols - 2].values
            peak_indices = range(2, n_cols - 3)

            # Radical Crop Logic
            peaks_only = df.iloc[:, peak_indices]
            sum_of_peaks = peaks_only.sum(axis=1).values 
            active_fit = np.where(sum_of_peaks > 1)[0] 
            
            if len(active_fit) == 0:
                s, e = 0, len(be_full)-1
            else:
                s, e = active_fit[0], active_fit[-1]

            be, raw, bg, env = be_full[s:e], raw_full[s:e], bg_full[s:e], env_full[s:e]

            # Calculate positions for the shift lines
            first_peak_data = df.iloc[s:e, 2].values
            current_peak_pos = be[np.argmax(first_peak_data)]
            if i == 0: anchor_be = current_peak_pos

            # --- PLOTTING ---
            ax.scatter(be, raw, s=20, facecolors='none', edgecolors='silver', linewidth=1.0, zorder=1)
            ax.plot(be, bg, color='gray', linestyle='--', linewidth=1.5, zorder=2)

            colors = ['#d62728', '#1f77b4', '#9467bd', '#2ca02c', '#ff7f0e']
            for idx, col_idx in enumerate(peak_indices):
                p_val = df.iloc[s:e, col_idx].values
                ax.plot(be, p_val, color=colors[idx % len(colors)], linewidth=2.0, zorder=3)
                ax.fill_between(be, bg, p_val, color=colors[idx % len(colors)], alpha=0.15, zorder=2)

            ax.plot(be, env, color='black', linewidth=3.0, zorder=10)

            # --- CONDITIONAL SHIFT ELEMENTS ---
            if show_shift:
                # Red dashed line for the anchor (first plot)
                ax.axvline(x=anchor_be, color='red', linestyle='--', linewidth=1.5, alpha=0.7, zorder=11)
                if i > 0:
                    # Blue dotted line for current plot
                    ax.axvline(x=current_peak_pos, color='blue', linestyle=':', linewidth=1.5, zorder=11)
                    shift = current_peak_pos - anchor_be
                    ax.text(0.97, 0.08, f"$\Delta$BE: {shift:+.2f} eV", transform=ax.transAxes, 
                            ha='right', fontsize=11, color='blue', fontweight='bold', 
                            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

            # Formatting
            ax.text(0.03, 0.85, item['label'], transform=ax.transAxes, fontsize=16, fontweight='bold')
            ax.invert_xaxis()
            ax.tick_params(direction='in', top=True, right=True, width=1.5, length=5, labelsize=11)
            ax.set_ylabel('Intensity (a.u.)', fontweight='bold', fontsize=12)
            
            for spine in ax.spines.values():
                spine.set_linewidth(1.5)

        except Exception as ex:
            print(f"Error processing {item['path']}: {ex}")

    axes[-1].set_xlabel('Binding Energy (eV)', fontsize=14, fontweight='bold', labelpad=12)
    
    # Increased bottom margin in rect to prevent "Binding Energy" from clipping
    plt.tight_layout(rect=[0, 0.05, 1, 0.98])
    
    # Save with tight bounding box
    plt.savefig("XPS_Stacked_Plot.pdf", bbox_inches='tight', dpi=300)
    plt.show()

if __name__ == "__main__":
    data, show_shift = select_data()
    if data: 
        plot_stacked_radical_crop(data, show_shift)