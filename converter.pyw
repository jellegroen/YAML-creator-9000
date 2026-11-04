"""Local dialogue-to-YAML editor. Requires Python 3 with Tkinter; no pip packages."""
# Program flow: read pasted lines -> find character templates -> build YAML -> export.

import json
import os
from pathlib import Path
import re
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk


# Save templates under %APPDATA%. If APPDATA is unavailable, use the home folder.
# The / operator on Path objects joins folder and file names.
SETTINGS = Path(os.environ.get('APPDATA', str(Path.home()))) / 'YAMLcreator9000' / 'characters.json'
TITLE_DIRECTIVE = object()
PRESET_DIRECTIVE = object()

FONT_FILE = Path(__file__).resolve().with_name('OMORI_GAME2.ttf')
FONT_FAMILY = 'OMORI_GAME'
COLORS = {
    'ink': '#FFF0D8',       
    'border': '#B96031',    
    'accent': '#FFC17C',    
    'muted': '#7B4027',     
    'surface': '#6B341F',   
    'field': '#48271C',     
    'button': '#EF9950',    
    'pressed': '#D97B38',   
}


def load_app_font():
    if os.name == 'nt' and FONT_FILE.exists():
        import ctypes
        data = FONT_FILE.read_bytes()
        buffer = ctypes.create_string_buffer(data)
        count = ctypes.c_uint()
        register_font = ctypes.windll.gdi32.AddFontMemResourceEx
        register_font.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
                                 ctypes.POINTER(ctypes.c_uint)]
        register_font.restype = ctypes.c_void_p
        register_font(buffer, len(data), None, ctypes.byref(count))


def default_template(name):
    """Create initial settings for a previously unknown character."""
    prefix = re.sub(r'[^\w]+', '_', name.lower(), flags=re.UNICODE).strip('_')
    return {'name': name, 'prefix': prefix or 'message', 'faceset': '', 'text_only': False}


def parse_dialogue(source):
    """Return ordered pairs for dialogue, comments and @title instructions."""
    messages = []
    errors = []
    for number, line in enumerate(source.splitlines(), 1):
        if not line.strip():
            continue
        if line.lstrip().startswith('#'):
            messages.append((None, line))
            continue
        instruction = re.fullmatch(r'@title(?:\s+(.*))?', line.strip(), flags=re.IGNORECASE)
        if instruction:
            prefix = (instruction.group(1) or '').strip()
            if not re.fullmatch(r'[\w-]+', prefix, flags=re.UNICODE):
                errors.append(f'Line {number}: use @title followed by letters, numbers, underscores or hyphens.')
            else:
                messages.append((TITLE_DIRECTIVE, prefix))
            continue
        instruction = re.fullmatch(
            r'@preset(?:\s+(.*))?', line.strip(), flags=re.IGNORECASE
        )
        if instruction:
            character, separator, preset = (
                instruction.group(1) or ''
            ).rpartition('|')
            character = character.strip()
            preset = preset.strip().casefold()

            if not separator or not character or not re.fullmatch(r'[\w-]+', preset):
                errors.append(
                    f'Line {number}: use @preset Character | preset_name'
                  )
            else:
                messages.append((PRESET_DIRECTIVE, (character, preset)))
            continue
        name, separator, text = line.partition(':')
        if not separator or not name.strip():
            errors.append(f'Line {number}: expected Character: message')
            continue
        if text.startswith(' '):
            text = text[1:]
        messages.append((name.strip(), text))
    if errors:
        raise ValueError('\n'.join(errors))
    if not messages:
        raise ValueError('Paste at least one line in the form Character: message.')
    return messages


