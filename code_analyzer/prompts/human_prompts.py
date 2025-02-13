WRITER_PROMPT = """The project has the following structure
{structure}

Here is the content of each file:
{codebase}
"""

AUDITOR_PROMPT = """Please give feedback on the given documentation. Only provide feedback on code belonging to the following code:
        
<Codebase>
{codebase}
</Codebase>

<Documentation>
{docs}
</Documentation>
"""

FOLLOWUP_WRITER_PROMPT = """Please generate again the documentation you first provided, improving it according to the following feedback. Do not reference previous versions of the documentation, but explicitly write them again.

{feedback}
"""

INTEGRATION_PROMPT = """Enrich the provided documentation with additional information from the detailed component section. Remember to always provide a self-contained documentation, without references to previous versions.
Documentation to augment:

{documentation}

---

Details for {key}:

{section_detail}
"""
