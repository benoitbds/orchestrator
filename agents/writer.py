# agents/writer.py
from __future__ import annotations
from html import escape
from textwrap import dedent
import os
from .schemas import ExecResult, RenderResult, FeatureProposal, FeatureProposals
from dotenv import load_dotenv
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from orchestrator.prompt_loader import load_prompt

# Load environment variables
load_dotenv()

def render_exec(exec_result: ExecResult, objective: str) -> RenderResult:
    """Transforme ExecResult + objectif en bloc HTML & résumé court."""
    title = f"<h2>Résultat : {escape(objective)}</h2>"

    if exec_result.success:
        summary = "Exécution réussie ✅"
        body = f"""
        <pre><code>{escape(exec_result.stdout)}</code></pre>
        """
    else:
        summary = "Erreur lors de l’exécution ❌"
        body = f"""
        <p><strong>stderr :</strong></p>
        <pre><code>{escape(exec_result.stderr)}</code></pre>
        """

    # Liste d’artefacts (liens relatifs)
    if exec_result.artifacts:
        files = "\n".join(
            f'<li><a href="{escape(path)}" download>{escape(path)}</a></li>'
            for path in exec_result.artifacts
        )
        body += f"<h3>Fichiers générés</h3><ul>{files}</ul>"

    html = dedent(f"""
    {title}
    <p>{summary}</p>
    {body}
    """).strip()

    return RenderResult(html=html, summary=summary, artifacts=exec_result.artifacts)


# Agent de génération de propositions de features pour un épic
load_dotenv()

llm_feature = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4"), temperature=0.2)
feature_parser = PydanticOutputParser(pydantic_object=FeatureProposals)

def make_feature_proposals(project_id: int, parent_id: int, parent_title: str) -> FeatureProposals:
    """
    Génère plusieurs propositions de features pour un épic via un LLM.
    """
    user_msg = (
        f"Project ID: {project_id}\n"
        f"Épic ID: {parent_id}\n"
        f"Titre de l'épic: {parent_title}\n\n"
        "Propose 3-5 features avec un titre et une brève description chacune."
    )
    system_template = load_prompt("feature_generation")
    system_prompt = system_template.replace(
        "{{schema}}", feature_parser.get_format_instructions()
    )
    rsp = llm_feature.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
    )
    return feature_parser.parse(rsp.content)
