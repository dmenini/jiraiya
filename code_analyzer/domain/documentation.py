from pathlib import Path

from pydantic import BaseModel

STANDALONE_TEMPLATE = """## Module: {module}

### Summary

{summary}

### Analysis

{analysis}

### Usage Notes

{usage}

"""

SUBSECTION_TEMPLATE = """### Submodule: {module}

#### Summary

{summary}

#### Analysis

{analysis}

"""

HEADER_TEMPLATE = """## Module: {module}

#### Summary

{summary}

#### Usage Notes

{usage}

"""

template_map = {
    "standalone": STANDALONE_TEMPLATE,
    "subsection": SUBSECTION_TEMPLATE,
    "header": HEADER_TEMPLATE,
}


class TechnicalDoc(BaseModel):
    summary: str
    analysis: str
    usage: str

    def to_markdown(self, path: str, template: str = "standalone") -> str:
        module_path = Path(path).with_suffix("")
        module = ".".join(module_path.parts)

        md_template = template_map[template]
        return md_template.format(module=module, **self.model_dump())