def render_yaml(messages, templates):
    """Use one active title/counter while portrait settings follow each speaker."""
    # The first speaker supplies the default prefix. @title replaces it and
    # resets the counter. All state is fresh on each conversion/preview refresh.
    prefix, count = None, 0
    keys, blocks = set(), []
    active_presets = {}
    for name, text in messages:
        if name is None:
            blocks.append(text)
            continue
        if name is TITLE_DIRECTIVE:
            prefix, count = text, 0
            continue
        
        if name is PRESET_DIRECTIVE:
            character, preset = text
            identity = character.casefold()

            if preset == 'default':
                active_presets.pop(identity, None)
            else:
                preset_key = f'{identity}::{preset}'
                if preset_key not in templates:
                    raise ValueError(
                        f'{character}: preset "{preset}" does not exist. '
                        'Create it in Character settings.'
                    )
                active_presets[identity] = preset_key
            continue
        identity = name.casefold()
        template = templates[active_presets.get(identity, identity)]
        if prefix is None:
            prefix = template['prefix']
        if not re.fullmatch(r'[\w-]+', prefix, flags=re.UNICODE):
            raise ValueError(f'{name}: key prefix must contain only letters, numbers, underscores or hyphens.')
        count += 1
        key = f'{prefix}_{count}'
        if key in keys:
            raise ValueError(f'Duplicate key {key}. Use a different @title name for each new section.')
        keys.add(key)
        fields = [f'{key}:']
        if not template['text_only']:
            if not template['faceset'].strip():
                raise ValueError(f'{name}: enter a faceset or select Text only in Character settings.')
            fields += [f'  faceset: {template["faceset"]}', '  faceindex:']
        fields.append(f'  text: {text}')
        blocks.append('\n'.join(fields))
    return '\n\n'.join(blocks) + '\n'


class TemplateDialog(tk.Toplevel):
    """A smaller window for setting up or editing one character."""
    def __init__(self, parent, name, template, allow_skip=False):
        super().__init__(parent)
        self.configure(background=COLORS['surface'])
        self.title(f'Character settings: {name}')
        self.resizable(False, False)
        self.transient(parent)
        # The caller checks result after the dialog closes. None means cancelled.
        self.result = None
        self.name = name
        # Frames group controls. grid positions them in rows and columns.
        body = ttk.Frame(self, padding=24)
        body.grid(sticky='nsew')
        ttk.Label(body, text=name, style='Heading.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 16))
        # Tk variables connect input controls to values readable with .get().
        self.prefix = tk.StringVar(value=template['prefix'])
        self.faceset = tk.StringVar(value=template['faceset'])
        self.text_only = tk.BooleanVar(value=template['text_only'])
        ttk.Label(body, text='Key prefix').grid(row=1, column=0, sticky='w', padx=(0, 20))
        prefix_entry = ttk.Entry(body, textvariable=self.prefix, width=36)
        prefix_entry.grid(row=1, column=1, pady=6)
        ttk.Label(body, text='Faceset').grid(row=2, column=0, sticky='w')
        self.face_entry = ttk.Entry(body, textvariable=self.faceset, width=36)
        self.face_entry.grid(row=2, column=1, pady=6)
        ttk.Checkbutton(body, text='Text only', variable=self.text_only, command=self.toggle).grid(row=3, column=1, sticky='w', pady=8)
        ttk.Label(body, text='Faceindex is left blank for manual editing.').grid(row=4, column=0, columnspan=2, sticky='w', pady=(4, 20))
        buttons = ttk.Frame(body)
        buttons.grid(row=5, column=0, columnspan=2, sticky='e')
        # command names the function to run when a button is clicked.
        # destroy closes the window. pack places these buttons side by side.
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side='left', padx=4)
        if allow_skip:
            ttk.Button(buttons, text='Skip setup', command=self.skip).pack(side='left', padx=4)
        ttk.Button(buttons, text='Save character', command=self.save).pack(side='left', padx=4)
        # bind attaches keyboard actions. lambda is a short unnamed function;
        # it accepts Tkinter's event argument and calls the action we want.
        self.bind('<Escape>', lambda event: self.destroy())
        self.bind('<Return>', lambda event: self.save())
        self.toggle()
        # Keep interaction in this dialog until it closes. wait_window pauses
        # the caller while Tkinter continues responding to dialog actions.
        self.grab_set()
        prefix_entry.focus_set()
        self.wait_window()

    def toggle(self):
        """Disable the unused faceset field when text-only mode is selected."""
        self.face_entry.configure(state='disabled' if self.text_only.get() else 'normal')

    def skip(self):
        """Return default text-only settings and close the dialog."""
        self.result = default_template(self.name)
        self.result['text_only'] = True
        self.destroy()

    def save(self):
        """Check the entered values, return the template, then close the dialog."""
        prefix, faceset = self.prefix.get().strip(), self.faceset.get().strip()
        if not re.fullmatch(r'[\w-]+', prefix, flags=re.UNICODE):
            messagebox.showerror('Check key prefix', 'Use letters, numbers, underscores or hyphens.', parent=self)
            return
        if not self.text_only.get() and not faceset:
            messagebox.showerror('Faceset needed', 'Enter a faceset, or select Text only.', parent=self)
            return
        # Only valid values reach this point. The caller saves this dictionary.
        self.result = {'name': self.name, 'prefix': prefix, 'faceset': faceset, 'text_only': self.text_only.get()}
        self.destroy()


