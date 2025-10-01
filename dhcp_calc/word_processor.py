# Import necessary libraries
import tkinter as tk
from tkinter import ttk, font, messagebox, filedialog, scrolledtext, colorchooser
from tkinter.font import Font
import os
from tkinter import *
import win32print
import win32api
import tempfile

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from tkinter.ttk import *
from reportlab.platypus import Paragraph

# Class to handle pagination
class PagingSystem:
    def __init__(self, text_area):
        # Initialize the PagingSystem with the text area
        self.text_area = text_area
        self.page_breaks = [1.0]

    def paginate(self):
        # Paginate the document based on a simple line count
        self.page_breaks = [1.0]
        # This is a simple pagination logic, it can be improved
        # for more accurate page breaks based on content height.
        lines = self.text_area.get(1.0, tk.END).split('\n')
        line_count = 0
        for i, line in enumerate(lines):
            line_count += 1
            if line_count > 40:  # Simple assumption of 40 lines per page
                self.page_breaks.append(f"{i+1}.0")
                line_count = 0

    def get_page_content(self, page_num):
        # Get the content of a specific page
        if page_num < 1 or page_num > len(self.page_breaks):
            return ""
        
        start_index = self.page_breaks[page_num - 1]
        end_index = self.page_breaks[page_num] if page_num < len(self.page_breaks) else tk.END
        
        return self.text_area.get(start_index, end_index)

