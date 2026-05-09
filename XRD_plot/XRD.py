import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
import re

def format_chemical_formula(text):
    """
    Automagically wraps numbers in LaTeX subscript format.
    Example: TiO2 -> TiO$_{2}$
    """
    return re.sub(r'(\d+)', r'$_{\1}$', text)

def plot_xrd_final():
    # 1. Ask for Material Name
    material_raw = simpledialog.askstring("Input", "Enter Material Name (e.g., TiO2):")
    if not material_raw:
        return
    
    material_formatted = format_chemical_formula(material_raw)

    # 2. File Selection
    file_path = filedialog.askopenfilename(
        title="Select .asc Data",
        filetypes=[("ASCII files", "*.asc"), ("All files", "*.*")]
    )
    
    if not file_path:
        return

    try:
        df = pd.read_csv(file_path, header=None, sep=r'\s+', engine='python')
        df = df.apply(pd.to_numeric, errors='coerce').dropna()
        x, y = df.iloc[:, 0], df.iloc[:, 1]

        # --- STYLE SETTINGS ---
        DEEP_RED = '#8B0000' 
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.serif'] = ['Times New Roman']
        
        fig, ax = plt.subplots(figsize=(4, 3), dpi=300)
        
        # Plotting
        ax.plot(x, y, color=DEEP_RED, linewidth=2.5)
        ax.fill_between(x, y, color=DEEP_RED, alpha=0.08)

        # 3. ADDING THE COMPOSITION LABEL (Publication Style)
        # Placed in the top-left of the headspace
        ax.text(0.05, 0.90, material_formatted, transform=ax.transAxes, 
                fontsize=14, fontweight='bold', verticalalignment='top', 
                bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))

        # Axes Labels
        ax.set_xlabel(r'2$\theta$ (degrees)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Intensity (a.u.)', fontsize=14, fontweight='bold')

        # Formatting Ticks
        ax.tick_params(direction='in', length=5, width=1.5, top=True, right=True, labelsize=12)
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.tick_params(which='minor', direction='in', length=3, width=1, top=True, right=True)

        # Thickening Frame
        for spine in ax.spines.values():
            spine.set_linewidth(1.8)

        # Headspace for legends/labels
        ax.set_xlim(20,90)
        ax.set_ylim(0, y.max() * 1.35) # Increased to 35% for the label room
        
        plt.tight_layout()

        # Save Logic
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG (Transparent)", "*.png"), ("PDF (Vector)", "*.pdf")],
            title="Save Your Publication Plot"
        )
        
        if save_path:
            plt.savefig(save_path, dpi=600, bbox_inches='tight', transparent=True)
            messagebox.showinfo("Success", "Plot saved with chemical label!")
        
        plt.show()

    except Exception as e:
        messagebox.showerror("Error", f"Failed: {e}")

# GUI
root = tk.Tk()
root.title("XRD Pro Plotter")
root.geometry("300x120")
tk.Button(root, text="Start Plotting Process", command=plot_xrd_final, 
          bg="#8B0000", fg="white", font=('Arial', 10, 'bold'), padx=10, pady=10).pack(pady=25)
root.mainloop()