This is a demo for how to get a cheatsheet of all Talo voice commands.  

To recreate what I did: 

1. Have talon installed on your computer following the instructions in talonvoice.com
2. Paste both the cheatsheet.py and cheatsheet.talon  into the user directory of ~/talon.  This makes these scripts available to talon. 
3. Open the talon repl and type 

```
actions.user.cheatsheet()
```

This will generate a markdown file.  Currently, the markdown file doesn't look very nice because I am misusing markdown so that when I do the next step, I get containers.
4.  In a shell, I open pandoc and run the command 

```
> pandoc -s cheatsheet.md -c cheatsheet.css -f markdown -t html -o cheatsheet.html
```

and that gets me the output, cheatsheet.html

And finally, what that does is give a webpage that looks ok and is very information-dense when you print it out.  
