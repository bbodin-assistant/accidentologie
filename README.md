# Accidentologie

Bibliothèque Python pour télécharger, filtrer, analyser et visualiser les bases
annuelles des accidents corporels de la circulation routière (BAAC).

L'interface est conçue autour de trois principes :

1. une ligne par accident dans le DataFrame principal ;
2. des fonctions d'analyse qui retournent des DataFrames réutilisables ;
3. des fonctions de rendu indépendantes qui retournent une figure Matplotlib ou une
   carte Folium.

Ainsi, chaque CSV et chaque graphique peut être produit séparément, puis les figures
choisies peuvent être assemblées dans un rapport PDF.

## Installation

Le projet nécessite Python 3.10 ou une version plus récente.

```bash
git clone <URL_DU_DEPOT>
cd accidentologie
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Exemple rapide

```python
from accidentologie import (
    get_dataframe,
    plot_accident_per_year,
    plot_severity_map,
)

accidents = get_dataframe(
    years=[2022, 2023, 2024],
    communes=["17015", "17021", "17306"],
)

ax = plot_accident_per_year(accidents)
ax.figure.savefig("accidents_par_annee.png", dpi=180, bbox_inches="tight")

carte = plot_severity_map(accidents, output="carte.html")
```

Les communes sont identifiées par leur code INSEE à cinq caractères, et non par leur
code postal.

## Organisation

```text
accidentologie/
├── __init__.py       # interface publique
├── download.py       # téléchargement data.gouv.fr
├── data.py           # DataFrame canonique des accidents
├── analysis.py       # tableaux et DataFrame des usagers
├── clustering.py     # profils de victimes
├── plots.py          # graphiques et cartes
├── report.py         # assemblage PDF
└── territories.py    # territoires réutilisables
main.py               # exemple/CLI utilisant uniquement l'interface publique
```

Toute la logique métier se trouve dans le paquet `accidentologie`. Le fichier
`main.py` est volontairement un orchestrateur mince : il montre comment appeler les
fonctions une par une pour créer des CSV, des images, une carte HTML et un PDF.

## Télécharger les CSV BAAC

```python
from accidentologie import download_csv_files

downloaded = download_csv_files(
    years=[2022, 2023, 2024],
    data_dir="data",
)

print(f"{len(downloaded)} fichiers téléchargés")
```

Chaque année contient les quatre tables officielles : `caracteristiques`, `lieux`,
`vehicules` et `usagers`. Les fichiers déjà présents ne sont pas retéléchargés.

```python
# Retéléchargement explicite
download_csv_files(years=2024, force=True)

# Sans affichage de progression, par exemple dans une application web
download_csv_files(years=2024, progress=None)
```

Depuis l'exemple en ligne de commande :

```bash
python main.py --download
```

## Définir un territoire

Un territoire est simplement un nom et une liste de codes INSEE communaux.

```python
from accidentologie import Territory

secteur_royan = Territory(
    "Royan et communes voisines",
    ["17306", "17333", "17380", "17461"],
)
```

Deux territoires sont fournis comme exemples :

```python
from accidentologie import CARA, ROYAN

print(ROYAN.name, ROYAN.communes)
print(CARA.name, len(CARA.communes))
```

La classe est pratique pour une interface utilisateur, mais les fonctions acceptent
aussi directement une chaîne ou une liste de codes.

## Charger les accidents

`get_dataframe` retourne une ligne par accident et filtre les fichiers pendant leur
lecture afin de limiter la mémoire utilisée.

```python
from accidentologie import get_dataframe

