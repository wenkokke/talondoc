# Talon Voice Commands Cheatsheet

This is a demo for how to get a cheatsheet of all Talon voice commands.  

To recreate what I did: 

1. Install Talon on your computer (see [Getting Started][talon-getting-started]).
2. Clone this repository into your Talon user directory (see [Getting Scripts](talon-getting-scripts)).
3. Say `print help` or `phrase print latex help`.

This will generate self contained HTML or LaTeX  file in the repository directory.

# Building the style sheet

The repository contains a prebuilt CSS file which is used in the HTML file. To rebuild the file from source:

1. Install [npm][install-npm]
2. Run `npx parcel build index.html`


[talon-getting-started]: https://talonvoice.com/docs/index.html#getting-started
[talon-getting-scripts]: https://talonvoice.com/docs/index.html#getting-scripts
[install-npm]: https://nodejs.org/en/
