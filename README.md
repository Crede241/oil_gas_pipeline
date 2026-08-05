# Documentation technique — Métriques et calculs du Dashboard Oil & Gas Analytics

## Sommaire

1. Modèle de données
2. KPI principaux (cartes en haut du dashboard)
3. Graphiques et agrégations
4. Formules détaillées
5. Génération des données sources (synthétiques)
6. Limites et notes méthodologiques

---

## 1. Modèle de données

Le dashboard s'appuie sur un modèle en étoile PostgreSQL (base `dw_oil_gas` / Supabase) :

**Dimensions**
- `dim_time` — calendrier (jour, mois, trimestre, année, semaine)
- `dim_field` — champs pétroliers
- `dim_well` — puits, rattachés à un champ
- `dim_equipment` — équipements, rattachés à un champ et un puits
- `dim_employee` — employés

**Faits**
- `fact_production` — une ligne par puits et par jour : barils extraits, coût, coût par baril
- `fact_maintenance` — une ligne par événement de panne : type de panne, temps d'arrêt, coût
- `fact_sales` — une ligne par vente : produit, quantité, prix, chiffre d'affaires

`app.py` récupère ces données via des requêtes SQL avec `JOIN` (voir `load_data()`), ce qui rattache chaque fait aux dimensions nécessaires (nom du champ, année/mois, type d'équipement, etc.) avant tout calcul côté Python/pandas.

---

## 2. KPI principaux (les 4 cartes en haut)

### 2.1 Production totale (barils)

```
Production totale = Σ barrels_extracted
```

Somme simple de la colonne `barrels_extracted` sur l'ensemble des lignes de `fact_production` retenues par les filtres (champ, années) actifs dans la barre latérale.

Code (`app.py`) :
```python
total_production = prod.barrels_extracted.sum()
```

### 2.2 Chiffre d'affaires

```
Chiffre d'affaires = Σ revenue = Σ (quantity_barrels × price_per_barrel)
```

`revenue` est déjà pré-calculé lors du chargement (voir section 4.3) ; le dashboard ne fait que sommer la colonne sur les ventes filtrées.

```python
total_revenue = sales.revenue.sum()
```

### 2.3 Coût moyen par baril

```
Coût moyen / baril = (Σ cost) / (Σ barrels_extracted)
```

⚠️ Ce n'est **pas** la moyenne simple des `cost_per_barrel` journaliers (ce qui donnerait un poids identique à un jour de faible production et un jour de forte production). C'est un **coût moyen pondéré par le volume**, plus représentatif économiquement : diviser la somme totale des coûts par la somme totale des barils.

```python
avg_cost_per_barrel = prod.cost.sum() / total_production if total_production else 0
```

### 2.4 Temps d'arrêt total (heures)

```
Temps d'arrêt total = Σ downtime_hours
```

Somme de toutes les durées de panne enregistrées dans `fact_maintenance`, sur le périmètre filtré (champ sélectionné, s'il y en a un).

```python
total_downtime = maint.downtime_hours.sum()
```

---

## 3. Graphiques et agrégations

### 3.1 Production mensuelle (courbe)

Regroupement (`GROUPBY`) par année et mois, puis somme des barils extraits :

```
Production(année, mois) = Σ barrels_extracted   pour toutes les lignes de cette (année, mois)
```

```python
monthly = prod.groupby(["year", "month"], as_index=False).barrels_extracted.sum()
```

L'axe X (`period`) est construit en concaténant année et mois au format `AAAA-MM` pour un tri chronologique correct.

### 3.2 Production par champ (barres)

```
Production(champ) = Σ barrels_extracted   pour toutes les lignes de ce champ
```

```python
by_field = prod.groupby("field_name", as_index=False).barrels_extracted.sum()
```

### 3.3 Pannes par type d'équipement (barres)

Comptage du nombre d'événements de maintenance, pas une somme de valeur :

```
Nombre de pannes(type équipement) = COUNT(maintenance_id)   pour ce type d'équipement
```

```python
by_equip = maint.groupby("equipment_type", as_index=False).agg(
    nb_pannes=("maintenance_id", "count"),
    downtime=("downtime_hours", "sum"),
)
```

(la colonne `downtime` est calculée en même temps mais n'est utilisée que si vous étendez le graphique)

### 3.4 Coût de maintenance par type de panne (camembert)

```
Coût(type de panne) = Σ cost   pour tous les événements de ce type de panne
```

```python
by_failure = maint.groupby("failure_type", as_index=False).cost.sum()
```

Le camembert affiche la **part relative** de chaque type de panne dans le coût total de maintenance, calculée automatiquement par Plotly (`part = coût du type / Σ coûts de tous les types`).

### 3.5 Ventes par type de produit (barres)

```
Chiffre d'affaires(produit) = Σ revenue   pour ce type de produit (brut, gaz, condensats)
```

```python
by_product = sales.groupby("product_type", as_index=False).revenue.sum()
```

### 3.6 Évolution du chiffre d'affaires (courbe)

Identique à 3.1 mais sur les ventes :

```
CA(année, mois) = Σ revenue   pour cette (année, mois)
```

```python
monthly_sales = sales.groupby(["year", "month"], as_index=False).revenue.sum()
```

---

## 4. Formules détaillées (calculées en amont, dans le pipeline)

Ces calculs ne sont **pas** faits dans `app.py` mais en amont, dans `scripts/transform.py`, au moment du chargement des données dans PostgreSQL.

### 4.1 Coût par baril (niveau ligne, `fact_production`)

```
cost_per_barrel = cost / barrels_extracted
```

Calculé pour **chaque ligne individuelle** (chaque puits, chaque jour) — c'est une métrique de granularité fine, différente du "coût moyen pondéré" du KPI global (section 2.3).

```python
production["cost_per_barrel"] = (
    production["cost"] / production["barrels_extracted"].replace(0, pd.NA)
).round(4)
```

Le `.replace(0, pd.NA)` évite une division par zéro si un puits n'a rien produit un jour donné (le résultat devient `NaN` plutôt qu'une erreur).

### 4.2 Colonnes calendaires (`dim_time`)

À partir de chaque date rencontrée dans les faits, on dérive :

```
année    = extraction de l'année de la date
mois     = extraction du mois (1-12)
trimestre = extraction du trimestre (1-4)
semaine  = numéro de semaine ISO (1-53)
```

```python
dim_time["year"] = dim_time.date_id.dt.year
dim_time["month"] = dim_time.date_id.dt.month
dim_time["quarter"] = dim_time.date_id.dt.quarter
dim_time["week"] = dim_time.date_id.dt.isocalendar().week
```

### 4.3 Chiffre d'affaires par vente (`fact_sales`)

```
revenue = quantity_barrels × price_per_barrel
```

Ce calcul est fait au moment de la **génération des données** (voir section 5), pas dans le pipeline de transformation — mais la logique reste la même partout où le CA apparaît.

---

## 5. Génération des données sources (synthétiques)

Les 7 fichiers CSV utilisés sont des données **fictives** générées par script Python (`generate_data.py`), avec les règles suivantes :

### 5.1 Production journalière (`production.csv`)

Pour chaque puits, un **débit de base** aléatoire est tiré :
```
débit_base ~ Uniforme(80, 400) barils/jour
```

Puis pour chaque jour de la période (2023-2024), on ajoute :
- un **bruit gaussien** : `bruit ~ Normale(0, 8% × débit_base)`
- une **légère tendance décroissante** : `-0.02 × nombre_de_jours_écoulés` (simule l'épuisement progressif du puits)

```
barils(jour) = max(0, débit_base + bruit − 0.02 × jours_écoulés)
```

Le coût journalier est tiré indépendamment :
```
coût(jour) = barils(jour) × Uniforme(8, 15)  [$/baril]
```

### 5.2 Maintenance (`maintenance.csv`)

150 événements générés aléatoirement :
```
downtime_hours ~ Uniforme(1, 48) heures
cost ~ Uniforme(500, 15000) $
```

Type de panne et équipement concerné tirés uniformément dans des listes prédéfinies.

### 5.3 Ventes (`sales.csv`)

500 ventes générées :
```
quantity_barrels ~ Entier Uniforme(500, 5000)
price_per_barrel ~ Uniforme(60, 95) $/baril   (fourchette réaliste Brent/WTI)
revenue = quantity_barrels × price_per_barrel
```

---

## 6. Limites et notes méthodologiques

- **Aucune modélisation prédictive** n'est appliquée dans le dashboard actuel (pas de régression, pas de prévision) — toutes les métriques sont **descriptives** (sommes, moyennes pondérées, comptages).
- Le **coût moyen par baril** (KPI) et le **coût par baril** (colonne détaillée) répondent à des questions différentes : le premier donne une vision globale économique, le second permet de repérer les puits ou journées les moins rentables.
- Les données étant synthétiques, les tendances (ex. déclin de production) sont **injectées volontairement** dans le générateur — elles ne reflètent aucune réalité pétrolière observée.
- Toutes les agrégations respectent les filtres actifs (champ pétrolier, années sélectionnées) définis dans la barre latérale de `app.py` avant tout calcul.
