import pytest
from pathlib import Path
from src.generator import CVGenerator


@pytest.fixture
def mock_config(tmp_path):
    # tmp_path is already a Path object
    configs_dir = tmp_path / "configs"
    resumes_dir = tmp_path / "resumes"
    output_dir = tmp_path / "dist"
    templates_dir = tmp_path / "templates"

    configs_dir.mkdir()
    resumes_dir.mkdir()
    templates_dir.mkdir()

    return {
        "paths": {
            "configs": str(configs_dir),
            "resumes": str(resumes_dir),
            "output": str(output_dir),
        },
        "template": {"local_path": str(templates_dir / "resume_template.docx")},
    }


def test_find_yaml_extension_logic(mock_config):
    gen = CVGenerator(mock_config)
    config_dir = Path(mock_config["paths"]["configs"])

    # Case 1: Create a .yaml file
    yaml_file = config_dir / "common_fr.yaml"
    yaml_file.write_text("test: true")  # Use write_text instead of touch
    assert gen.find_yaml(str(config_dir), "common_fr").endswith(".yaml")

    # Case 2: Create a .yml file
    yml_file = config_dir / "common_en.yml"
    yml_file.write_text("test: true")
    assert gen.find_yaml(str(config_dir), "common_en").endswith(".yml")


def test_str_to_rich_formatting():
    gen = CVGenerator({"paths": {}, "template": {}})

    # Test Bold
    rich_bold = gen.str_to_rich("Test **Gras**")
    # docxtpl RichText objects convert to XML strings when forced to str
    xml_output = str(rich_bold)
    assert (
        "<w:b/>" in xml_output
        or 'bold="1"' in xml_output
        or "bold" in xml_output.lower()
    )

    # Test Italic
    rich_italic = gen.str_to_rich("Test *Italique*")
    assert "<w:i/>" in str(rich_italic) or "italic" in str(rich_italic).lower()
