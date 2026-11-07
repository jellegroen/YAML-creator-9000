YAMLcreator9000

Double-click Start.cmd to open the app
install Python 3 with Tcl/Tk support and add it to PATH.
No additional Python packages are required.


1. Paste dialogue, one message per line:
2. Click Convert / refresh. New characters get a setup window.
3. Choose a key prefix, such as Basil, and either Text only or a faceset.
   Uncheck Text to enter a faceset, such as FA_BASIL_DIALOGUE.
   Skip setup saves that character as text only. Cancel stops conversion.
4. Click Export YAML... to save all messages in one file.


All messages share one title and counter. 
The first speaker's saved key prefix supplies the initial title.
To choose a title or change it midway, put this instruction on its own line: @title kel
The following messages become kel_1, kel_2, kel_3, etc., until another @title.
You can also put @title at the very beginning to override the default title.
Instructions do not appear in the output.
Numbering starts fresh each time you convert/export.


Custom YAML presets

Open Character settings, select a character, and click New preset.
Give it a name, such as custom, then enter your layout in Custom YAML:

{message_id}:
examplefaceset: FACESET
examplefaceindex:
exampletext: {text}

{message_id} becomes the generated message ID.
{text} becomes the dialogue text.
Include {message_id} exactly once. Leave Custom YAML blank to use the standard format.

After saving, switch presets using instructions in the Dialogue box:

@preset FACESET | custom
ExampleCharacter: This uses the custom layout.
@preset FACESET | default
ExampleCharacter: This uses the default layout.

The switch affects only that character's following messages.
Custom presets are saved separately and do not overwrite the default.


Names are matched without regard to capitalization. 
Prefix capitalization is preserved as configured. 
Blank input lines are ignored.


The first colon separates the character from the message. 
Further colons are dialogue. One optional space after the first colon is removed.
Lines without a character and colon are reported as errors.
Lines starting with # are kept exactly as written, between the same messages.
These comments do not count as messages or require character setup. 
Leading spaces before # are also preserved. A # inside dialogue remains dialogue text.


For portrait messages, faceindex: is emitted with no value, for manual editing.
Text-only messages contain just the text field. Facesets stay fixed for each
saved character. Edit them later through Character settings.


Settings are saved in:
  %APPDATA%\YAMLcreator9000\characters.json
Only character settings are saved. Pasted dialogue is not saved automatically.
Copy this JSON file to back up or transfer your templates.


Shortcuts: Ctrl+Enter converts; Ctrl+S exports.
Export replaces the selected file only after the Windows save dialog confirms.


This tool generates YAML; it does not modify your OMORI installation.
Verify portrait indices and dialogue behavior in your mod before distributing it.
