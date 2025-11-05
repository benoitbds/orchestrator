from __future__ import annotations

import asyncio
import json
import unicodedata
from typing import Optional, Dict, List, Tuple, Any

from orchestrator import crud
from orchestrator.models import EpicCreate, FeatureCreate, USCreate, UCCreate
from agents.tools_context import get_current_run_id, set_current_run_id

# ---------------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------------

EPIC_TITLES: List[str] = [
    "Parcours d'achat",
    "Catalogue & Recherche",
    "Gestion des comptes",
    "Paiement & Facturation",
    "Logistique & Livraison",
    "Support & Service client",
]

FEATURES_BY_EPIC: Dict[str, List[str]] = {
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalized_key(text: str) -> str:
    if text is None:
        return ""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(normalized.lower().strip().split())


def _record_step(run_id: Optional[str], node: str, payload: dict) -> None:
    blob = json.dumps(payload, ensure_ascii=False)
    crud.record_run_step(run_id or "generate_full_tree_v2", node, blob)


async def _retry(func, *args, retries: int = 2, base_delay: float = 0.5, **kwargs):
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            if attempt >= retries:
                raise
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
            attempt += 1


def _list_items(project_id: int, item_type: Optional[str] = None, parent_id: Optional[int] = None, limit: int = 10000):
    items = crud.get_items(project_id, type=item_type, limit=limit)
    if parent_id is not None:
        items = [it for it in items if it.parent_id == parent_id]
    return items


def _ensure_length(items: List[str], target: int, prefix: str) -> List[str]:
    pool = list(items)
    counter = 1
    while len(pool) < target:
        pool.append(f"{prefix} {counter}")
        counter += 1
    return pool[:target]


def _build_user_story_variants(feature_name: str, count: int) -> List[Tuple[str, str, List[str]]]:
    base_lower = feature_name.lower()
    variants: List[Tuple[str, str, List[str]]] = []
    templates = [
        (
            "Découvrir {feature}",
            "En tant que client, je veux découvrir {feature_lower} afin de comprendre l'offre." ,
            [
                "Étant donné un client sur la page, Quand la page se charge, Alors le contenu principal s'affiche en moins de deux secondes.",
                "Étant donné un client authentifié, Quand il revient sur la page, Alors des suggestions personnalisées apparaissent.",
            ],
        ),
        (
            "Interagir avec {feature}",
            "En tant que client, je veux interagir avec {feature_lower} pour réaliser mon objectif facilement.",
            [
                "Étant donné un client sur la page, Quand il utilise une action clé, Alors une confirmation claire est affichée.",
                "Étant donné un client sur mobile, Quand il interagit avec {feature_lower}, Alors l'expérience reste fluide et responsive.",
            ],
        ),
        (
            "Analyser {feature}",
            "En tant que client, je veux comprendre l'effet de mes actions dans {feature_lower} pour décider de la suite.",
            [
                "Étant donné un client, Quand une action aboutit, Alors un message de succès détaille les prochaines étapes.",
                "Étant donné un client, Quand une erreur survient, Alors un message explicite propose une alternative.",
            ],
        ),
    ]
    for idx in range(count):
        template = templates[idx % len(templates)]
        title = template[0].format(feature=feature_name, feature_lower=feature_name)
        description = template[1].format(feature_lower=base_lower)
        raw_criteria = [crit.format(feature_lower=base_lower) for crit in template[2]]
        # ensure at least 2 distinct criteria
        criteria = []
        seen = set()
        for crit in raw_criteria:
            key = _normalized_key(crit)
            if key not in seen:
                criteria.append(crit)
                seen.add(key)
        while len(criteria) < 2:
            criteria.append(
                "Étant donné un client, Quand l'action se répète, Alors le système reste cohérent et met à jour l'état."
            )
        variants.append((title, description, criteria))
    return variants


def _make_acceptance_text(criteria: List[str]) -> str:
    unique: List[str] = []
    seen = set()
    for crit in criteria:
        key = _normalized_key(crit)
        if key not in seen and crit.strip():
            unique.append(crit.strip())
            seen.add(key)
        if len(unique) >= 3:
            break
    while len(unique) < 2:
        unique.append("Étant donné un client, Quand il poursuit son action, Alors le système maintient l'état attendu.")
    return "\n".join(f"- {line}" for line in unique)


def _uc_description(us_title: str, index: int) -> str:
    base = us_title.split(" – ")[-1]
    action = base.replace("En tant que", "").strip()
    ordre = index + 1
    return (
        "Acteurs : Client, Système, Service support\n"
        "Préconditions : Le client est authentifié et le contexte est prêt\n"
        "Déclencheur : Le client initie l'action principale\n"
        "Flux principal :\n"
        f"  1. Le client lance l'action {action.lower()}.\n"
        "  2. Le système valide les données et exécute l'opération.\n"
        "  3. Le système confirme le succès de l'étape.\n"
        "Extensions/Erreurs :\n"
        "  E1. Données invalides → afficher un message d'erreur et proposer une correction.\n"
        "Postconditions : L'état métier est mis à jour et visible par le client."
    )


def _uc_title(us_title: str, index: int) -> str:
    base = us_title.replace("En tant que", "").strip()
    suffix = f" #{index + 1}" if index > 0 else ""
    return f"UC – {base}{suffix}"


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------


async def _ensure_epics(
    project_id: int,
    target: int,
    dry_run: bool,
    run_id: Optional[str],
) -> Dict[str, int]:
    existing_items = _list_items(project_id, item_type="Epic", limit=1000)
    existing_map = {_normalized_key(item.title): item for item in existing_items}
    epic_ids: Dict[str, int] = {}
    created = 0
    skipped = 0

    titles = _ensure_length(EPIC_TITLES, target, "Epic e-commerce")

    for title in titles:
        key = _normalized_key(title)
        if key in existing_map:
            epic_ids[title] = existing_map[key].id
            skipped += 1
            continue
        if dry_run:
            created += 1
            continue
        epic = await _retry(
            crud.create_item,
            EpicCreate(
                title=title,
                description=f"Epic e-commerce : {title}",
                project_id=project_id,
                parent_id=None,
            ),
        )
        crud.mark_item_ai_touch(epic.id)
        epic_ids[title] = epic.id
        existing_map[key] = epic
        created += 1

    _record_step(run_id, "tool:generate_full_tree_v2:epics", {"created": created, "skipped": skipped, "total": len(existing_map)})
    return epic_ids


async def _ensure_features(
    project_id: int,
    epic_map: Dict[str, int],
    n_features: int,
    dry_run: bool,
    run_id: Optional[str],
) -> Dict[int, Dict[str, int]]:
    features_by_parent: Dict[int, Dict[str, int]] = {}
    existing_features = _list_items(project_id, item_type="Feature", limit=5000)
    for feature in existing_features:
        if feature.parent_id is None:
            continue
        parent_map = features_by_parent.setdefault(feature.parent_id, {})
        parent_map[_normalized_key(feature.title)] = feature.id

    created = 0
    skipped = 0

    for epic_title, epic_id in epic_map.items():
        target_titles = FEATURES_BY_EPIC.get(epic_title, [])
        titles = _ensure_length(target_titles, n_features, f"Feature {epic_title}")
        parent_map = features_by_parent.setdefault(epic_id, {})
        for title in titles:
            key = _normalized_key(title)
            if key in parent_map:
                skipped += 1
                continue
            if dry_run:
                created += 1
                continue
            feature = await _retry(
                crud.create_item,
                FeatureCreate(
                    title=title,
                    description=f"Fonctionnalité clé pour {epic_title.lower()}.",
                    project_id=project_id,
                    parent_id=epic_id,
                    acceptance_criteria="- Définir les attentes métier.\n- Valider avec les parties prenantes.",
                ),
            )
            crud.mark_item_ai_touch(feature.id)
            parent_map[key] = feature.id
            created += 1

    total = sum(len(children) for children in features_by_parent.values())
    _record_step(run_id, "tool:generate_full_tree_v2:features", {"created": created, "skipped": skipped, "total": total})
    return features_by_parent


async def _ensure_user_stories(
    project_id: int,
    feature_map: Dict[int, Dict[str, int]],
    n_us: int,
    dry_run: bool,
    run_id: Optional[str],
) -> Dict[int, Dict[str, int]]:
    existing_us = _list_items(project_id, item_type="US", limit=10000)
    us_by_parent: Dict[int, Dict[str, int]] = {}
    for story in existing_us:
        if story.parent_id is None:
            continue
        parent_map = us_by_parent.setdefault(story.parent_id, {})
        parent_map[_normalized_key(story.title)] = story.id

    created = 0
    skipped = 0
    feature_to_us_map: Dict[int, Dict[str, int]] = {}

    for epic_features in feature_map.values():
        for feature_key, feature_id in epic_features.items():
            feature_item = await _retry(crud.get_item, feature_id)
            if feature_item is None:
                continue
            parent_map = us_by_parent.setdefault(feature_id, {})
            current_count = len(parent_map)
            if current_count >= n_us:
                feature_to_us_map[feature_id] = parent_map
                continue
            needed = n_us - current_count
            variants = _build_user_story_variants(feature_item.title, needed)
            for title, description, criteria in variants:
                key = _normalized_key(title)
                if key in parent_map:
                    skipped += 1
                    continue
                if dry_run:
                    created += 1
                    continue
                us = await _retry(
                    crud.create_item,
                    USCreate(
                        title=title,
                        description=description,
                        project_id=project_id,
                        parent_id=feature_id,
                        acceptance_criteria=_make_acceptance_text(criteria),
                    ),
                )
                crud.mark_item_ai_touch(us.id)
                parent_map[key] = us.id
                created += 1
            feature_to_us_map[feature_id] = parent_map

    total = sum(len(children) for children in us_by_parent.values())
    _record_step(run_id, "tool:generate_full_tree_v2:us", {"created": created, "skipped": skipped, "total": total})
    return feature_to_us_map


async def _ensure_use_cases(
    project_id: int,
    us_map: Dict[int, Dict[str, int]],
    n_uc: int,
    dry_run: bool,
    run_id: Optional[str],
) -> None:
    existing_ucs = _list_items(project_id, item_type="UC", limit=10000)
    uc_by_parent: Dict[int, Dict[str, int]] = {}
    for uc in existing_ucs:
        if uc.parent_id is None:
            continue
        parent_map = uc_by_parent.setdefault(uc.parent_id, {})
        parent_map[_normalized_key(uc.title)] = uc.id

    created = 0
    skipped = 0

    for feature_us_map in us_map.values():
        for us_key, us_id in feature_us_map.items():
            us_item = await _retry(crud.get_item, us_id)
            if us_item is None:
                continue
            parent_map = uc_by_parent.setdefault(us_id, {})
            current_count = len(parent_map)
            if current_count >= n_uc:
                continue
            for index in range(n_uc):
                title = _uc_title(us_item.title, index)
                key = _normalized_key(title)
                if key in parent_map:
                    skipped += 1
                    continue
                if dry_run:
                    created += 1
                    continue
                uc = await _retry(
                    crud.create_item,
                    UCCreate(
                        title=title,
                        description=_uc_description(us_item.title, index),
                        project_id=project_id,
                        parent_id=us_id,
                        acceptance_criteria=None,
                        invest_compliant=False,
                    ),
                )
                crud.mark_item_ai_touch(uc.id)
                parent_map[key] = uc.id
                created += 1

    total = sum(len(children) for children in uc_by_parent.values())
    _record_step(run_id, "tool:generate_full_tree_v2:uc", {"created": created, "skipped": skipped, "total": total})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_full_tree_v2(
    project_id: int,
    theme: str = "e-commerce",
    *,
    n_epics: int = 6,
    n_features: int = 6,
    n_us: int = 3,
    n_uc: int = 2,
    dry_run: bool = False,
    run_id: Optional[str] = None,
) -> dict:
    previous_run = get_current_run_id()
    if run_id:
        set_current_run_id(run_id)
    try:
        _record_step(
            run_id,
            "tool:generate_full_tree_v2:start",
            {
                "project_id": project_id,
                "theme": theme,
                "quotas": {
                    "epics": n_epics,
                    "features": n_features,
                    "user_stories": n_us,
                    "use_cases": n_uc,
                },
                "dry_run": dry_run,
            },
        )

        if dry_run:
            epics = _list_items(project_id, item_type="Epic", limit=1000)
            epic_count = len(epics)
            needed_epics = max(n_epics - epic_count, 0)
            _record_step(run_id, "tool:generate_full_tree_v2:epics", {"created": 0, "skipped": epic_count, "planned": needed_epics, "total": epic_count})

            features = _list_items(project_id, item_type="Feature", limit=5000)
            features_by_epic: Dict[int, int] = {}
            for feat in features:
                features_by_epic[feat.parent_id] = features_by_epic.get(feat.parent_id, 0) + 1
            planned_features = 0
            for epic in epics:
                current = features_by_epic.get(epic.id, 0)
                planned_features += max(n_features - current, 0)
            _record_step(run_id, "tool:generate_full_tree_v2:features", {"created": 0, "skipped": len(features), "planned": planned_features, "total": len(features)})

            stories = _list_items(project_id, item_type="US", limit=10000)
            us_by_feature: Dict[int, int] = {}
            for us in stories:
                us_by_feature[us.parent_id] = us_by_feature.get(us.parent_id, 0) + 1
            planned_us = 0
            for feat in features:
                current = us_by_feature.get(feat.id, 0)
                planned_us += max(n_us - current, 0)
            _record_step(run_id, "tool:generate_full_tree_v2:us", {"created": 0, "skipped": len(stories), "planned": planned_us, "total": len(stories)})

            use_cases = _list_items(project_id, item_type="UC", limit=10000)
            uc_by_us: Dict[int, int] = {}
            for uc in use_cases:
                uc_by_us[uc.parent_id] = uc_by_us.get(uc.parent_id, 0) + 1
            planned_uc = 0
            for us in stories:
                current = uc_by_us.get(us.id, 0)
                planned_uc += max(n_uc - current, 0)
            _record_step(run_id, "tool:generate_full_tree_v2:uc", {"created": 0, "skipped": len(use_cases), "planned": planned_uc, "total": len(use_cases)})

            summary = {
                "epics": epic_count,
                "features": len(features),
                "user_stories": len(stories),
                "use_cases": len(use_cases),
                "dry_run": True,
                "planned": {
                    "epics": needed_epics,
                    "features": planned_features,
                    "user_stories": planned_us,
                    "use_cases": planned_uc,
                },
            }
            _record_step(run_id, "tool:generate_full_tree_v2:done", summary)
            return summary

        epic_map = await _ensure_epics(project_id, n_epics, dry_run, run_id)
        feature_map = await _ensure_features(project_id, epic_map, n_features, dry_run, run_id)
        us_map = await _ensure_user_stories(project_id, feature_map, n_us, dry_run, run_id)
        await _ensure_use_cases(project_id, us_map, n_uc, dry_run, run_id)

        summary = {
            "epics": len(_list_items(project_id, item_type="Epic", limit=1000)),
            "features": len(_list_items(project_id, item_type="Feature", limit=5000)),
            "user_stories": len(_list_items(project_id, item_type="US", limit=10000)),
            "use_cases": len(_list_items(project_id, item_type="UC", limit=10000)),
            "dry_run": dry_run,
        }
        _record_step(run_id, "tool:generate_full_tree_v2:done", summary)
        return summary
    finally:
        set_current_run_id(previous_run)
