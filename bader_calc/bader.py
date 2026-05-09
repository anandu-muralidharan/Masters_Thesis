import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd

class BaderAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Bader Charge Analyzer (All Atoms)")
        self.root.geometry("700x600") # Increased height slightly

        # Variables
        self.acf_path = tk.StringVar()
        self.poscar_path = tk.StringVar()
        self.valence_pt = tk.DoubleVar(value=10.0)

        # Title
        tk.Label(root, text="Bader Charge Analysis Tool", font=("Arial", 14, "bold")).pack(pady=10)

        # File Selection
        frame = tk.Frame(root)
        frame.pack(pady=10, padx=20, fill='x')

        tk.Button(frame, text="Select ACF.dat", command=self.load_acf).grid(row=0, column=0, pady=5)
        tk.Entry(frame, textvariable=self.acf_path, width=50).grid(row=0, column=1, padx=5)

        tk.Button(frame, text="Select POSCAR", command=self.load_poscar).grid(row=1, column=0, pady=5)
        tk.Entry(frame, textvariable=self.poscar_path, width=50).grid(row=1, column=1, padx=5)

        tk.Label(frame, text="Pt Valence (from POTCAR):").grid(row=2, column=0, pady=5)
        tk.Entry(frame, textvariable=self.valence_pt).grid(row=2, column=1, sticky='w', padx=5)

        # Action Buttons Frame
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Calculate Charges", command=self.process, bg="green", fg="white", width=20).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Copy Data to Clipboard", command=self.copy_to_clipboard, bg="#2196F3", fg="white", width=20).grid(row=0, column=1, padx=5)

        # Table
        self.tree = ttk.Treeview(root, columns=("Index", "Element", "Bader", "Net"), show='headings')

        self.tree.heading("Index", text="Atom Index")
        self.tree.heading("Element", text="Element")
        self.tree.heading("Bader", text="Bader Charge (e)")
        self.tree.heading("Net", text="Net Charge (Q_net)")

        self.tree.pack(pady=10, fill='both', expand=True)

    # ---------------- FILE LOAD ----------------
    def load_acf(self):
        path = filedialog.askopenfilename()
        if path: self.acf_path.set(path)

    def load_poscar(self):
        path = filedialog.askopenfilename()
        if path: self.poscar_path.set(path)

    # ---------------- COPY TO CLIPBOARD ----------------
    def copy_to_clipboard(self):
        """Copies the table content to the system clipboard in a tab-separated format."""
        # Get column headers
        columns = ["Atom Index", "Element", "Bader Charge (e)", "Net Charge (Q_net)"]
        output = "\t".join(columns) + "\n"
        
        # Get all rows
        rows = self.tree.get_children()
        if not rows:
            messagebox.showwarning("Warning", "No data to copy!")
            return

        for row_id in rows:
            values = self.tree.item(row_id)['values']
            output += "\t".join(map(str, values)) + "\n"

        # Clear clipboard and append data
        self.root.clipboard_clear()
        self.root.clipboard_append(output)
        self.root.update() # Keeps data on clipboard after window closes
        messagebox.showinfo("Success", "Data copied to clipboard! You can now paste into Excel/Notepad.")

    # ---------------- MAIN PROCESS ----------------
    def process(self):
        try:
            if not self.poscar_path.get() or not self.acf_path.get():
                messagebox.showwarning("Input Error", "Please select both files.")
                return

            # ---- Read POSCAR ----
            with open(self.poscar_path.get(), 'r') as f:
                lines = f.readlines()
                atom_types = lines[5].split()
                atom_counts = [int(x) for x in lines[6].split()]

            # Build atom list
            atom_list = []
            for t, count in zip(atom_types, atom_counts):
                atom_list.extend([t] * count)

            # ---- Read ACF.dat ----
            df = pd.read_csv(
                self.acf_path.get(),
                sep=r'\s+',
                skiprows=2,
                skipfooter=4,
                engine='python',
                header=None
            )

            self.tree.delete(*self.tree.get_children())

            results = []

            # ---- Compute for ALL atoms ----
            for idx in range(len(atom_list)):
                element = atom_list[idx]
                bader = df.iloc[idx, 4]

                # Assign valence
                valences = {
                    "O": 6, "H": 1, "C": 4, 
                    "B": 3, "N": 5, "Pt": self.valence_pt.get()
                }
                
                valence = valences.get(element, bader) # fallback to bader if unknown
                net = valence - bader

                results.append((idx + 1, element, round(bader, 4), round(net, 4)))

            # Sort and Insert
            results.sort(key=lambda x: x[0])
            for r in results:
                self.tree.insert("", "end", values=r)

            messagebox.showinfo("Success", "All atomic charges calculated!")

        except Exception as e:
            messagebox.showerror("Error", f"Could not process files:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BaderAnalyzer(root)
    root.mainloop()