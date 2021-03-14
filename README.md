This is a demo for how to get a cheatsheet of all Talon voice commands.  

To recreate what I did: 

1. Have talon installed on your computer following the instructions at [talonvoice.com](https://talonvoice.com/docs/index.html#getting-started)
2. Paste both the cheatsheet.py and cheatsheet.talon  into the user directory of ~/talon.  This makes these scripts available to talon. 
3. Open the talon repl and type 

```
actions.user.cheatsheet()
```

This will generate a markdown file in the same directory you put cheatsheet.py.  Currently, the markdown file doesn't look very nice because I am misusing markdown so that when I do the next step, I get containers around the html I generate that are easy to select with css selectors.  It woud probably be better to just have the python script create html in the first place, or even 
4.  In a shell, I open pandoc and run the command 

```
> pandoc -s cheatsheet.md -c cheatsheet.css -f markdown -t html -o cheatsheet.html
```

This command says "create a standalone document (-s) from the markdown document cheatsheet.md  markdown (cheatsheet.md -f markdown) to html (-t html) with the css styleshees cheatsheet.css (-c cheatsheet.css)"

And that gets me the output, cheatsheet.html

This creates a wepbate that when you print it, has make a twenty-four page document with every talon command on it, formatted in a way where it is easy to find things, very information-dense, and organized.  