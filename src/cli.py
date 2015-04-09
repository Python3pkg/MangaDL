from clint.textui import puts, indent, prompt, validators


class CLI:
    def __init__(self):
        pass

    def print_header(self):
        """
        Prints the CLI header
        """
        puts("""
                                   ___  __
  /\/\   __ _ _ __   __ _  __ _   /   \/ /
 /    \ / _` | '_ \ / _` |/ _` | / /\ / /
/ /\/\ \ (_| | | | | (_| | (_| |/ /_// /___
\/    \/\__,_|_| |_|\__, |\__,_/___,'\____/
                    |___/
        """)

    def prompt(self):
        """
        Prompt for an action

        :return : An action to perform
        :rtype : str
        """
        self.print_header()
        puts('1. Download new series')
        puts('2. Update existing series')
        puts('3. Create PDF\'s from existing series')
        puts('4. Delete existing series')
        puts('--------------------------------')
        puts('e. Exit\n')

        return prompt.query('What would you like to do?')