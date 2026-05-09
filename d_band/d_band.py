import tkinter as tk
from tkinter import filedialog, ttk, simpledialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

DATA_FILE = "d_band_results.xlsx"

file_data = []

# ✅ GLOBAL PDOS COLUMN SETTING
pdos_columns = [5, 6, 7, 8, 9]   # default


# ------------------ Persistence ------------------
def save_data():
    df = pd.DataFrame(file_data)
    df.to_excel(DATA_FILE, index=False)


def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE)
        for _, row in df.iterrows():
            file_data.append({
                "path": row["path"],
                "name": row["name"],
                "d_center": row.get("d_center", None)
            })


# ------------------ Column Selector ------------------
def set_columns():
    global pdos_columns

    user_input = simpledialog.askstring(
        "PDOS Columns",
        "Enter PDOS columns:\nExamples:\n5,6,7,8,9\nor\n5-9"
    )

    if not user_input:
        return

    try:
        if "-" in user_input:
            start, end = map(int, user_input.split("-"))
            pdos_columns = list(range(start, end + 1))
        else:
            pdos_columns = list(map(int, user_input.split(",")))

        messagebox.showinfo("Success", f"Using columns: {pdos_columns}")

    except:
        messagebox.showerror("Error", "Invalid input format!")


# ------------------ Core calculation ------------------
def calculate_d_center(energy, pdos):

    mask = (energy >= -7) & (energy <= 0)

    energy_occ = energy[mask]
    pdos_occ = pdos[mask]

    if len(energy_occ) == 0:
        return None

    numerator = np.trapz(energy_occ * pdos_occ, energy_occ)
    denominator = np.trapz(pdos_occ, energy_occ)

    if denominator == 0:
        return None

    return numerator / denominator


# ------------------ File handling ------------------
def add_files():
    files = filedialog.askopenfilenames(title="Select PDOS files")

    for f in files:
        if not any(d["path"] == f for d in file_data):
            file_data.append({
                "path": f,
                "name": os.path.basename(f),
                "d_center": None
            })

    update_table()
    save_data()


def clear_files():
    if messagebox.askyesno("Confirm", "Clear all entries?"):
        file_data.clear()
        update_table()
        save_data()


def delete_selected():
    selected = table.selection()
    if not selected:
        return

    for item in selected:
        index = table.index(item)
        file_data.pop(index)

    update_table()
    save_data()


def rename_entry():
    selected = table.selection()
    if not selected:
        return

    index = table.index(selected[0])
    old_name = file_data[index]["name"]

    new_name = simpledialog.askstring("Rename", f"Rename '{old_name}' to:")

    if new_name:
        file_data[index]["name"] = new_name
        update_table()
        save_data()


# ------------------ Table update ------------------
def update_table():
    for row in table.get_children():
        table.delete(row)

    for d in file_data:
        value = f"{d['d_center']:.3f}" if d["d_center"] is not None else "Pending"
        table.insert("", "end", values=(d["name"], value))


# ------------------ Compute ------------------
def compute_and_plot():

    fig_pdos, ax_pdos = plt.subplots(figsize=(7, 5))

    colors = ["#ff6b6b", "#4c9aff", "#5ac878", "#ffb347", "#c678dd"]

    for i, d in enumerate(file_data):

        file = d["path"]
        label = d["name"]

        try:
            df = pd.read_csv(file, sep=r"\s+", header=None, engine="python")
            df = df.apply(pd.to_numeric, errors="coerce").dropna()

            if df.empty:
                raise ValueError("Empty file")

        except Exception as e:
            print(f"Error in {file}: {e}")
            continue

        try:
            energy = df.iloc[:, 0].values
            pdos = df.iloc[:, pdos_columns].sum(axis=1).values

        except Exception as e:
            print(f"Column error in {file}: {e}")
            continue

        temp = pd.DataFrame({"E": energy, "DOS": pdos}).sort_values("E")

        energy = temp["E"].values
        pdos = temp["DOS"].values

        d_center = calculate_d_center(energy, pdos)

        file_data[i]["d_center"] = d_center

        color = colors[i % len(colors)]

        ax_pdos.plot(energy, pdos, label=label, color=color)

        if d_center is not None:
            ax_pdos.axvline(d_center, linestyle="--", color=color)

    save_data()
    update_table()

    ax_pdos.axvline(0, color="black", linewidth=2, label="Fermi level")

    ax_pdos.set_xlim(-8, 2)
    ax_pdos.set_xlabel("Energy (E − Ef) [eV]")
    ax_pdos.set_ylabel("d-PDOS (states/eV)")
    ax_pdos.legend()
    ax_pdos.grid(alpha=0.3)

    plt.title("Pt d-PDOS and d-band center")
    plt.tight_layout()
    plt.show()

    plot_comparison()


def plot_comparison():
    systems = [d["name"] for d in file_data]
    centers = [d["d_center"] if d["d_center"] is not None else np.nan for d in file_data]

    plt.figure(figsize=(6, 4))
    plt.plot(systems, centers, marker="o", linewidth=2)

    plt.ylabel("d-band center (eV)")
    plt.xlabel("Catalyst System")
    plt.xticks(rotation=45)
    plt.grid(alpha=0.3)

    plt.title("d-Band Center Comparison")
    plt.tight_layout()
    plt.show()


# ------------------ GUI ------------------
root = tk.Tk()
root.title("Pt d-Band Center Tracker")
root.geometry("850x550")

title = tk.Label(root, text="Pt d-Band Center Evolution", font=("Arial", 18))
title.pack(pady=10)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="Add Files", command=add_files, width=15).grid(row=0, column=0, padx=5)
tk.Button(btn_frame, text="Delete Selected", command=delete_selected, width=18).grid(row=0, column=1, padx=5)
tk.Button(btn_frame, text="Clear All", command=clear_files, width=15).grid(row=0, column=2, padx=5)
tk.Button(btn_frame, text="Rename", command=rename_entry, width=15).grid(row=0, column=3, padx=5)
tk.Button(btn_frame, text="Set PDOS Columns", command=set_columns, width=18).grid(row=0, column=4, padx=5)
tk.Button(btn_frame, text="Compute & Plot", command=compute_and_plot, width=18).grid(row=0, column=5, padx=5)

columns = ("System", "d-band center (eV)")
table = ttk.Treeview(root, columns=columns, show="headings")

for col in columns:
    table.heading(col, text=col)
    table.column(col, width=350)

table.pack(expand=True, fill="both", padx=20, pady=20)


# Load previous session
load_data()
update_table()

root.mainloop()