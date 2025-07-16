# agents/writer.py
from __future__ import annotations
from html import escape
from textwrap import dedent
from .schemas import ExecResult, RenderResult

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
