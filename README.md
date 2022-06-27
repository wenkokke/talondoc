# Talon Voice Commands Cheatsheet

This is a demo for how to get a cheatsheet of all Talon voice commands.

1. **Install Talon**

   See [Getting Started][talon-getting-started]).

2. **Install Talon Cheatsheet**

   Talon Cheatsheet is written under the assumption that you put the code in your Talon directory,
   _e.g._, `~/.talon`, and that you only copy the code that must be run from within Talon into your
   Talon user directory, _e.g._, `~/.talon/user`.

   On Linux and macOS, run:

   ```bash
   git clone https://github.com/wenkokke/talon-cheatsheet.git ~/.talon/cheatsheet
   cp ~/.talon/cheatsheet/user/cheatsheet ~/.talon/user/cheatsheet
   ```

   On Windows, run:

   ```batch
   git clone https://github.com/wenkokke/talon-cheatsheet.git %AppData%\Talon\cheatsheet
   cp %AppData%\Talon\cheatsheet\user\cheatsheet %AppData%\Talon\user\cheatsheet
   ```

3. **Install docstring_parser** _(Optional)_

   If `docstring_parser` is installed, Talon Cheatsheet will try to parse the docstrings
   on Talon actions as Sphinx docstrings, and use that information to try and interpolate
   short docstrings to give you better, more readable cheatsheets.

   On Linus and macOS, run:

   ```bash
   ~/.talon/bin/pip install docstring_parser
   ```

   On Windows, run:

   ```batch
   %AppData%\Talon\user\bin pip install docstring_parser
   ```

   _This step is not required for the basic functionality._

4. Say `print help` or `print latex help`.

This will generate a self contained HTML or LaTeX file in the repository directory, _e.g._, `~/.talon/cheatsheet`.

# Building the style sheet

The repository contains both a Sass stylesheet, `html/sass/style.sass`, and a precompiled CSS stylesheet, `html/css/style.css`.
When you say `print help`, the generated HTML file, `cheatsheet.html` uses the precompiled CSS stylesheet.

To develop the Sass stylesheet you will need [npm][install-npm].
There is a precompiled HTML file, `cheatsheet-dev.html`, which links to the Sass stylesheet.
To build this file and the linked Sass style sheet, run `npm run dev`.

If you wish to compile only the Sass style sheet, run `npm run build-sass`.

[talon-getting-started]: https://talonvoice.com/docs/index.html#getting-started
[talon-getting-scripts]: https://talonvoice.com/docs/index.html#getting-scripts
[install-npm]: https://nodejs.org/en/
