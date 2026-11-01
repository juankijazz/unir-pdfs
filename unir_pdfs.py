"""Unir PDFs - une varios PDF en uno solo (GUI para Windows).

Uso:
  - Doble clic: se abre la ventana, añade PDFs, ordénalos y pulsa "Unir".
  - Arrastrar PDFs sobre el .exe: se abren ya cargados en la lista.
  - Línea de comandos: unir_pdfs.exe -o salida.pdf a.pdf b.pdf c.pdf
"""
import os
import sys
import argparse
from pypdf import PdfReader, PdfWriter


def merge_pdfs(paths, output, bookmarks=True, progress=None):
    """Une `paths` en `output`. Devuelve (n_paginas, lista_de_errores)."""
    writer = PdfWriter()
    errors = []
    for i, p in enumerate(paths, 1):
        try:
            reader = PdfReader(p)
            if reader.is_encrypted:
                if reader.decrypt("") == 0:
                    raise ValueError("protegido con contraseña")
            title = os.path.splitext(os.path.basename(p))[0]
            writer.append(reader, outline_item=title if bookmarks else None)
        except Exception as e:  # un PDF malo no debe tumbar todo el proceso
            errors.append((p, str(e)))
        if progress:
            progress(i, len(paths))
    if len(writer.pages) == 0:
        raise ValueError("No se pudo leer ningún PDF.")
    tmp = output + ".tmp"
    with open(tmp, "wb") as f:
        writer.write(f)
    os.replace(tmp, output)  # no deja un archivo a medias si falla
    return len(writer.pages), errors


def run_gui(initial_files):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("Unir PDFs")
    root.geometry("640x460")
    root.minsize(520, 380)

    files = []

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill="both", expand=True)

    list_frame = ttk.Frame(frame)
    list_frame.pack(side="left", fill="both", expand=True)
    lb = tk.Listbox(list_frame, selectmode="extended", activestyle="none")
    sb = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
    lb.configure(yscrollcommand=sb.set)
    lb.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    status = tk.StringVar(value="Añade los PDFs y ordénalos.")
    ttk.Label(root, textvariable=status, anchor="w").pack(fill="x", padx=10)
    bar = ttk.Progressbar(root, mode="determinate")
    bar.pack(fill="x", padx=10, pady=(2, 8))

    def refresh(select=None):
        lb.delete(0, "end")
        for p in files:
            lb.insert("end", p)
        for i in select or []:
            lb.selection_set(i)
        status.set(f"{len(files)} archivo(s) en la lista.")

    def add_files(paths=None):
        paths = paths or filedialog.askopenfilenames(
            title="Selecciona PDFs", filetypes=[("PDF", "*.pdf")])
        for p in paths:
            if p.lower().endswith(".pdf") and os.path.isfile(p):
                files.append(os.path.abspath(p))
        refresh()

    def add_folder():
        d = filedialog.askdirectory(title="Carpeta con PDFs")
        if d:
            names = sorted(n for n in os.listdir(d) if n.lower().endswith(".pdf"))
            add_files([os.path.join(d, n) for n in names])

    def remove():
        for i in reversed(lb.curselection()):
            del files[i]
        refresh()

    def move(delta):
        sel = list(lb.curselection())
        if not sel:
            return
        order = sel if delta < 0 else reversed(sel)
        new_sel = []
        for i in order:
            j = i + delta
            if 0 <= j < len(files) and j not in new_sel and j not in sel:
                files[i], files[j] = files[j], files[i]
                new_sel.append(j)
            else:
                new_sel.append(i)
        refresh(new_sel)

    def sort_names():
        files.sort(key=lambda p: os.path.basename(p).lower())
        refresh()

    bookmarks = tk.BooleanVar(value=True)

    def do_merge():
        if len(files) < 2:
            messagebox.showwarning("Unir PDFs", "Añade al menos 2 PDFs.")
            return
        out = filedialog.asksaveasfilename(
            title="Guardar PDF unido como", defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="unido.pdf",
            initialdir=os.path.dirname(files[0]))
        if not out:
            return
        if os.path.abspath(out) in files:
            messagebox.showerror(
                "Unir PDFs", "El archivo de salida no puede ser uno de los de entrada.")
            return

        def prog(i, n):
            bar["value"] = 100 * i / n
            status.set(f"Procesando {i}/{n}...")
            root.update_idletasks()

        try:
            pages, errors = merge_pdfs(files, out, bookmarks.get(), prog)
        except Exception as e:
            messagebox.showerror("Unir PDFs", f"Error: {e}")
            return
        msg = f"Listo: {pages} páginas.\n{out}"
        if errors:
            msg += "\n\nNo se pudieron incluir:\n" + "\n".join(
                f"- {os.path.basename(p)}: {e}" for p, e in errors)
            messagebox.showwarning("Unir PDFs", msg)
        else:
            messagebox.showinfo("Unir PDFs", msg)
        status.set(f"Guardado: {out}")

    side = ttk.Frame(frame, padding=(10, 0, 0, 0))
    side.pack(side="right", fill="y")
    for text, cmd in [("Añadir PDFs...", add_files), ("Añadir carpeta...", add_folder),
                      ("Quitar", remove), ("Subir", lambda: move(-1)),
                      ("Bajar", lambda: move(1)), ("Ordenar por nombre", sort_names)]:
        ttk.Button(side, text=text, command=cmd).pack(fill="x", pady=2)
    ttk.Checkbutton(side, text="Marcadores por archivo", variable=bookmarks).pack(
        anchor="w", pady=(12, 2))
    ttk.Button(side, text="Unir", command=do_merge).pack(fill="x", pady=(8, 0), ipady=6)

    root.bind("<Delete>", lambda e: remove())
    if initial_files:
        add_files(initial_files)
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description="Une varios PDF en uno.")
    ap.add_argument("files", nargs="*", help="PDFs de entrada (en orden)")
    ap.add_argument("-o", "--output", help="PDF de salida (modo sin ventana)")
    ap.add_argument("--no-bookmarks", action="store_true")
    a = ap.parse_args()
    if a.output:
        if len(a.files) < 2:
            ap.error("Indica al menos 2 PDFs.")
        pages, errors = merge_pdfs(a.files, a.output, not a.no_bookmarks)
        print(f"OK: {pages} páginas -> {a.output}")
        for p, e in errors:
            print(f"AVISO: {p}: {e}", file=sys.stderr)
        sys.exit(1 if errors else 0)
    run_gui(a.files)


if __name__ == "__main__":
    main()