accidents = get_dataframe(
    years=range(2020, 2025),
    communes=["17306", "17333", "17380", "17461"],
    data_dir="data",
)
```

Passer `None` sélectionne toutes les années présentes ou toute la France :

```python
france = get_dataframe(years=2024, communes=None)
toutes_les_annees = get_dataframe(years=None, communes="17306")
```

### Colonnes principales

| Colonne | Description |
|---|---|
| `accident_id` | identifiant BAAC unique |
| `year`, `date`, `time` | date et heure normalisées |
| `department_code`, `commune_code` | codes géographiques |
| `address` | adresse déclarée |
| `latitude`, `longitude`, `has_coordinates` | géolocalisation disponible |
| `severity_code`, `severity` | conséquence la plus grave de l'accident |
| `number_killed` | personnes tuées |
| `number_hospitalized` | blessés hospitalisés |
| `number_slightly_injured` | blessés légers |
| `number_users`, `number_vehicles` | usagers et véhicules enregistrés |
| `vehicle_codes`, `vehicle_types` | catégories de véhicules impliquées |

La gravité est exclusive : un accident mortel n'est pas également compté comme grave
ou léger. Les codes communaux de l'ancien schéma 2005–2018 sont normalisés au format
INSEE à cinq caractères.

## Produire les tableaux CSV

Les fonctions d'analyse retournent des DataFrames ordinaires.

```python
from accidentologie import (
    export_csv,
    get_accidents_per_year,
    get_vehicle_severity_table,
    get_victim_dataframe,
    get_fatalities_by_user_type,
)

par_annee = get_accidents_per_year(accidents)
par_vehicule = get_vehicle_severity_table(accidents)

usagers = get_victim_dataframe(
    years=[2022, 2023, 2024],
    communes=["17306", "17333", "17380", "17461"],
)
tues = get_fatalities_by_user_type(usagers)

export_csv(accidents, "exports/accidents.csv")
export_csv(par_annee, "exports/accidents_par_annee.csv")
export_csv(par_vehicule, "exports/accidents_par_vehicule.csv")
export_csv(usagers, "exports/usagers.csv")
export_csv(tues, "exports/tues_par_type_usager.csv")
```

`get_vehicle_severity_table` compte un accident une fois pour chaque type de véhicule
distinct impliqué. Le total par véhicule n'est donc pas nécessairement le nombre
d'accidents uniques.

## Générer les graphiques individuellement

Chaque fonction retourne un axe Matplotlib. Sa figure peut être affichée dans un
notebook, enregistrée ou insérée dans une interface.

```python
from accidentologie import (
    plot_accident_per_year,
    plot_vehicle_severity_table,
    plot_fatalities_by_user_type,
    plot_severity_map_static,
)

ax_year = plot_accident_per_year(
    accidents,
    title="Accidents — Royan et communes voisines",
)
ax_year.figure.savefig("plots/par_annee.png", dpi=180, bbox_inches="tight")

ax_vehicle = plot_vehicle_severity_table(par_vehicule)
ax_vehicle.figure.savefig("plots/par_vehicule.png", dpi=180, bbox_inches="tight")

if not tues.empty:
    ax_fatalities = plot_fatalities_by_user_type(tues)

ax_map = plot_severity_map_static(accidents)
ax_map.figure.savefig("plots/carte.png", dpi=180, bbox_inches="tight")
```

## Générer la carte interactive

```python
from accidentologie import plot_severity_map

carte = plot_severity_map(
    accidents,
    output="carte_interactive.html",
    cluster=True,
)
```

La fonction retourne un objet `folium.Map`. Les accidents mortels sont des étoiles
rouges, les graves non mortels des losanges orange et les légers des ronds jaunes.
La limite par défaut est de 20 000 points pour éviter un HTML accidentellement énorme.

## Clustering des profils de victimes

```python
from accidentologie import (
    cluster_victims,
    plot_cluster_profiles,
    plot_clustering_diagnostic,
)

result = cluster_victims(usagers)

print(result.selected_clusters)
print(result.profiles)
print(result.diagnostics)

ax_profiles = plot_cluster_profiles(result.profiles)
ax_diagnostic = plot_clustering_diagnostic(result.diagnostics)

export_csv(result.profiles, "exports/clusters_profils.csv")
export_csv(result.victims, "exports/usagers_avec_cluster.csv")
export_csv(result.diagnostics, "exports/clusters_diagnostic.csv")
```

Le clustering utilise une distance de Gower et une classification hiérarchique à
lien complet. Il compare par défaut 2 à 20 groupes et écarte les solutions contenant
des microgroupes ou insuffisamment stables.

## Composer un rapport à partir des graphiques choisis

```python
from accidentologie import save_pdf_report

figures = [
    ax_year.figure,
    ax_vehicle.figure,
    ax_map.figure,
    ax_profiles.figure,
    ax_diagnostic.figure,
]

