import yaml
import os
import logging
import re
from glob import glob
from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict, ValidationError
from docxtpl import DocxTemplate, RichText, Listing

logger = logging.getLogger(__name__)

# --- DATA SCHEMAS (PYDANTIC) ---


class Task(BaseModel):
    context: str
    stack: Optional[str] = ""
    bullets: List[str] = []


class Experience(BaseModel):
    title: str
    company: str
    dates: str
    tasks: List[Task] = []


class CVModel(BaseModel):
    model_config = ConfigDict(extra="allow")  # This is the V2 way
    filename: str
    lang: str = "fr"
    common_file: str
    role_title: str
    skills: Dict[str, str]
    experiences: List[Experience]


# --- GENERATOR ---


class CVGenerator:
    def __init__(self, config):
        paths = config.get("paths", {})
        tpl = config.get("template", {})
        self.config_dir = paths.get("configs", "configs")
        self.resumes_dir = paths.get("resumes", "resumes")
        self.output_dir = paths.get("output", "dist")
        self.template_path = tpl.get("local_path", "templates/resume_template.docx")

    def str_to_rich(self, text: str) -> RichText:
        """
        Parses Markdown-like syntax for **bold** and *italic* into Word RichText.
        """
        if not text:
            return ""
        if "**" not in text and "*" not in text:
            return Listing(text) if "\n" in text else text

        rt = RichText()
        # Regex split on bold and italic markers
        parts = re.split(r"(\*\*.*?\*\*|\*.*?\*)", text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                rt.add(part[2:-2], bold=True)
            elif part.startswith("*") and part.endswith("*"):
                rt.add(part[1:-1], italic=True)
            else:
                rt.add(part)
        return rt

    def load_yaml(self, path: str):
        """Loads a YAML file with UTF-8 encoding."""
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def find_yaml(self, directory: str, filename: str):
        """Looks for a specific YAML file with .yaml or .yml extension."""
        for ext in (".yaml", ".yml"):
            path = os.path.join(directory, f"{filename}{ext}")
            if os.path.exists(path):
                return path
        return None

    def process_skills(self, skills: Dict[str, str]) -> Dict[str, str]:
        """
        Formats skill categories (removes underscores) and applies RichText formatting.
        """
        processed = {}
        for category, value in skills.items():
            clean_category = category.replace("_", " ")
            processed[clean_category] = self.str_to_rich(value)
        return processed

    def generate(self):
        """Main loop to generate resumes from YAML files."""
        all_files = [
            f
            for ext in ("*.yaml", "*.yml")
            for f in glob(os.path.join(self.resumes_dir, ext))
        ]

        # Filter: ignore files containing 'example' in their name
        cv_files = [f for f in all_files]

        if not cv_files:
            logger.warning(
                f"No valid resume files found in {self.resumes_dir} (examples ignored)."
            )
            return

        for cv_path in cv_files:
            try:
                # 1. Load and Validate CV Data
                raw_cv_data = self.load_yaml(cv_path)
                cv_data = CVModel(**raw_cv_data)

                # 2. Load Common Data (Contact info, etc.)
                common_path = self.find_yaml(self.config_dir, cv_data.common_file)

                if not common_path:
                    logger.error(
                        f"⚠️ Common file '{cv_data.common_file}' not found in {self.config_dir}"
                    )
                    continue

                common_data = self.load_yaml(common_path) or {}

                # 3. Process Experiences with Markdown
                processed_exps = []
                for exp in cv_data.experiences:
                    exp_dict = exp.model_dump()
                    for t in exp_dict["tasks"]:
                        t["context"] = self.str_to_rich(t["context"])
                        t["bullets"] = [self.str_to_rich(b) for b in t["bullets"]]
                    processed_exps.append(exp_dict)

                # 4. Merge Context
                context = {**common_data}
                context.update(cv_data.model_dump())

                # Overwrite with processed data
                context["experiences"] = processed_exps
                context["skills_display"] = self.process_skills(cv_data.skills)

                # 5. Render Word Document
                if not os.path.exists(self.template_path):
                    logger.error(f"Template missing at: {self.template_path}")
                    continue

                doc = DocxTemplate(self.template_path)
                doc.render(context)

                os.makedirs(self.output_dir, exist_ok=True)
                output_file = os.path.join(self.output_dir, f"{cv_data.filename}.docx")
                doc.save(output_file)

                logger.info(f"Successfully generated: {output_file}")

            except ValidationError as e:
                logger.error(f"Schema validation failed for {cv_path}:\n{e}")
            except Exception as e:
                logger.error(f"Critical error processing {cv_path}: {e}")