class App(tk.Tk):
    """The main window, its controls, and the actions connected to those controls."""
    def __init__(self):
        load_app_font()
        super().__init__()
        self.title('OMORI Dialogue Converter')
        self.geometry('1120x720')
        self.minsize(820, 520)
        self.configure(background=COLORS['surface'])
        # Tk named fonts also cover entries, menus and Tk-managed popup text.
        for font_name in tkfont.names(self):
            tkfont.nametofont(font_name, root=self).configure(family=FONT_FAMILY)
        tkfont.nametofont('TkDefaultFont', root=self).configure(size=16)
        tkfont.nametofont('TkTextFont', root=self).configure(size=18)
        self.option_add('*Font', (FONT_FAMILY, 16))
        self.option_add('*Background', COLORS['surface'])
        self.option_add('*Foreground', COLORS['ink'])
        self.option_add('*selectBackground', COLORS['accent'])
        self.option_add('*selectForeground', COLORS['surface'])
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=(FONT_FAMILY, 16), background=COLORS['surface'],
                        foreground=COLORS['ink'], bordercolor=COLORS['border'],
                        lightcolor=COLORS['surface'], darkcolor=COLORS['border'],
                        focuscolor=COLORS['accent'], selectbackground=COLORS['accent'],
                        selectforeground=COLORS['surface'])
        style.configure('TButton', padding=(12, 7), background=COLORS['button'],
                        foreground=COLORS['surface'])
        style.map('TButton', background=[('pressed', COLORS['pressed']), ('active', COLORS['accent'])],
                  foreground=[('pressed', COLORS['surface']), ('active', COLORS['surface'])])
        style.configure('Heading.TLabel', font=(FONT_FAMILY, 24), foreground=COLORS['accent'])
        style.configure('Section.TLabel', font=(FONT_FAMILY, 18), foreground=COLORS['accent'])
        style.configure('TEntry', fieldbackground=COLORS['field'], insertcolor=COLORS['ink'])
        style.map('TEntry', fieldbackground=[('disabled', COLORS['muted'])],
                  foreground=[('disabled', COLORS['ink'])],
                  bordercolor=[('focus', COLORS['accent'])],
                  lightcolor=[('focus', COLORS['accent'])], darkcolor=[('focus', COLORS['accent'])])
        style.configure('TCheckbutton', indicatorbackground=COLORS['field'],
                        indicatorforeground=COLORS['ink'])
        style.map('TCheckbutton', background=[('active', COLORS['muted'])],
                  indicatorforeground=[('selected', COLORS['surface'])],
                  indicatorbackground=[('selected', COLORS['accent']), ('active', COLORS['muted'])])
        style.configure('Vertical.TScrollbar', background=COLORS['border'],
                        troughcolor=COLORS['surface'], arrowcolor=COLORS['ink'])
        style.map('Vertical.TScrollbar', background=[('pressed', COLORS['pressed']), ('active', COLORS['button'])],
                  arrowcolor=[('pressed', COLORS['surface']), ('active', COLORS['surface'])])
        style.configure('TPanedwindow', background=COLORS['muted'])
        style.configure('Treeview', font=(FONT_FAMILY, 16), rowheight=30,
                        fieldbackground=COLORS['field'], background=COLORS['field'])
        style.map('Treeview', background=[('selected', COLORS['accent'])],
                  foreground=[('selected', COLORS['surface'])])
        style.configure('Treeview.Heading', font=(FONT_FAMILY, 16), background=COLORS['muted'])
        style.map('Treeview.Heading', background=[('active', COLORS['border'])])
        # App state: saved templates, whether the preview is current, and the
        # identifier of any scheduled preview update. {} is an empty dictionary.
        self.templates = {}
        self.load_settings()
        self.preview_valid = False
        self.timer = None
        # Build the title area. pack(fill=..., expand=True) lets widgets grow
        # with their container when the user resizes the window.
        outer = ttk.Frame(self, padding=22)
        outer.pack(fill='both', expand=True)
        header = ttk.Frame(outer)
        header.pack(fill='x', pady=(0, 8))
        ttk.Label(header, text='YAML CREATOR 9000', style='Heading.TLabel').pack(side='left')
        ttk.Button(header, text='Character settings', command=self.manage_characters).pack(side='right')
        ttk.Label(outer, text='One Character: message per line. Use @title (name) to switch entry titles.').pack(anchor='w', pady=(0, 18))
        # A draggable divider separates the editable input and read-only preview.
        panes = ttk.Panedwindow(outer, orient='horizontal')
        panes.pack(fill='both', expand=True)
        self.input = self.make_editor(panes, 'Dialogue', editable=True)
        self.output = self.make_editor(panes, 'YAML preview', editable=False)
        # Ask Tkinter to call on_edit whenever the dialogue text changes.
        self.input.bind('<<Modified>>', self.on_edit)
        actions = ttk.Frame(outer)
        actions.pack(fill='x', pady=(16, 10))
        ttk.Button(actions, text='Convert / refresh', command=lambda: self.convert(True)).pack(side='left')
        ttk.Button(actions, text='Copy YAML', command=self.copy_yaml).pack(side='left', padx=8)
        ttk.Button(actions, text='Export YAML...', command=self.export_yaml).pack(side='right')
        # Changing this variable automatically updates the status label.
        self.status = tk.StringVar(value='Paste dialogue to begin.')
        ttk.Label(outer, textvariable=self.status, wraplength=1000).pack(anchor='w')
        self.bind('<Control-Return>', lambda event: self.convert(True))
        self.bind('<Control-s>', lambda event: self.export_yaml())

    def make_editor(self, parent, title, editable):
        """Create a labeled text box with a scrollbar; used for both panels."""
        frame = ttk.Frame(parent, padding=(0, 0, 10, 0))
        parent.add(frame, weight=1)
        ttk.Label(frame, text=title, style='Section.TLabel').pack(anchor='w', pady=(0, 8))
        container = ttk.Frame(frame)
        container.pack(fill='both', expand=True)
        text = tk.Text(container, wrap='word', undo=editable, font=(FONT_FAMILY, 18),
                       background=COLORS['field'], foreground=COLORS['ink'],
                       insertbackground=COLORS['accent'], selectbackground=COLORS['accent'],
                       selectforeground=COLORS['surface'], highlightbackground=COLORS['border'],
                       highlightcolor=COLORS['accent'],
                       relief='solid', borderwidth=1, padx=12, pady=12)
        # Connect both directions: dragging scrolls the text; scrolling the text
        # updates the scrollbar's position. Word wrapping only affects display.
        scrollbar = ttk.Scrollbar(container, command=text.yview)
        scrollbar.pack(side='right', fill='y')
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(fill='both', expand=True)
        if not editable:
            text.configure(state='disabled')
        return text

    def load_settings(self):
        """Read saved character templates, if a settings file already exists."""
        if not SETTINGS.exists():
            return
        try:
            data = json.loads(SETTINGS.read_text(encoding='utf-8'))
            for identity, template in data.items():
                # Require text for the three text fields and True/False for text_only.
                if not isinstance(template, dict) or not all(isinstance(template.get(k), str) for k in ('name', 'prefix', 'faceset')) or not isinstance(template.get('text_only'), bool):
                    raise ValueError('Invalid character settings.')
            self.templates = data
        # Catch unreadable or malformed settings and report them 
        except (OSError, ValueError, AttributeError) as error:
            messagebox.showwarning('Settings could not be loaded', f'{error}\n\nYour settings file has not been changed.\n{SETTINGS}', parent=self)

    def persist(self):
        """Write character templates to disk so they survive closing the app."""
        try:
            # Create the folder if needed. Write a temporary file before replacing
            # the previous settings, reducing the risk of a partly written file.
            SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            temporary = SETTINGS.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.templates, indent=2, ensure_ascii=False), encoding='utf-8')
            temporary.replace(SETTINGS)
        except OSError as error:
            messagebox.showerror('Settings could not be saved', str(error), parent=self)

    def on_edit(self, event=None):
        """Clear the stale preview and schedule a refresh after typing pauses."""
        if not self.input.edit_modified():
            return
        # Reset Tkinter's change flag so the next real edit can be detected.
        self.input.edit_modified(False)
        self.preview_valid = False
        self.set_preview('')
        self.status.set('Dialogue changed. Updating preview...')
        # Cancel the previous scheduled refresh. after schedules work without
        # freezing the window; each edit restarts the 400 millisecond delay.
        if self.timer:
            self.after_cancel(self.timer)
        self.timer = self.after(400, self.auto_preview)

    def auto_preview(self):
        """Refresh without opening character setup dialogs while someone types."""
        self.timer = None
        self.convert(False)

    def set_preview(self, value):
        """Temporarily unlock the preview to replace its contents, then lock it."""
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        self.output.insert('1.0', value)
        self.output.configure(state='disabled')

    def convert(self, interactive=True):
        """Coordinate parsing, character setup and rendering; return success/failure."""
        # Manual conversion supersedes any automatic conversion still waiting.
        if self.timer:
            self.after_cancel(self.timer)
            self.timer = None
        self.preview_valid = False
        try:
            # Tk text positions: 1.0 is the start, end-1c excludes the extra final
            # newline that Tkinter maintains internally in every text widget.
            messages = parse_dialogue(self.input.get('1.0', 'end-1c'))
            unknown = list(dict.fromkeys(name for name, _ in messages if isinstance(name, str) and name.casefold() not in self.templates))
            # Treat differently capitalized names as the same character.
            for name in unknown:
                if name.casefold() in self.templates:
                    continue
                if not interactive:
                    self.set_preview('')
                    self.status.set('New characters found. Click Convert / refresh to configure them or skip setup.')
                    return False
                # This constructor waits for the dialog to close before returning.
                dialog = TemplateDialog(self, name, default_template(name), allow_skip=True)
                if dialog.result is None:
                    self.set_preview('')
                    self.status.set('Conversion cancelled. Your dialogue is still here.')
                    return False
                # Save both configured templates and skipped text-only templates.
                self.templates[name.casefold()] = dialog.result
                self.persist()
            result = render_yaml(messages, self.templates)
        # Handle input/template errors from parse_dialogue and render_yaml.
        except ValueError as error:
            self.set_preview('')
            self.status.set(str(error).splitlines()[0])
            if interactive:
                messagebox.showerror('Check dialogue or settings', str(error), parent=self)
            return False
        self.set_preview(result)
        self.preview_valid = True
        # The underscore means the second item of each pair is not needed.
        message_count = sum(isinstance(name, str) for name, _ in messages)
        self.status.set(f'{message_count} messages ready. Faceindex fields are blank. Numbering restarts on each export.')
        return True

    def copy_yaml(self):
        """Convert current input first, then copy the result to the clipboard."""
        if self.convert(True):
            self.clipboard_clear()
            self.clipboard_append(self.output.get('1.0', 'end-1c'))
            self.status.set('YAML copied to clipboard.')

    def export_yaml(self):
        """Convert, ask for a destination, then write the preview to a UTF-8 file."""
        if not self.convert(True):
            return
        destination = filedialog.asksaveasfilename(parent=self, title='Export dialogue', defaultextension='.yaml', initialfile='dialogue.yaml', filetypes=[('YAML files', '*.yaml *.yml'), ('All files', '*.*')])
        # An empty destination means the user cancelled the save dialog.
        if not destination:
            return
        try:
            # newline='\n' uses consistent line endings in the exported file.
            Path(destination).write_text(self.output.get('1.0', 'end-1c'), encoding='utf-8', newline='\n')
            self.status.set(f'Exported to {destination}')
        except OSError as error:
            messagebox.showerror('Export failed', str(error), parent=self)

    def manage_characters(self):
        """Open the saved-character list with actions to edit or remove templates."""
        window = tk.Toplevel(self)
        window.configure(background=COLORS['surface'])
        window.title('Saved character settings')
        window.geometry('640x400')
        window.transient(self)
        frame = ttk.Frame(window, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Saved characters', style='Heading.TLabel').pack(anchor='w', pady=(0, 12))
        # Treeview is a table-like control. Its built-in first column is named #0.
        tree = ttk.Treeview(frame, columns=('prefix', 'faceset'), show='tree headings', selectmode='browse')
        tree.heading('#0', text='Character')
        tree.heading('prefix', text='Key prefix')
        tree.heading('faceset', text='Faceset / text only')
        for col in ('#0', 'prefix', 'faceset'):
            tree.column(col, width=170)
        tree.pack(fill='both', expand=True)
        
        def refresh():
            """Rebuild the table using the current templates, sorted by identity."""
            # * expands the child IDs into separate arguments for delete().
            tree.delete(*tree.get_children())
            for identity, template in sorted(self.templates.items()):
                preset_name = identity.partition('::')[2] or 'default'
                tree.insert(
                    '', 'end',
                    iid=identity,
                    text=f'{template["name"]} [{preset_name}]',
                    values=(
                        template['prefix'],
                        'Text only' if template['text_only'] else template['faceset']
                    )
                )

        def new_preset():
            selected = tree.selection()
            if not selected:
                messagebox.showinfo(
                    'Select a character',
                    'Select a character to copy into a new preset.',
                    parent=window
                )
                return

            identity = selected[0]
            original = self.templates[identity]
            character_identity = identity.split('::', 1)[0]

            preset_name = simpledialog.askstring(
                'New preset',
                f'Name the new preset for {original["name"]}:',
                parent=window
            )
            if preset_name is None:
                return

            preset_name = preset_name.strip().casefold()
            if (
                preset_name == 'default'
                or not re.fullmatch(r'[\w-]+', preset_name)
            ):
                messagebox.showerror(
                    'Invalid preset name.',
                    'Use letters, numbers, underscores or hyphens. '
                    '"default" is reserved.',
                    parent=window
                )
                return

            preset_key = f'{character_identity}::{preset_name}'
            if preset_key in self.templates:
                messagebox.showerror(
                    'Preset already exists',
                    'Choose another name, or select that preset and click edit selected.',
                    parent=window
                )
                return

            dialog = TemplateDialog(
                window,
                original['name'],
                original.copy()
            )
            if dialog.result is None:
                return

            self.templates[preset_key] = dialog.result
            self.persist()
            refresh()
            self.convert(False)

        def edit():
            """Edit the selected template, save it, and refresh the list/preview."""
            selected = tree.selection()
            if not selected:
                return
            identity = selected[0]
            template = self.templates[identity]
            dialog = TemplateDialog(window, template['name'], template)
            if dialog.result:
                self.templates[identity] = dialog.result
                self.persist()
                refresh()
                self.convert(False)

        def remove():
            """Remove a saved template after confirmation; dialogue is untouched."""
            selected = tree.selection()
            if selected and messagebox.askyesno('Remove saved character?', 'The next conversion will ask you to set up this character again.', parent=window):
                del self.templates[selected[0]]
                self.persist()
                refresh()
                self.convert(False)

        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=(12, 0))
        ttk.Button(buttons, text='New preset', command=new_preset).pack(side='left', padx=(0, 8))
        ttk.Button(buttons, text='Edit selected', command=edit).pack(side='left')
        ttk.Button(buttons, text='Remove selected', command=remove).pack(side='left', padx=8)
        ttk.Button(buttons, text='Close', command=window.destroy).pack(side='right')
        # Double-clicking a row is a shortcut for Edit selected.
        tree.bind('<Double-1>', lambda event: edit())
        refresh()


# Run the window only when this file is launched directly. Importing it from
# tests makes its functions available without automatically opening a window.
if __name__ == '__main__':
    # mainloop keeps the app responsive and dispatches clicks, typing and timers.
    App().mainloop()
