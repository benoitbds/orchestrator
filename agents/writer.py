# agents/writer.py
from __future__ import annotations
from html import escape
from textwrap import dedent
from .schemas import ExecResult, RenderResult, FeatureProposal, FeatureProposals
from dotenv import load_dotenv
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

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

llm_feature = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
feature_parser = PydanticOutputParser(pydantic_object=FeatureProposals)

SYSTEM_FEATURE_PROMPT = (
    "Tu es un expert en gestion de backlog. "
    "Pour l'épic donné, génère STRICTEMENT un JSON conforme à ce schéma :\n"
    f"{feature_parser.get_format_instructions()}"
)

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
    rsp = llm_feature.invoke(
        [
            {"role": "system", "content": SYSTEM_FEATURE_PROMPT},
            {"role": "user", "content": user_msg},
        ]
    )
    return feature_parser.parse(rsp.content)
