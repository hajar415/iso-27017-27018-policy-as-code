# Policy as Code — Contrôles de sécurité cloud avec Checkov

Automatisation de contrôles de sécurité sur des fichiers Terraform, avec rapports lisibles et intégration à GitHub Actions.

> **Périmètre :** ce projet est une démonstration technique utilisant trois contrôles Checkov dans le contexte des bonnes pratiques de sécurité cloud associées à ISO/IEC 27017 et ISO/IEC 27018. Il ne démontre pas, à lui seul, une conformité complète à ces normes ni une certification ISO.

## Objectifs

- Analyser automatiquement les configurations Terraform avec Checkov.
- Détecter des configurations cloud potentiellement risquées avant la fusion d'une Pull Request.
- Expliquer les résultats en français et proposer des actions correctives.
- Générer un rapport PDF, un rapport Markdown et conserver les résultats JSON de Checkov.
- Publier les rapports en tant qu'artefact GitHub Actions, même lorsque des contrôles échouent.
- Bloquer la fusion lorsque le contrôle obligatoire de sécurité échoue.

## Fonctionnement

1. Une Pull Request est ouverte ou mise à jour.
2. GitHub Actions installe Checkov et ReportLab.
3. Checkov analyse le dossier `terraform/` et enregistre ses résultats dans `checkov-results.json`.
4. Les scripts de `scripts/` génèrent les rapports Markdown et PDF à partir du JSON et de la cartographie `policies/control-mapping.json`.
5. GitHub Actions publie les trois fichiers dans un artefact téléchargeable.
6. Le contrôle obligatoire `Checkov ISO Compliance Scan` échoue si les contrôles sélectionnés échouent ou si la génération ou la publication des rapports échoue.

Le workflow est déclenché sur les Pull Requests et lors d'un push sur la branche `main`.

## Contrôles sélectionnés

| Identifiant Checkov | Vérification | Risque à examiner |
|---|---|---|
| `CKV_AWS_24` | Aucun groupe de sécurité ne doit autoriser SSH depuis `0.0.0.0/0` sur le port 22. | Exposition du service d'administration à Internet. |
| `CKV2_AWS_5` | Les groupes de sécurité doivent être associés à une ressource. | Groupe de sécurité potentiellement inutilisé ou configuration incomplète. |
| `CKV2_AWS_61` | Un bucket S3 doit disposer d'une configuration de cycle de vie. | Politique de conservation et coûts de stockage à examiner selon le besoin métier. |

Les priorités affichées dans les rapports sont définies par le projet. Elles ne sont pas des niveaux de sévérité officiels de Checkov. Une correspondance marquée « À vérifier » dans le rapport doit être validée à partir des éditions de référence et des exigences applicables. Un échec Checkov n'établit pas automatiquement une violation d'une clause ISO.

## Structure du dépôt

Après le rangement des fichiers de démonstration, la structure recommandée est :

```text
.
├── .github/
│   └── workflows/
│       └── compliance-check.yml
├── policies/
│   └── control-mapping.json
├── scripts/
│   ├── generate_pdf_report.py
│   └── generate_report.py
├── terraform/
│   └── conforme/
│       ├── good-s3.tf
│       └── good-vpc.tf
├── tests/
│   └── fixtures/
│       └── non-compliant/
│           ├── combined-violations.tf
│           ├── demo-violation.tf
│           ├── public-ssh-unattached.tf
│           └── s3-no-lifecycle.tf
├── .gitignore
└── README.md
```

### Rôle des principaux chemins

- `.github/workflows/compliance-check.yml` : définit le pipeline GitHub Actions.
- `policies/control-mapping.json` : décrit en français les contrôles, risques, recommandations et états de validation des correspondances ISO.
- `scripts/generate_report.py` : crée le rapport Markdown.
- `scripts/generate_pdf_report.py` : crée le rapport PDF.
- `terraform/conforme/` : contient les exemples destinés à réussir les contrôles sélectionnés.
- `tests/fixtures/non-compliant/` : conserve les configurations de test volontairement non conformes. Ce dossier n'est pas analysé par le scan normal du workflow.