# Main Word Processor class
class WordProcessor:
    def __init__(self):
        # Initialize the main window
        self.root = tk.Tk()
        self.root.title("Python Word Processor")
        self.root.geometry("1200x800")
        
        # Configure the main text area
        self.text_font = Font(family="Arial", size=12)
        self.text_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            undo=True,
            font=self.text_font,
            padx=10,
            pady=5,
            relief=tk.FLAT
        )
        
        # Create UI elements
        self.create_menu_bar()
        self.create_toolbar()
        self.create_status_bar()
        
        # Pack the text area
        self.text_area.pack(expand=True, fill='both')
        
        # Bind events
        self.bind_events()
        
        # Initialize properties
        self.current_file = None
        self.autosave_interval = 30000  # 30 seconds
        self.after_id = None
        
        # Paging System
        self.paging_system = PagingSystem(self.text_area)


    def create_menu_bar(self):
        # Create the menu bar
        menubar = tk.Menu(self.root, background='#f0f0f0', foreground='black', activebackground='#0078d4', activeforeground='white')
        
        # File Menu
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        self.file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        self.file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        self.file_menu.add_command(label="Save As", command=self.save_as_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export to PDF", command=self.export_to_pdf)
        self.file_menu.add_command(label="Export to HTML", command=self.export_to_html)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Print", command=self.print_file, accelerator="Ctrl+P")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit_app)
        menubar.add_cascade(label="File", menu=self.file_menu)
        
        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.text_area.edit_undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.text_area.edit_redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.text_area.event_generate("<<Cut>>"), accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=lambda: self.text_area.event_generate("<<Copy>>"), accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=lambda: self.text_area.event_generate("<<Paste>>"), accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Find and Replace", command=self.show_find_replace_dialog, accelerator="Ctrl+F")
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Format Menu
        format_menu = tk.Menu(menubar, tearoff=0)
        format_menu.add_command(label="Font Color", command=self.choose_font_color)
        format_menu.add_command(label="Highlight Color", command=self.choose_highlight_color)
        format_menu.add_separator()
        format_menu.add_command(label="Indent", command=self.indent_text, accelerator="Ctrl+]")
        format_menu.add_command(label="Outdent", command=self.outdent_text, accelerator="Ctrl+[")
        menubar.add_cascade(label="Format", menu=format_menu)

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Reset Zoom", command=self.reset_zoom, accelerator="Ctrl+0")
        view_menu.add_separator()
        view_menu.add_command(label="Paginate", command=self.paginate_document)
        menubar.add_cascade(label="View", menu=view_menu)

        self.root.config(menu=menubar)

    def create_toolbar(self):
        # Create the toolbar
        toolbar = ttk.Frame(self.root, style='Toolbar.TFrame')
        
        # Font family
        families = sorted(font.families())
        self.font_family = ttk.Combobox(toolbar, values=families, width=20, style='Toolbar.TCombobox')
        self.font_family.set("Arial")
        self.font_family.bind('<<ComboboxSelected>>', self.change_font)
        self.font_family.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Font size
        sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72]
        self.font_size = ttk.Combobox(toolbar, values=sizes, width=5, style='Toolbar.TCombobox')
        self.font_size.set(12)
        self.font_size.bind('<<ComboboxSelected>>', self.change_font)
        self.font_size.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Style buttons
        self.bold_btn = ttk.Button(toolbar, text="B", width=3, command=self.toggle_bold, style='Toolbar.TButton')
        self.bold_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        self.italic_btn = ttk.Button(toolbar, text="I", width=3, command=self.toggle_italic, style='Toolbar.TButton')
        self.italic_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        self.underline_btn = ttk.Button(toolbar, text="U", width=3, command=self.toggle_underline, style='Toolbar.TButton')
        self.underline_btn.pack(side=tk.LEFT, padx=2, pady=5)

        # Alignment buttons
        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, padx=5, fill='y', pady=5)
        
        align_left_btn = ttk.Button(toolbar, text="Left", width=5, command=lambda: self.align_text('left'), style='Toolbar.TButton')
        align_left_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        align_center_btn = ttk.Button(toolbar, text="Center", width=6, command=lambda: self.align_text('center'), style='Toolbar.TButton')
        align_center_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        align_right_btn = ttk.Button(toolbar, text="Right", width=5, command=lambda: self.align_text('right'), style='Toolbar.TButton')
        align_right_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Color buttons
        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, padx=5, fill='y', pady=5)
        
        font_color_btn = ttk.Button(toolbar, text="Color", width=6, command=self.choose_font_color, style='Toolbar.TButton')
        font_color_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        highlight_btn = ttk.Button(toolbar, text="Highlight", width=10, command=self.choose_highlight_color, style='Toolbar.TButton')
        highlight_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        toolbar.pack(fill=tk.X, pady=2)

    def apply_styles(self):
        # Apply styles to the UI elements
        style = ttk.Style()
        style.configure('Toolbar.TFrame', background='#f0f0f0')
        style.configure('Toolbar.TButton', background='#f0f0f0', font=('Arial', 9))
        style.configure('Toolbar.TCombobox', background='#f0f0f0', font=('Arial', 9))
        self.root.option_add('*TCombobox*Listbox.font', ('Arial', 9))


    def create_status_bar(self):
        # Create the status bar
        self.status_bar = ttk.Label(self.root, text="Ready", anchor=tk.W, style='StatusBar.TLabel')
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def bind_events(self):
        # Bind keyboard shortcuts to functions
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-f>', lambda e: self.show_find_replace_dialog())
        self.root.bind('<Control-p>', lambda e: self.print_file())
        self.root.bind('<Control-plus>', self.zoom_in)
        self.root.bind('<Control-minus>', self.zoom_out)
        self.root.bind('<Control-0>', self.reset_zoom)
        self.root.bind('<Control-bracketright>', self.indent_text)
        self.root.bind('<Control-bracketleft>', self.outdent_text)
        self.text_area.bind('<KeyRelease>', self.update_status)

    def new_file(self):
        # Create a new file
        self.text_area.delete(1.0, tk.END)
        self.current_file = None
        self.update_status()

    def open_file(self):
        # Open an existing file
        file_path = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(1.0, file.read())
                self.current_file = file_path
                self.update_status()
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}")

    def save_file(self):
        # Save the current file
        if self.current_file:
            try:
                content = self.text_area.get(1.0, tk.END)
                with open(self.current_file, 'w') as file:
                    file.write(content)
                self.update_status("File saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")
        else:
            self.save_as_file()

    def save_as_file(self):
        # Save the current file with a new name
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            self.current_file = file_path
            self.save_file()

    def export_to_pdf(self):
        # Export the content to a PDF file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if file_path:
            try:
                c = canvas.Canvas(file_path, pagesize=letter)
                width, height = letter
                styles = getSampleStyleSheet()
                style = styles['Normal']
                text = self.text_area.get(1.0, tk.END)
                p = Paragraph(text.replace('\n', '<br/>'), style)
                p.wrapOn(c, width - 100, height)
                p.drawOn(c, 50, height - p.height)
                c.save()
                messagebox.showinfo("Export to PDF", "File exported successfully!")
            except Exception as e:
                messagebox.showerror("Export to PDF", f"Could not export file: {str(e)}")

    def export_to_html(self):
        # Export the content to an HTML file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML Files", "*.html")]
        )
        if file_path:
            try:
                content = self.text_area.get(1.0, tk.END)
                html_content = f"""<!DOCTYPE html>
<html>
<head>
<title>{os.path.basename(file_path)}</title>
</head>
<body>
{content.replace('\n', '<br/>')}
</body>
</html>"""
                with open(file_path, 'w') as file:
                    file.write(html_content)
                messagebox.showinfo("Export to HTML", "File exported successfully!")
            except Exception as e:
                messagebox.showerror("Export to HTML", f"Could not export file: {str(e)}")

    def autosave(self):
        # Automatically save the file at regular intervals
        if self.current_file:
            self.save_file()
        self.after_id = self.root.after(self.autosave_interval, self.autosave)

    def show_find_replace_dialog(self):
        # Show the find and replace dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Find and Replace")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        
        # Find frame
        find_frame = ttk.LabelFrame(dialog, text="Find")
        find_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(find_frame, text="Find:").pack(side=tk.LEFT, padx=5)
        find_entry = ttk.Entry(find_frame)
        find_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Replace frame
        replace_frame = ttk.LabelFrame(dialog, text="Replace")
        replace_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(replace_frame, text="Replace with:").pack(side=tk.LEFT, padx=5)
        replace_entry = ttk.Entry(replace_frame)
        replace_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Options frame
        options_frame = ttk.Frame(dialog)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        case_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Match case", variable=case_var).pack(side=tk.LEFT)
        
        # Buttons frame
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        def find_next():
            # Find the next occurrence of the search text
            search_text = find_entry.get()
            if search_text:
                start_pos = self.text_area.search(
                    search_text, "insert", tk.END,
                    nocase=not case_var.get()
                )
                if start_pos:
                    end_pos = f"{start_pos}+{len(search_text)}c"
                    self.text_area.tag_remove("search", "1.0", tk.END)
                    self.text_area.tag_add("search", start_pos, end_pos)
                    self.text_area.tag_config("search", background="yellow")
                    self.text_area.see(start_pos)
                    self.text_area.mark_set("insert", end_pos)
                else:
                    messagebox.showinfo("Find", "Text not found")
        
        def replace():
            # Replace the current occurrence of the search text
            if self.text_area.tag_ranges("search"):
                self.text_area.delete("search.first", "search.last")
                self.text_area.insert("search.first", replace_entry.get())
                find_next()
        
        def replace_all():
            # Replace all occurrences of the search text
            count = 0
            current_pos = "1.0"
            search_text = find_entry.get()
            replace_text = replace_entry.get()
            
            while True:
                current_pos = self.text_area.search(
                    search_text, current_pos, tk.END,
                    nocase=not case_var.get()
                )
                if not current_pos:
                    break
                end_pos = f"{current_pos}+{len(search_text)}c"
                self.text_area.delete(current_pos, end_pos)
                self.text_area.insert(current_pos, replace_text)
                current_pos = f"{current_pos}+{len(replace_text)}c"
                count += 1
            
            messagebox.showinfo("Replace All", f"Replaced {count} occurrences")
        
        ttk.Button(buttons_frame, text="Find Next", command=find_next).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Replace", command=replace).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Replace All", command=replace_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        find_entry.focus_set()

    def change_font(self, event=None):
        # Change the font of the selected text
        try:
            family = self.font_family.get()
            size = int(self.font_size.get())
            self.text_font.configure(family=family, size=size)
        except:
            pass

    def toggle_bold(self):
        # Toggle bold style for the selected text
        self.apply_tag("bold", font=Font(weight="bold"))

    def toggle_italic(self):
        # Toggle italic style for the selected text
        self.apply_tag("italic", font=Font(slant="italic"))

    def toggle_underline(self):
        # Toggle underline style for the selected text
        self.apply_tag("underline", underline=True)

    def apply_tag(self, tag_name, **kwargs):
        # Apply a tag to the selected text
        try:
            current_tags = self.text_area.tag_names("sel.first")
            if tag_name in current_tags:
                self.text_area.tag_remove(tag_name, "sel.first", "sel.last")
            else:
                self.text_area.tag_add(tag_name, "sel.first", "sel.last")
                self.text_area.tag_configure(tag_name, **kwargs)
        except tk.TclError:
            pass  # No text selected

    def align_text(self, alignment):
        # Align the selected text
        self.text_area.tag_configure(alignment, justify=alignment)
        self.text_area.tag_add(alignment, "sel.first", "sel.last")

    def choose_font_color(self):
        # Choose a font color for the selected text
        color = colorchooser.askcolor()[1]
        if color:
            self.text_area.tag_add("font_color", "sel.first", "sel.last")
            self.text_area.tag_configure("font_color", foreground=color)

    def choose_highlight_color(self):
        # Choose a highlight color for the selected text
        color = colorchooser.askcolor()[1]
        if color:
            self.text_area.tag_add("highlight", "sel.first", "sel.last")
            self.text_area.tag_configure("highlight", background=color)

    def indent_text(self, event=None):
        # Indent the selected text
        self.text_area.tag_add("indent", "sel.first", "sel.last")
        self.text_area.tag_configure("indent", lmargin1=30, lmargin2=30)

    def outdent_text(self, event=None):
        # Outdent the selected text
        self.text_area.tag_add("outdent", "sel.first", "sel.last")
        self.text_area.tag_configure("outdent", lmargin1=0, lmargin2=0)

    def zoom_in(self, event=None):
        # Zoom in the text
        size = self.text_font.cget("size")
        self.text_font.configure(size=size + 2)

    def zoom_out(self, event=None):
        # Zoom out the text
        size = self.text_font.cget("size")
        if size > 2:
            self.text_font.configure(size=size - 2)

    def reset_zoom(self, event=None):
        # Reset the zoom to the default size
        self.text_font.configure(size=12)

    def paginate_document(self):
        # Paginate the document
        self.paging_system.paginate()
        self.update_status()

    def update_status(self, event=None):
        # Update the status bar with information about the document
        position = self.text_area.index(tk.INSERT)
        line, column = position.split('.')
        words = len(self.text_area.get(1.0, tk.END).split())
        
        # Page number
        page_num = 1
        for i, break_point in enumerate(self.paging_system.page_breaks):
            if self.text_area.compare(position, "<", break_point):
                page_num = i
                break
        else:
            page_num = len(self.paging_system.page_breaks)
            
        status = f"Page: {page_num} | Line: {line} | Column: {column} | Words: {words}"
        if self.current_file:
            status += f" | File: {os.path.basename(self.current_file)}"
        self.status_bar.config(text=status)

    def exit_app(self):
        # Exit the application
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.root.destroy()

    def print_file(self):
        # Print the current file
        try:
            # Create a temporary file to print
            temp_file = tempfile.mktemp(".txt")
            with open(temp_file, "w") as f:
                f.write(self.text_area.get(1.0, tk.END))

            # Get the default printer
            printer_name = win32print.GetDefaultPrinter()

            # Print the file
            win32api.ShellExecute(
                0,
                "print",
                temp_file,
                f'/d:"{printer_name}"',
                ".",
                0
            )

        except Exception as e:
            messagebox.showerror("Print Error", f"Could not print file: {str(e)}")

    def apply_styles(self):
        # Apply styles to the UI elements
        style = ttk.Style()
        style.configure('Toolbar.TFrame', background='#f0f0f0')
        style.configure('Toolbar.TButton', background='#f0f0f0', font=('Arial', 9))
        style.configure('Toolbar.TCombobox', background='#f0f0f0', font=('Arial', 9))
        style.configure('StatusBar.TLabel', background='#f0f0f0', font=('Arial', 9))
        self.root.option_add('*TCombobox*Listbox.font', ('Arial', 9))

    def run(self):
        # Run the application
        self.apply_styles()
        self.autosave()
        self.root.mainloop()

if __name__ == "__main__":
    # Create and run the application
    app = WordProcessor()
    app.run()
