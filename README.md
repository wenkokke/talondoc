# Talon Voice Commands Cheatsheet

This is a demo for how to get a cheatsheet of all Talon voice commands.

To recreate what I did:

1. Install Talon on your computer (see [Getting Started][talon-getting-started]).
2. Clone this repository into your Talon user directory (see [Getting Scripts](talon-getting-scripts)).
3. Install a package that this cheatsheet code relies on by doing `~/.talon/bin/pip install docstring_parser` in your terminal.
4. Say `print help` or `print latex help`.

This will generate self contained HTML or LaTeX  file in the repository directory.

# Building the style sheet

The repository contains both a Sass stylesheet, `style.sass`, and a precompiled CSS stylesheet, `style.css`.
When you say 'print cheatsheet', the generated HTML file, `cheatsheet.html` inlines the precompiled CSS stylesheet.

To develop the Sass stylesheet you will need [npm][install-npm].
There exists a precompiled HTML file, `cheatsheet-dev.html`, which links to the Sass stylesheet.
To build this file and the linked Sass style sheet, run `npm run dev`.

If you wish to compile only the Sass style sheet, run `npm run build-sass`.

[talon-getting-started]: https://talonvoice.com/docs/index.html#getting-started
[talon-getting-scripts]: https://talonvoice.com/docs/index.html#getting-scripts
[install-npm]: https://nodejs.org/en/
