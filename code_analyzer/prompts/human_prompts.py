FIRST_ANALYZER_PROMPT = """The project has the following structure
{structure}

Here is the content of each file:
{codebase}
"""

DEVELOPER_PROMPT = """Please give feedback on the given documentation. Only provide feedback on code belonging to the following code:
        
<Codebase>
{codebase}
</Codebase>

<Documentation>
{docs}
</Documentation>
"""

FOLLOWUP_ANALYZER_PROMPT = """Please generate again the documentation you first provided, improving it according to the following feedback:
{feedback}
"""

FINAL_PROMPT = """Generated Documentation:
{docs}
"""