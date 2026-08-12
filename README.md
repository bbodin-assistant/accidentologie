# Accidentologie

Bibliothèque Python pour télécharger, normaliser, analyser et visualiser les
bases annuelles des accidents corporels de la circulation routière (BAAC).

L'API sépare les données, les agrégations et les rendus : les tableaux sont des
`pandas.DataFrame`, les graphiques retournent des axes Matplotlib et les cartes
interactives des objets Folium ou un site WebGL statique.

## Installation

Le projet requiert Python 3.10 ou une version plus récente.

```bash
git clone https://github.com/bbodin/accidentologie.git
cd accidentologie
git lfs pull
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Pour exécuter le notebook :

```bash
python -m pip install -e ".[notebook]"
```

## Télécharger les données BAAC

Sans argument `years`, la fonction découvre les années proposées par la source.
Les quatre tables officielles sont téléchargées par défaut.

```python
from accidentologie import download_csv_files

download_csv_files(years=[2022, 2023, 2024], data_dir="data")
download_csv_files(years=None, data_dir="data")
```

Les analyses de la bibliothèque utilisent seulement `caracteristiques`, `vehicules`
et `usagers`. Pour ne récupérer que ces tables :

```python
from accidentologie import ANALYSIS_TABLES, download_csv_files

download_csv_files(years=2024, tables=ANALYSIS_TABLES)
```

`force=True` remplace les fichiers existants et `progress=None` désactive l'affichage
de la progression.

## Charger les accidents

`get_dataframe` retourne une ligne par accident. `years=None` sélectionne toutes les
années présentes localement et `communes=None` toute la France.

```python
from accidentologie import get_dataframe

accidents = get_dataframe(
    years=[2022, 2023, 2024],
    communes=["75101", "75102"],
    data_dir="data",
)

france_2024 = get_dataframe(years=2024, communes=None)
```

Les communes sont identifiées par leur code INSEE à cinq caractères, et non par
leur code postal.

### Colonnes principales

| Colonne | Description |
|---|---|
| `accident_id` | identifiant BAAC de l'accident |
| `year`, `date`, `time` | année, date et heure normalisées |
| `department_code`, `commune_code` | codes géographiques |
| `address` | adresse déclarée dans le BAAC |
| `latitude`, `longitude`, `has_coordinates` | géolocalisation |
| `severity_code`, `severity` | conséquence la plus grave parmi les usagers |
| `number_killed`, `number_hospitalized` | nombre de personnes tuées ou hospitalisées |
| `number_users`, `number_vehicles` | usagers et véhicules enregistrés |
| `vehicle_codes`, `vehicle_types` | types distincts de véhicules impliqués |

La gravité de l'accident est exclusive : un accident mortel n'est pas également
compté dans la catégorie « Blessé hospitalisé ». La collecte de cette dernière
catégorie connaît une rupture méthodologique à partir de 2018 ; elle n'est plus
labellisée officiellement depuis 2019. Le graphique annuel
matérialise automatiquement cette rupture lorsque la période l'encadre.

## Définir un territoire

```python
from accidentologie import Territory

territoire = Territory(
    "Paris Centre",
    ["75101", "75102", "75103", "75104"],
)

accidents = get_dataframe(years=2024, communes=territoire.communes)
```

Un territoire peut aussi être chargé depuis un GeoJSON dont les entités possèdent
une propriété `code` :

```python
territoire = Territory.from_geojson(
    "territoire.geojson",
    name="Mon territoire",
)
```

## Produire les tableaux

```python
from accidentologie import (
    export_csv,
    get_accidents_per_year,
    get_fatalities_by_user_type,
    get_vehicle_severity_table,
    get_victim_dataframe,
)

par_annee = get_accidents_per_year(accidents)
par_vehicule = get_vehicle_severity_table(accidents)
victimes = get_victim_dataframe(
    years=[2022, 2023, 2024],
    communes=territoire.communes,
)
tues = get_fatalities_by_user_type(victimes)

export_csv(par_annee, "exports/accidents_par_annee.csv")
export_csv(par_vehicule, "exports/accidents_par_vehicule.csv")
export_csv(victimes, "exports/victimes.csv")
export_csv(tues, "exports/personnes_tuees.csv")
```

Un accident multivéhicule apparaît une fois pour chaque type distinct dans le
tableau par véhicule. La somme de ce tableau n'est donc pas un nombre d'accidents
uniques.

## Générer les graphiques

```python
from accidentologie import (
    plot_accident_per_year,
    plot_monthly_seasonality,
    plot_severity_map_static,
    plot_vehicle_severity_table,
)

ax = plot_accident_per_year(accidents)
ax.figure.savefig("accidents_par_annee.png", dpi=180, bbox_inches="tight")

ax = plot_vehicle_severity_table(par_vehicule)
ax.figure.savefig("accidents_par_vehicule.png", dpi=180, bbox_inches="tight")

ax = plot_monthly_seasonality(accidents)

ax = plot_severity_map_static(accidents)
ax.figure.savefig("carte_statique.png", dpi=180, bbox_inches="tight")
```

La carte statique charge un fond CartoDB via Contextily et masque les axes. Pour un
rendu hors ligne, utiliser `plot_severity_map_static(accidents, basemap=False)`.

## Générer les cartes interactives

### Carte Folium

```python
from accidentologie import plot_severity_map

