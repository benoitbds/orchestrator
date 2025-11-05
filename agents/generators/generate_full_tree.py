from __future__ import annotations

import json
from typing import Optional, Dict, List

from orchestrator import crud
from orchestrator.models import EpicCreate, FeatureCreate, USCreate
from agents.tools_context import set_current_run_id, get_current_run_id


EPIC_FEATURES: Dict[str, List[str]] = {
    "Parcours d'achat": [
        "Page d’accueil",
        "Listing produits",
        "Fiche produit",
        "Panier",
        "Checkout",
        "Suivi de commande",
    ],
    "Catalogue & Recherche": [
        "Recherche par mots-clés",
        "Filtres avancés",
        "Tri des résultats",
        "Suggestions intelligentes",
        "Comparateur de produits",
        "Disponibilité en magasin",
    ],
    "Gestion des comptes": [
        "Inscription rapide",
        "Connexion sécurisée",
        "Profil client",
        "Adresses enregistrées",
        "Gestion des préférences",
        "Historique d'achats",
    ],
    "Paiement & Facturation": [
        "Moyens de paiement",
        "Sécurité 3D Secure",
        "Factures téléchargeables",
        "Sauvegarde cartes",
        "Gestion des taxes",
        "Remboursements automatiques",
    ],
    "Logistique & Livraison": [
        "Choix des transporteurs",
        "Suivi colis",
        "Points relais",
        "Préparation de commande",
        "Retour produit",
        "Calcul des frais de port",
    ],
    "Support & Service client": [
        "FAQ dynamique",
        "Chat en ligne",
        "Centre d'aide",
        "Avis clients",
        "Notifications proactives",
        "Gestion des tickets",
    ],
}


def _build_user_stories(feature_name: str) -> List[dict]:
    lower_name = feature_name.lower()
    stories = [
        {
            "title": f"Explorer la section {feature_name}",
            "description": (
                f"En tant que client, je veux parcourir {lower_name} pour trouver rapidement des informations pertinentes."  # noqa: E501
            ),
            "criteria": [
                f"Étant donné un client sur la page « {feature_name} », Quand il affiche la page, Alors le contenu principal s'affiche en moins de deux secondes.",
                f"Étant donné un client authentifié, Quand il revient sur « {feature_name} », Alors la page affiche des recommandations personnalisées basées sur son historique.",
            ],
        },
        {
            "title": f"Interagir avec {feature_name}",
            "description": (
                f"En tant que client, je veux interagir avec {lower_name} pour accomplir mon objectif sans friction."  # noqa: E501
            ),
            "criteria": [
                f"Étant donné un client qui consulte « {feature_name} », Quand il clique sur une action clé, Alors une confirmation visuelle et textuelle apparaît immédiatement.",
                f"Étant donné un client sur mobile, Quand il utilise « {feature_name} », Alors la mise en page s'adapte au format et reste entièrement fonctionnelle.",
            ],
        },
        {
            "title": f"Suivre les résultats de {feature_name}",
            "description": (
                f"En tant que client, je veux comprendre l'effet de mes actions dans {lower_name} pour prendre des décisions éclairées."  # noqa: E501
            ),
            "criteria": [
                f"Étant donné un client qui agit dans « {feature_name} », Quand l'action réussit, Alors un message de succès détaillant la suite apparaît.",
                f"Étant donné un client, Quand une erreur survient dans « {feature_name} », Alors un message explicite explique le problème et la marche à suivre.",
            ],
        },
    ]
    return stories


def _acceptance_to_string(criteria: List[str]) -> str:
    unique = []
    seen = set()
    for crit in criteria:
        key = crit.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            unique.append(crit.strip())
    if len(unique) < 2:
        unique.append("Étant donné un client, Quand il poursuit son parcours, Alors l'expérience reste cohérente.")
    return "\n".join(f"- {line}" for line in unique[:3])


def _record_step(run_id: str | None, node: str, payload: dict) -> None:
    message = json.dumps(payload, ensure_ascii=False)
    crud.record_run_step(run_id or "generate_full_tree_v1", node, message)


def _normalized_key(text: str) -> str:
    return " ".join(text.lower().split())