save_pdf_report(
    figures,
    "rapport.pdf",
    title="Rapport d'accidentologie — Royan et communes voisines",
)
```

L'ordre de la liste est l'ordre des pages. Une application peut donc proposer des
cases à cocher et composer seulement les pages demandées.

## Utiliser `main.py`

### Générer le rapport PDF de la CARA

La CARA est le territoire utilisé par défaut dans `main.py`. Pour télécharger les
données manquantes, produire tous les CSV et graphiques, puis générer le rapport :

```bash
python main.py --download
```

Si les CSV BAAC sont déjà présents dans `data/`, le téléchargement peut être omis :

```bash
python main.py
```

Ces commandes analysent les 33 communes de la CARA sur la période 2005–2024. Le
graphique des personnes tuées porte sur 2023 et 2024, les deux dernières années de
la sélection. Le PDF est créé ici :

```text
outputs/communaute-d-agglomeration-royan-atlantique-cara/rapport.pdf
```

Pour indiquer explicitement la période et les années du graphique des personnes
tuées :

```bash
python main.py \
  --years 2005 2006 2007 2008 2009 2010 2011 2012 2013 2014 \
          2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 \
  --fatality-years 2023 2024
```

Le même rapport peut être construit directement avec l'API Python. Chaque page est
d'abord générée séparément, puis transmise à `save_pdf_report` dans l'ordre souhaité :

```python
from accidentologie import (
    CARA,
    cluster_victims,
    get_dataframe,
    get_fatalities_by_user_type,
    get_vehicle_severity_table,
    get_victim_dataframe,
    plot_accident_per_year,
    plot_cluster_profiles,
    plot_clustering_diagnostic,
    plot_fatalities_by_user_type,
    plot_severity_map_static,
    plot_vehicle_severity_table,
    save_pdf_report,
)

years = range(2005, 2025)
accidents = get_dataframe(years=years, communes=CARA.communes)
usagers = get_victim_dataframe(years=years, communes=CARA.communes)

vehicules = get_vehicle_severity_table(accidents)
tues = get_fatalities_by_user_type(usagers, years=[2023, 2024])
clusters = cluster_victims(usagers)

figures = [
    plot_accident_per_year(
        accidents,
        title=f"Accidents par année et gravité — {CARA.name}",
    ).figure,
    plot_vehicle_severity_table(
        vehicules,
        title=f"Accidents par véhicule et gravité — {CARA.name}",
    ).figure,
    plot_fatalities_by_user_type(
        tues,
        title=f"Personnes tuées par type d'usager — {CARA.name}",
    ).figure,
    plot_severity_map_static(
        accidents,
        title=f"Accidents géolocalisés — {CARA.name}",
    ).figure,
    plot_cluster_profiles(
        clusters.profiles,
        title=f"Profils de victimes — {CARA.name}",
    ).figure,
    plot_clustering_diagnostic(
        clusters.diagnostics,
        title=f"Choix du nombre de profils — {CARA.name}",
    ).figure,
]

save_pdf_report(
    figures,
    "rapport_cara.pdf",
    title=f"Rapport d'accidentologie — {CARA.name}",
)
```

Les résultats sont écrits dans `outputs/<territoire>/` :

```text
csv/                    # toutes les tables exportables
plots/                  # chaque graphique en PNG
carte_interactive.html  # carte Folium
rapport.pdf             # figures assemblées
```

### Rapport pour une autre ville

Royan, pour 2015–2024 :

```bash
python main.py \
  --territory-name "Royan" \
  --communes 17306 \
  --years 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024
```

Plusieurs communes :

```bash
python main.py \
  --territory-name "Côte de Beauté" \
  --communes 17306 17333 17380 17461 \
  --years 2020 2021 2022 2023 2024 \
  --fatality-years 2023 2024 \
  --download
```

Le graphique des personnes tuées porte par défaut sur les deux dernières années de
la sélection ; le CSV conserve toutes les années. `--fatality-years` permet de choisir
explicitement les années du graphique.

Pour un petit territoire où le clustering serait peu pertinent :

```bash
python main.py --territory-name "Royan" --communes 17306 --skip-clustering
```

## Intégration dans une interface web

Les fonctions ne dépendent ni du terminal ni de `main.py` :

- `download_csv_files(..., progress=None)` convient à une tâche d'arrière-plan ;
- les DataFrames peuvent être sérialisés en CSV avec `export_csv` ou directement en
  JSON avec Pandas ;
- les figures Matplotlib peuvent être écrites dans un `BytesIO` ;
- `plot_severity_map` retourne le HTML Folium via `carte.get_root().render()` ;
- `save_pdf_report` accepte n'importe quelle sélection de figures.

Exemple de graphique en mémoire :

```python
from io import BytesIO

