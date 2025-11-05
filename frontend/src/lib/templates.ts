export interface EpicTemplate {
  name: string;
  description: string;
  vision: string;
  objectives: string[];
  valueHypothesis: string;
  descriptionTemplate: string;
  inScope: string[];
  outOfScope: string[];
  leadingIndicators: string[];
  laggingIndicators: string[];
  successDefinition: string;
}

export interface FeatureTemplate {
  name: string;
  description: string;
  businessBenefit: string;
  personas: string[];
  expectedImpact: 'Faible' | 'Moyen' | 'Fort' | 'Critique';
  descriptionTemplate: string;
  mainFeatures: string[];
  nonFunctionalReqs: string;
  acceptanceCriteria: string[];
}

export const epicTemplates: Record<string, EpicTemplate> = {
  strategic: {
    name: "Epic Stratégique Standard",
    description: "Template pour une initiative stratégique classique",
    vision: "Permettre à [persona cible] de [capacité principale] afin de [objectif métier], en améliorant [métrique clé] de [pourcentage/valeur].",
    objectives: [
      "Augmenter [métrique métier] de [X]% d'ici [date/période]",
      "Réduire [problème actuel] de [X]% sur [période]",
      "Atteindre un NPS de [score] auprès de [segment utilisateurs]"
    ],
    valueHypothesis: "En développant [cette capacité], nous pensons que [segment utilisateurs] pourra [action clé], ce qui générera [valeur mesurable] de revenus/économies sur [période].",
    descriptionTemplate: `## Contexte Métier
Le marché/l'organisation nécessite [besoin stratégique] pour répondre à [opportunité/menace].

## Capacités Visées
- [Capacité 1]
- [Capacité 2]
- [Capacité 3]

## Impact Attendu
Cette initiative permettra de [transformation attendue] avec un impact estimé de [valeur métier].`,
    inScope: [
      "Support des [fonctionnalités principales]",
      "Intégration avec [systèmes existants]",
      "Migration des [données/processus existants]"
    ],
    outOfScope: [
      "Fonctionnalités [avancées] (prévues pour v2)",
      "Intégration avec [systèmes legacy non prioritaires]",
      "Support de [cas d'usage marginaux] (<5% utilisateurs)"
    ],
    leadingIndicators: [
      "Nombre de tests utilisateurs réalisés (target: [X])",
      "Couverture de tests automatisés (target: [X]%)",
      "Nombre de sprints/iterations complétés"
    ],
    laggingIndicators: [
      "Taux d'adoption par les utilisateurs (baseline: [X]%, target: [Y]%)",
      "Temps moyen d'exécution de [processus] (baseline: [X], target: [Y])",
      "Revenus générés ou coûts économisés (target: [montant])"
    ],
    successDefinition: `L'Epic sera considéré comme un succès si:
- [Métrique 1] atteint au minimum [seuil]
- [Métrique 2] s'améliore d'au moins [X]%
- Le ROI dépasse [valeur] sur [période]
- La satisfaction utilisateur (NPS) dépasse [score]`
  },
  
  enabler: {
    name: "Epic Technique/Enabler",
    description: "Template pour une initiative technique (dette, architecture, infrastructure)",
    vision: "Moderniser/Améliorer [composant/système technique] pour permettre [capacités futures] et réduire [problème technique actuel].",
    objectives: [
      "Réduire la dette technique dans [module/composant]",
      "Améliorer les performances de [X]%",
      "Augmenter la maintenabilité (réduire le temps de développement de [X]%)"
    ],
    valueHypothesis: "En investissant dans [amélioration technique], nous permettrons à l'équipe de livrer [X]% plus rapidement, réduisant les coûts de maintenance de [montant] par an.",
    descriptionTemplate: `## Problème Technique Actuel
[Système/composant] souffre de [problème technique] qui limite [capacités] et génère [coûts/risques].

## Solution Technique Proposée
Migrer vers [nouvelle architecture/technologie] en utilisant [approche technique].

## Bénéfices Techniques
- Performance: [amélioration attendue]
- Scalabilité: [capacité future]
- Maintenabilité: [simplification]

## Approche de Migration
[Stratégie progressive/big bang/strangler pattern]`,
    inScope: [
      "Migration de [modules prioritaires]",
      "Refactoring de [composants critiques]",
      "Mise en place de [nouvelle infrastructure]"
    ],
    outOfScope: [
      "Refactoring complet de [modules legacy non critiques]",
      "Migration des [anciennes versions non supportées]"
    ],
    leadingIndicators: [
      "Nombre de modules migrés/refactorisés",
      "Couverture de tests après refactoring (target: [X]%)",
      "Nombre de vulnérabilités résolues"
    ],
    laggingIndicators: [
      "Temps de build/déploiement (baseline: [X], target: [Y])",
      "Nombre d'incidents de production (réduction de [X]%)",
      "Vélocité de l'équipe (augmentation de [X]%)"
    ],
    successDefinition: `L'Epic technique sera un succès si:
- Les performances s'améliorent d'au moins [X]%
- Le temps de développement diminue de [X]%
- Les incidents de production baissent de [X]%
- La couverture de tests atteint [X]%`
  },
  
  innovation: {
    name: "Epic Innovation/R&D",
    description: "Template pour une initiative exploratoire ou innovante",
    vision: "Explorer et valider [nouvelle capacité/technologie/marché] pour déterminer la faisabilité de [opportunité stratégique].",
    objectives: [
      "Valider la faisabilité technique de [innovation]",
      "Tester l'appétence du marché auprès de [segment cible]",
      "Construire un POC démontrant [valeur clé]"
    ],
    valueHypothesis: "Si nous validons que [hypothèse d'innovation], alors nous pourrons capturer [opportunité de marché] estimée à [valeur].",
    descriptionTemplate: `## Hypothèse d'Innovation
Nous pensons que [segment marché] a besoin de [nouvelle capacité] parce que [insight utilisateur].

## Approche Lean Startup
1. **Build**: Créer un MVP avec [fonctionnalités minimales]
2. **Measure**: Tester auprès de [X] utilisateurs early adopters
3. **Learn**: Valider que [métrique clé] > [seuil de validation]

## Critères de Go/No-Go
- Continuer si [métrique] > [seuil]
- Pivoter si [signal faible mais intérêt pour variante]
- Arrêter si [absence de traction après X itérations]`,
    inScope: [
      "POC avec fonctionnalités [core minimum]",
      "Tests utilisateurs avec [X] early adopters",
      "Analyse de faisabilité technique et économique"
    ],
    outOfScope: [
      "Version production-ready (phase MVP uniquement)",
      "Scale/Performance optimale (focus sur validation)",
      "Intégration complète avec systèmes existants"
    ],
    leadingIndicators: [
      "Nombre d'itérations MVP complétées",
      "Nombre de tests utilisateurs réalisés (target: [X])",
      "Feedback qualitatif collecté (interviews, surveys)"
    ],
    laggingIndicators: [
      "Taux d'adoption du POC (target: [X]% des testeurs)",
      "NPS early adopters (target: > [score])",
      "Intention d'achat / willingness to pay ([X]% à [prix])"
    ],
    successDefinition: `L'Epic innovation sera validé si:
- Au moins [X]% des early adopters adoptent le POC
- Le NPS dépasse [score]
- [X]% expriment une intention d'achat à [prix]
- La faisabilité technique est confirmée (risques < [seuil])`
  }
};