def _ensure_epics(project_id: int, run_id: Optional[str]) -> Dict[str, int]:
    existing = { _normalized_key(epic.title): epic for epic in crud.get_items(project_id, type="Epic", limit=1000)}
    created = 0
    epic_ids: Dict[str, int] = {}
    for epic_title in EPIC_FEATURES.keys():
        key = _normalized_key(epic_title)
        if key in existing:
            epic_ids[epic_title] = existing[key].id
            continue
        epic = crud.create_item(
            EpicCreate(
                title=epic_title,
                description=f"Epic e-commerce : {epic_title}",
                project_id=project_id,
                parent_id=None,
            )
        )
        crud.mark_item_ai_touch(epic.id)
        epic_ids[epic_title] = epic.id
        existing[key] = epic
        created += 1
    _record_step(run_id, "tool:generate_full_tree_v1:epics_created", {"count": created})
    return epic_ids


def _ensure_features(project_id: int, epic_id_map: Dict[str, int], run_id: Optional[str]) -> Dict[int, Dict[str, int]]:
    features_by_parent: Dict[int, Dict[str, int]] = {pid: {} for pid in epic_id_map.values()}
    existing_features = crud.get_items(project_id, type="Feature", limit=5000)
    for feat in existing_features:
        if feat.parent_id is None:
            continue
        parent_map = features_by_parent.setdefault(feat.parent_id, {})
        parent_map[_normalized_key(feat.title)] = feat.id
    created = 0
    for epic_title, parent_id in epic_id_map.items():
        parent_map = features_by_parent.setdefault(parent_id, {})
        for feature_title in EPIC_FEATURES[epic_title]:
            key = _normalized_key(feature_title)
            if key in parent_map:
                continue
            feature = crud.create_item(
                FeatureCreate(
                    title=feature_title,
                    description=f"Fonctionnalité clé pour {epic_title.lower()}.",
                    project_id=project_id,
                    parent_id=parent_id,
                    acceptance_criteria="- Définir les attentes côté métier.\n- Valider avec les équipes UX/UI.",
                )
            )
            crud.mark_item_ai_touch(feature.id)
            parent_map[key] = feature.id
            created += 1
    _record_step(run_id, "tool:generate_full_tree_v1:features_created", {"count": created})
    return features_by_parent


def _ensure_user_stories(project_id: int, feature_map: Dict[int, Dict[str, int]], run_id: Optional[str]) -> None:
    existing_us = crud.get_items(project_id, type="US", limit=10000)
    us_by_parent: Dict[int, Dict[str, int]] = {}
    for story in existing_us:
        if story.parent_id is None:
            continue
        parent_map = us_by_parent.setdefault(story.parent_id, {})
        parent_map[_normalized_key(story.title)] = story.id

    created = 0
    for parent_id, feature_titles in feature_map.items():
        # need actual feature name by key? reconstruct using stored normalized to real names
        for norm_title, feature_item_id in ((k, vid) for k, vid in feature_titles.items()):
            feature_item = crud.get_item(feature_item_id)
            if not feature_item:
                continue
            desired_us = _build_user_stories(feature_item.title)
            parent_us_map = us_by_parent.setdefault(feature_item_id, {})
            for story in desired_us:
                key = _normalized_key(story["title"])
                if key in parent_us_map:
                    continue
                us = crud.create_item(
                    USCreate(
                        title=story["title"],
                        description=story["description"],
                        project_id=project_id,
                        parent_id=feature_item_id,
                        acceptance_criteria=_acceptance_to_string(story["criteria"]),
                    )
                )
                crud.mark_item_ai_touch(us.id)
                parent_us_map[key] = us.id
                created += 1
    _record_step(run_id, "tool:generate_full_tree_v1:stories_created", {"count": created})


async def generate_full_tree_v1(
    project_id: int,
    theme: str = "e-commerce",
    run_id: Optional[str] = None,
) -> dict:
    previous_run = get_current_run_id()
    if run_id:
        set_current_run_id(run_id)
    try:
        _record_step(run_id, "tool:generate_full_tree_v1:start", {"project_id": project_id, "theme": theme})
        epic_map = _ensure_epics(project_id, run_id)
        feature_map = _ensure_features(project_id, epic_map, run_id)
        _ensure_user_stories(project_id, feature_map, run_id)

        total_epics = len(crud.get_items(project_id, type="Epic", limit=1000))
        total_features = len(crud.get_items(project_id, type="Feature", limit=5000))
        total_us = len(crud.get_items(project_id, type="US", limit=10000))

        summary = {
            "epics": total_epics,
            "features": total_features,
            "user_stories": total_us,
        }
        _record_step(run_id, "tool:generate_full_tree_v1:done", summary)
        return summary
    finally:
        set_current_run_id(previous_run)