carte = plot_severity_map(
    accidents,
    output="carte.html",
    cluster=True,
)
```

La légende distingue les accidents mortels, avec blessé hospitalisé, légers,
indemnes et de gravité inconnue. `max_points` limite explicitement la taille du HTML.
Pour un fournisseur de tuiles personnalisé, utiliser `tiles=...` et `attr=...`.

### Site WebGL statique

Pour une sélection plus volumineuse, `build_web_map` produit un fichier JSON par
année et une carte Deck.gl. Les années locales et la vue initiale sont calculées
automatiquement.

```python
from accidentologie import build_web_map

index = build_web_map(
    years=None,
    communes=territoire.communes,
    data_dir="data",
    output_dir="site",
    title=f"Accidents corporels — {territoire.name}",
)
```

`basemap_url` et `basemap_attribution` permettent de remplacer le fond CartoDB.

## Profils observés parmi les victimes

```python
from accidentologie import (
    cluster_victims,
    plot_cluster_profiles,
    plot_clustering_diagnostic,
)

resultat = cluster_victims(
    victimes,
    min_clusters=2,
    max_clusters=20,
    stability_fraction=0.8,
    max_victims=5000,
)

plot_cluster_profiles(resultat.profiles)
plot_clustering_diagnostic(resultat.diagnostics)
```

Le clustering utilise l'âge, le sexe, la catégorie d'usager et le mode de
déplacement des personnes blessées ou tuées. Sa stabilité est mesurée sur plusieurs
sous-échantillons. Le calcul hiérarchique utilise une matrice O(n²), d'où la garde
mémoire `max_victims`.

Ces groupes décrivent les victimes enregistrées. Ils ne mesurent pas la probabilité
d'avoir un accident dans la population : cette mesure exigerait un dénominateur
d'exposition, par exemple le trafic ou les distances parcourues.

## Créer un rapport PDF

```python
from accidentologie import (
    plot_accident_per_year,
    plot_severity_map_static,
    plot_vehicle_severity_table,
    save_pdf_report,
)

ax_annee = plot_accident_per_year(accidents)
ax_vehicules = plot_vehicle_severity_table(par_vehicule)
ax_carte = plot_severity_map_static(accidents)
figures = [ax_annee.figure, ax_vehicules.figure, ax_carte.figure]
save_pdf_report(
    figures,
    "rapport.pdf",
    title=f"Rapport d'accidentologie — {territoire.name}",
)
```

`save_pdf_report` conserve la taille et la configuration de mise en page originales
des figures fournies.

## Interface en ligne de commande

Le territoire est toujours explicite. Sans `--years`, toutes les années disponibles
localement sont analysées.

```bash
python main.py \
  --territory-name "Paris 1er" \
  --communes 75101 \
  --years 2022 2023 2024 \
  --download
```

Le programme crée dans `outputs/<territoire>/` :

```text
csv/                    # tableaux exportés
plots/                  # graphiques PNG
carte_interactive.html  # carte Folium
rapport.pdf             # rapport assemblé
```

Options utiles :

- `--fatality-years` sélectionne les années du graphique des personnes tuées ;
- `--skip-clustering` désactive le clustering ;
- `--cluster-max-clusters` et `--cluster-max-victims` contrôlent son amplitude ;
- `--force-download` remplace les CSV locaux ;
- `--no-basemap` produit la carte PDF sans accès réseau ;
- `--no-interactive-map` désactive le fichier Folium ;
- `--territory-geojson` charge les communes depuis un fichier GeoJSON.

### Rapport d'exemple pour la CARA

Le fichier `data/reference/cara_communes.geojson` constitue la source unique des
communes utilisées par cet exemple.

```bash
python main.py \
  --territory-name "Communauté d'agglomération Royan Atlantique (CARA)" \
  --territory-geojson data/reference/cara_communes.geojson
```

Ajouter `--download` si les trois tables nécessaires ne sont pas encore présentes.

## Notebook d'exemple

[![Ouvrir dans Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/bbodin/accidentologie/blob/main/notebooks/accidentologie_demo.ipynb)

[`notebooks/accidentologie_demo.ipynb`](notebooks/accidentologie_demo.ipynb) applique
l'API à la CARA sur 2020–2024. Il charge les communes depuis le même GeoJSON, montre
comment construire une agrégation directement avec Pandas et produit les graphiques
du package. La première cellule installe directement la bibliothèque depuis GitHub.
Les cellules suivantes téléchargent uniquement les trois tables BAAC nécessaires pour
2020–2024. Le notebook est versionné sans sorties exécutées.

```bash
jupyter lab notebooks/accidentologie_demo.ipynb
```

![Accidents par année et gravité dans la CARA](docs/images/cara-accidents-par-annee.png)

*Accidents par année et gravité dans le territoire d'exemple, 2020–2024.*

![Saisonnalité mensuelle des accidents](docs/images/cara-saisonnalite.png)

*Nombre mensuel d'accidents dans le territoire d'exemple, 2020–2024.*

![Carte statique des accidents](docs/images/cara-carte-geographique.png)

*Carte statique produite par `plot_severity_map_static`, 2020–2024.*

## Limites des données

- La géolocalisation est très incomplète avant 2013 ; les cartes ne représentent
  que les accidents possédant des coordonnées valides.
- Les changements et fusions de communes ne sont pas reconstruits automatiquement.
- Les catégories de véhicules et les procédures de collecte ont évolué.
- La série des blessés hospitalisés connaît une rupture à partir de 2018.
- Le BAAC décrit les accidents enregistrés, pas l'exposition au risque routier.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Source et licences

Données : Ministère de l'Intérieur et ONISR, bases annuelles BAAC publiées sur
[data.gouv.fr](https://www.data.gouv.fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2024),
sous Licence Ouverte.

Le code du projet est distribué sous licence MIT.
