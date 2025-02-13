import json
from pathlib import Path

from code_analyzer.domain.documentation import TechnicalDoc


def convert_json_to_md(data: dict[str, TechnicalDoc]) -> str:
    md = ""
    for key, dp in data.items():
        md += dp.to_markdown(key)
    return md


def write_json_as_md(data: dict[str, TechnicalDoc], file_name: Path) -> str:
    title = "# " + " ".join(file_name.parts).replace("_", " ").title()
    write_json(data, file_name=file_name)
    md = convert_json_to_md(data)
    md = title + md
    write_md(md, file_name=file_name)
    return md


def write_md(data: str, file_name: str | Path) -> None:
    output_file = (Path("output") / file_name).with_suffix(".md")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w") as fp:
        fp.write(data)


def read_md(file_name: str | Path) -> str:
    output_file = (Path("output") / file_name).with_suffix(".md")
    with output_file.open("r") as fp:
        return fp.read()


def write_json(data: dict[str, TechnicalDoc], file_name: str | Path) -> None:
    output_file = (Path("output") / file_name).with_suffix(".json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w") as fp:
        serializable = {k: v.model_dump() for k, v in data.items()}
        json.dump(serializable, fp)


def read_json(file_name: str | Path) -> dict[str, TechnicalDoc]:
    output_file = (Path("output") / file_name).with_suffix(".json")
    with output_file.open("r") as fp:
        docs = json.load(fp)
    return {k: TechnicalDoc(**v) for k, v in docs.items()}
