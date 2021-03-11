from talon import  Module, actions, registry
import sys, os, pprint 


def write_alphabet(file):
	pp = pprint.PrettyPrinter(indent=2)
	file.write(pp.pformat(registry.lists['user.letter']) + "\n\n")

def write_numbers(file):
	pp = pprint.PrettyPrinter(indent=2)
	file.write(pp.pformat(registry.lists['user.number_key']) + "\n\n")

def write_modifiers(file):
	pp = pprint.PrettyPrinter(indent=2)
	file.write(pp.pformat(registry.lists['user.modifier_key']) + "\n\n")

def write_special(file):
	pp = pprint.PrettyPrinter(indent=2)
	file.write(pp.pformat(registry.lists['user.special_key']) + "\n\n")

def write_formatters(file):
	pp = pprint.PrettyPrinter(indent=2)
	dict_of_formatters = registry.lists['user.formatters'][0].items()
	for key, value in dict_of_formatters:
		file.write( key + ":" + actions.user.formatted_text(f"example of formatting with {key}", key) + "\n")

def write_context_commands(file, commands): 
	# write out each command and it's implementation
	for key in commands:
		rule = commands[key].rule.rule
		implementation = commands[key].target.code.replace("\n","\n\t\t")
		file.write("\n\t" + rule + " : " + implementation)

def pretty_print_context_name(file, name):
	## The logic here is intended to only print from talon files that have actual voice commands.  
		splits = name.split(".")
		index = -1
		if "talon" in splits[index]:
			index = -2
			short_name = splits[index].replace("_", " ")
		else:
			short_name = ""

		file.write("\n\n\n" + "#" + short_name + "\n\n")

mod = Module()

@mod.action_class
class user_actions:
		def cheatsheet():
			"""Print out a sheet of talon commands"""

			

			#open file

			this_dir = os.path.dirname(os.path.realpath(__file__))
			file_path = os.path.join(this_dir, 'cheatsheet.txt')
			file = open(file_path,"w") 


			write_alphabet(file)
			write_numbers(file)
			write_modifiers(file)
			write_special(file)

			write_formatters(file)


			#print out all the commands in all of the contexts

			list_of_contexts = registry.contexts.items()
			for key, value in list_of_contexts:
				
				commands= value.commands #Get all the commands from a context
				if len(commands) > 0:
					pretty_print_context_name(file, key)
					write_context_commands(file,commands)
			file.close()
	