buffer = BytesIO()
ax = plot_accident_per_year(accidents)
ax.figure.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
buffer.seek(0)
```

## Limites des données

- La géolocalisation est très incomplète avant 2013. Les comptages restent valides,
  mais la carte ne représente que les accidents disposant de coordonnées.
- Les changements et fusions de communes ne sont pas reconstruits automatiquement.
- Les catégories BAAC ont évolué ; les anciennes catégories restent explicitement
  libellées.
- Sans population exposée, trafic ou kilométrage parcouru, les résultats décrivent
  les accidents observés et non un risque individuel absolu.

## Source et licences

Données : Ministère de l'Intérieur — bases annuelles BAAC publiées sur
[data.gouv.fr](https://www.data.gouv.fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2024).

Conservez l'attribution de la source et vérifiez la licence affichée sur la fiche
data.gouv.fr avant republication. Le code du projet est sous licence MIT.

## Publier la carte de la CARA sur GitHub Pages

Les 80 CSV BAAC du dossier `data/` sont suivis avec Git LFS. Le site publié ne
contient pas ces sources : l'Action les utilise pour construire un HTML WebGL et un
fichier compact de points par année.

### Préparer et pousser les données LFS

Git LFS doit être installé localement avant le premier push :

```bash
git lfs install
git lfs ls-files
```

`git lfs ls-files` doit afficher les 80 CSV. Le premier push envoie environ 439 Mio
vers le stockage LFS du propriétaire du dépôt :

```bash
git push -u origin main
```

Les fichiers publiés par le site excluent les adresses et les caractéristiques des
usagers. Chaque point contient uniquement les coordonnées, la gravité, le code INSEE,
la date et l'identifiant BAAC de l'accident.

### Fonctionnement de l'Action

Le workflow [`.github/workflows/pages.yml`](.github/workflows/pages.yml) :

1. récupère les pointeurs Git sans télécharger les objets LFS ;
2. restaure le dossier `data/` depuis le cache GitHub Actions ;
3. appelle `git lfs pull` uniquement si ce cache est absent ; les fichiers `lieux`,
   inutiles à cette carte, restent alors de simples pointeurs ;
4. filtre les 33 communes de la CARA et génère leur carte pour 2005–2024 ;
5. déploie uniquement le dossier `site/` comme artifact GitHub Pages.

La clé du cache dépend des pointeurs LFS. Une modification du README ne déclenche pas
de reconstruction, et une modification du code réutilise les CSV déjà mis en cache.

Le premier build récupère depuis LFS les tables `caracteristiques`, `usagers` et
`vehicules`. Les builds suivants restaurent le cache tant qu'il n'a pas expiré ou été
évincé. Même sans cache, les données viennent de LFS et ne sont jamais retéléchargées
depuis data.gouv.fr.

### Activer Pages

Après le premier push :

1. ouvrir **Settings → Pages** dans le dépôt GitHub ;
2. choisir **GitHub Actions** comme source de publication ;
3. ouvrir l'onglet **Actions** et lancer manuellement
   **Carte CARA GitHub Pages** si le push ne l'a pas déjà déclenchée.

Le workflow ne s'exécute automatiquement que lorsque `main`, le générateur, les CSV
LFS ou le workflow changent. Il peut toujours être relancé avec `workflow_dispatch`.

### Tester le site localement

Pour construire seulement deux années :

```bash
python main.py \
  --build-github-pages \
  --years 2023 2024 \
  --output-dir site

python -m http.server 8000 --directory site
```

Ouvrir ensuite <http://localhost:8000>. Pour reproduire exactement le build Pages sur
les vingt années :

```bash
python main.py --build-github-pages --output-dir site
```

La carte charge progressivement un fichier par année et utilise deck.gl/WebGL pour
afficher les points. Les filtres permettent de masquer des années ou des niveaux de
gravité sans régénérer le site.