Les chemins ci-dessus sont relatifs à la racine du dépôt. Dans un README Markdown, utiliser des `/` même lorsque le projet est développé sous Windows. Par exemple : `scripts/generate_pdf_report.py`.

## Prérequis pour l'exécution locale

- Python 3.12, pour correspondre à l'environnement du workflow GitHub Actions.
- Git et un compte GitHub pour tester les Pull Requests et les exécutions du workflow.
- Un environnement Python virtuel avec Checkov et ReportLab.

À la racine du dépôt, activer l'environnement virtuel puis installer les dépendances :

```bat
python -m pip install checkov==3.3.27 reportlab==4.4.9
```

## Générer les rapports localement

Lancer d'abord Checkov sur les fichiers Terraform utilisés par le workflow :

```bat
checkov -d terraform/ --framework terraform --check CKV_AWS_24,CKV2_AWS_5,CKV2_AWS_61 --output cli --output json --output-file-path console,checkov-results.json --compact
```

Si Checkov détecte une violation, il peut retourner un code de sortie non nul. C'est le résultat attendu du contrôle de sécurité ; cela ne veut pas dire que les scripts de rapports ont échoué.

Générer le rapport Markdown :

```bat
python scripts\generate_report.py --input checkov-results.json --mapping policies\control-mapping.json --output reports\compliance-report.md
```

Générer le rapport PDF :

```bat
python scripts\generate_pdf_report.py --input checkov-results.json --mapping policies\control-mapping.json --output reports\compliance-report.pdf
```

Les commandes de génération créent le dossier `reports/` si le script le prévoit. Les fichiers produits localement et le JSON brut sont des résultats générés ; ils n'ont généralement pas besoin d'être versionnés. Le workflow GitHub les publie comme artefact.

## Scénarios de démonstration

### Test 1 — Détection d'une configuration non conforme

Le dossier `tests/fixtures/non-compliant/` conserve les exemples volontairement incorrects. Lancer le contrôle sur ces exemples :

```bat
checkov -d tests/fixtures/non-compliant --framework terraform --check CKV_AWS_24,CKV2_AWS_5,CKV2_AWS_61 --output cli --compact
```

Le résultat attendu est un ou plusieurs contrôles en échec. Ce test négatif permet de démontrer la détection ; il ne doit pas être interprété comme un échec du projet lui-même.

Dans la démonstration GitHub Actions, l'artefact du test contient :

- `compliance-report.pdf`
- `compliance-report.md`
- `checkov-results.json`

Conserver une copie de cet artefact si elle est nécessaire pour une présentation, car la rétention GitHub Actions est limitée.

### Test 2 — Configuration conforme

Le dossier analysé par le workflow, `terraform/`, doit uniquement contenir les configurations prévues pour passer les contrôles. Les configurations de test non conformes doivent rester dans `tests/fixtures/non-compliant/`.

Relancer le workflow sur la Pull Request après le rangement du fichier de démonstration. Le résultat attendu est trois contrôles réussis, aucun contrôle échoué, un artefact de rapports disponible et un contrôle GitHub Actions vert.

Les exemples conformes sont :

- `terraform/conforme/good-vpc.tf`
- `terraform/conforme/good-s3.tf`

## Lire les résultats

- **PDF :** rapport synthétique adapté à une revue ou à une présentation.
- **Markdown :** rapport textuel facile à lire dans GitHub et à versionner si nécessaire.
- **JSON :** résultats structurés de Checkov destinés au diagnostic ou à un traitement automatisé.

Le rapport est généré à partir des résultats du scan ; ce n'est pas un document statique. Le succès de génération du PDF ne signifie pas que les contrôles de sécurité ont réussi : le statut de conformité dépend du résultat Checkov.

## Limites

- Le projet exécute uniquement les trois contrôles Checkov explicitement sélectionnés.
- Les correspondances ISO doivent être vérifiées avant de revendiquer une correspondance normative précise.
- Un pipeline vert ne prouve ni la conformité complète d'une infrastructure ou d'une organisation ni une certification ISO.
- Les exemples dans `tests/fixtures/non-compliant/` servent à la démonstration et ne remplacent pas une suite de tests automatisés complète.