export const featureTemplates: Record<string, FeatureTemplate> = {
  crud: {
    name: "Feature CRUD Standard",
    description: "Template pour une fonctionnalité Create/Read/Update/Delete classique",
    businessBenefit: "Permettre aux [utilisateurs/rôle] de gérer [entité métier] de manière autonome, réduisant la charge de [équipe/processus manuel] et améliorant l'efficacité de [X]%.",
    personas: [
      "Utilisateur final [rôle principal]",
      "Administrateur système"
    ],
    expectedImpact: 'Moyen',
    descriptionTemplate: `## Vue d'ensemble
Cette feature permet la gestion complète du cycle de vie de [entité métier].

## Fonctionnalités CRUD

### Create (Créer)
- Formulaire de création avec validation
- Champs obligatoires: [liste]
- Règles métier: [règles de validation]

### Read (Consulter)
- Liste avec pagination, tri, filtres
- Vue détaillée avec [informations complètes]
- Export en [formats: CSV, PDF, etc.]

### Update (Modifier)
- Édition inline ou formulaire dédié
- Historique des modifications
- Validation des changements

### Delete (Supprimer)
- Suppression avec confirmation
- Soft delete ou hard delete selon [règle métier]
- Gestion des dépendances/cascade`,
    mainFeatures: [
      "Création de [entité] avec formulaire validé",
      "Liste paginée avec recherche et filtres avancés",
      "Édition et modification avec historique",
      "Suppression sécurisée avec gestion des dépendances"
    ],
    nonFunctionalReqs: `- **Performance**: Liste chargée en <1s pour 10k entrées
- **Sécurité**: RBAC - seuls les [rôles autorisés] peuvent [actions]
- **Audit**: Toutes les modifications sont tracées avec user/timestamp
- **Validation**: Côté client ET serveur pour sécurité`,
    acceptanceCriteria: [
      "Un utilisateur peut créer [entité] avec tous les champs obligatoires",
      "La liste affiche maximum [X] items par page avec pagination",
      "Les modifications sont sauvegardées et historisées",
      "La suppression requiert une confirmation et vérifie les dépendances"
    ]
  },
  
  integration: {
    name: "Feature Intégration",
    description: "Template pour intégrer un système/service externe",
    businessBenefit: "Connecter [système A] avec [système B] pour synchroniser [données/processus] et éliminer la saisie manuelle, économisant [X] heures/semaine.",
    personas: [
      "Utilisateur métier [qui bénéficie de la synchro]",
      "Administrateur système",
      "Équipe IT (maintenance)"
    ],
    expectedImpact: 'Fort',
    descriptionTemplate: `## Contexte d'Intégration
Actuellement, [processus manuel] nécessite [temps/effort]. L'intégration avec [système externe] automatisera ce processus.

## Architecture d'Intégration
- **Type**: [API REST / SOAP / Message Queue / Webhook]
- **Protocole**: [HTTP, AMQP, etc.]
- **Authentification**: [OAuth2, API Key, mTLS, etc.]
- **Fréquence**: [Temps réel / Batch horaire / Événementiel]

## Flux de Données
1. [Système A] déclenche [événement/trigger]
2. [Middleware/API] transforme les données selon [mapping]
3. [Système B] reçoit et traite [données transformées]
4. Confirmation/erreur retournée à [système source]

## Gestion d'Erreurs
- Retry avec backoff exponentiel (max [X] tentatives)
- Dead letter queue pour erreurs non récupérables
- Monitoring et alertes si taux d'erreur > [X]%`,
    mainFeatures: [
      "Connexion sécurisée à [API/service externe]",
      "Synchronisation [bidirectionnelle/unidirectionnelle] de [données]",
      "Transformation et mapping de données selon [règles métier]",
      "Gestion d'erreurs avec retry et monitoring"
    ],
    nonFunctionalReqs: `- **Performance**: Synchronisation de [X] records en <[Y] secondes
- **Fiabilité**: Taux de succès > 99.5%
- **Sécurité**: Chiffrement des données en transit (TLS 1.2+)
- **Monitoring**: Dashboard temps réel des synchros
- **Résilience**: Retry automatique + dead letter queue`,
    acceptanceCriteria: [
      "Le système se connecte avec succès à [API externe] avec authentification [type]",
      "Les données sont synchronisées selon la fréquence [temps réel/batch]",
      "En cas d'erreur, le système retry [X] fois avec backoff exponentiel",
      "Un dashboard affiche le statut des synchronisations en temps réel",
      "Les erreurs non récupérables sont envoyées en dead letter queue"
    ]
  },
  
  ux: {
    name: "Feature Amélioration UX",
    description: "Template pour améliorer l'expérience utilisateur",
    businessBenefit: "Améliorer [parcours utilisateur] pour réduire le taux d'abandon de [X]% et augmenter la satisfaction utilisateur (NPS +[X] points).",
    personas: [
      "Utilisateur final [segment principal]",
      "Utilisateur mobile (si applicable)",
      "Utilisateur accessibilité (déficience visuelle/motrice)"
    ],
    expectedImpact: 'Fort',
    descriptionTemplate: `## Problème UX Actuel
Les utilisateurs rencontrent [friction/difficulté] lors de [parcours], résultant en [métrique négative: abandon, support calls, etc.].

## Insights Utilisateurs
- **Pain points**: [problèmes identifiés via analytics/user research]
- **Opportunités**: [améliorations demandées par users]
- **Benchmarks**: [comparaison avec concurrence/best practices]

## Solution UX Proposée
### Wireframes / Maquettes
[Lien Figma/Sketch]

### Améliorations Clés
1. **Simplification**: Réduire [processus] de [X] à [Y] étapes
2. **Guidage**: Ajouter [tooltips, wizards, inline help]
3. **Feedback**: Messages clairs sur [actions, erreurs, succès]
4. **Performance**: Réduire le temps de [action] de [X]s à [Y]s

## Tests Utilisateurs
- [X] sessions avec utilisateurs réels
- A/B testing sur [variantes]
- Mesure avant/après: [métriques clés]`,
    mainFeatures: [
      "Refonte du [composant/écran] avec design [moderne/accessible]",
      "Ajout de [guidage contextuel, progressive disclosure]",
      "Optimisation du parcours [réduction d'étapes]",
      "Amélioration feedback utilisateur (messages, loading states)"
    ],
    nonFunctionalReqs: `- **Performance**: Chargement page <1s (LCP)
- **Accessibilité**: Conformité WCAG 2.1 niveau AA minimum
- **Responsive**: Support mobile/tablet/desktop
- **Browser**: Support [Chrome, Firefox, Safari, Edge] dernières versions
- **Progressivité**: Dégradation gracieuse si JS désactivé`,
    acceptanceCriteria: [
      "Le nouveau parcours réduit le nombre d'étapes de [X] à [Y]",
      "Le taux d'abandon diminue d'au moins [X]%",
      "Le temps de complétion diminue de [X]%",
      "Les tests utilisateurs montrent un score SUS > [X]/100",
      "La conformité WCAG 2.1 AA est validée par audit"
    ]
  },
  
  security: {
    name: "Feature Sécurité",
    description: "Template pour une fonctionnalité de sécurité/compliance",
    businessBenefit: "Renforcer la sécurité de [système/données] pour se conformer à [réglementation: RGPD, SOC2, etc.] et réduire les risques de [menace] estimés à [impact].",
    personas: [
      "RSSI / Security Officer",
      "Compliance Officer",
      "Administrateur système",
      "Utilisateur final (transparence)"
    ],
    expectedImpact: 'Critique',
    descriptionTemplate: `## Contexte Sécurité/Compliance
**Risque identifié**: [Description du risque ou menace]
**Impact potentiel**: [Financier, réputationnel, légal]
**Réglementation**: [RGPD, HIPAA, SOC2, ISO 27001, etc.]

## Solution de Sécurité
### Contrôles Techniques
- [Contrôle 1: ex. chiffrement at-rest]
- [Contrôle 2: ex. authentification multi-facteurs]
- [Contrôle 3: ex. audit logging]

### Conformité
- Exigences [réglementation]: [articles/sections applicables]
- Preuves d'audit: [logs, rapports, certifications]

## Threat Model
- **Attaquant**: [Profil: externe, interne, opportuniste, ciblé]
- **Vecteurs d'attaque**: [Possibles chemins d'exploitation]
- **Mitigations**: [Comment cette feature réduit le risque]

## Monitoring & Response
- Détection: [Métriques de sécurité à surveiller]
- Alerting: [Seuils déclenchant alertes]
- Incident response: [Procédure si compromission]`,
    mainFeatures: [
      "Implémentation de [contrôle de sécurité: MFA, encryption, etc.]",
      "Audit logging de [actions sensibles]",
      "Gestion des permissions avec principe du moindre privilège",
      "Monitoring et alerting sur [événements de sécurité]"
    ],
    nonFunctionalReqs: `- **Sécurité**: Conformité [standard: OWASP Top 10, SANS 25, etc.]
- **Chiffrement**: [Algorithme] pour données at-rest, TLS 1.3 pour données in-transit
- **Audit**: Logs immutables avec rétention [période] conformes à [réglementation]
- **Performance**: Impact < [X]% sur temps de réponse
- **Disponibilité**: Pas de single point of failure (redondance)`,
    acceptanceCriteria: [
      "Toutes les [données sensibles] sont chiffrées avec [algorithme] at-rest",
      "Les [actions sensibles] génèrent des logs d'audit immutables",
      "L'authentification nécessite [MFA/2FA] pour [rôles critiques]",
      "Un scan de sécurité automatisé valide l'absence de vulnérabilités [OWASP Top 10]",
      "La conformité à [réglementation] est validée par [audit/certification]"
    ]
  }
};

export function getEpicTemplate(templateKey: string): EpicTemplate | null {
  return epicTemplates[templateKey] || null;
}

export function getFeatureTemplate(templateKey: string): FeatureTemplate | null {
  return featureTemplates[templateKey] || null;
}

export function getEpicTemplateKeys(): string[] {
  return Object.keys(epicTemplates);
}

export function getFeatureTemplateKeys(): string[] {
  return Object.keys(featureTemplates);
}
