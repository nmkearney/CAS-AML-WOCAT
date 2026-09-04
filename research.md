# Resources

WOCAT Questionnaire on SLM Technologies: https://wocat.net/documents/447/QT_English_2019_CClicence.docx

# Module 1: Unsupervised machine learning

## Research questions

- How do SLM Technologies cluster geographically?

## Data

(Sections of the WOCAT Questionnaire on SLM Technologies are in parentheses)

### Essential input data

- Latitude and longitude (2.5)
- Altitudinal zone (5.2): 9 levels
- Agro-climatic zone (5.1): Humid, sub-humid, semi-arid, arid
- SLM group to which the Technology belongs (3.5): 26 categories, and "other"

### Optional input data

- Current land use type(s) where the Technology is applied: 8 high-level categories, and "other"
- Land use before the implementation of this Technology (3.3): 8 high-level categories, and "other"
- Date of implementation (2.6): Recent (<10 years), 10-50 years, traditional (50+ years)

## Methods and approach

- K-means clustering
- Grid search with 2-n centroids (e.g., n = 20)
- Select optimal cluster based on indicator (TBD)
- Interpret clusters (e.g., why might we see certain SLM Technologies in the same cluster?)

## Open questions

- Some entries specify coordinates for multiple sites. Do we take the midpoint among them?

# Module 2: Supervised machine learning

## Research questions

- Which features of SLM Technologies predict high versus low improvements in biodiversity?

## Data

(Sections of the WOCAT Questionnaire on SLM Technologies are in parentheses)

### Essential input data

- SLM group to which the Technology belongs (3.5): 26 categories, and "other"
- SLM measures comprising the Technology (3.6): Agronomic, vegetative, structural, management, and "other"
- Main types of land degradation addressed by the Technology (3.7): Soil erosion by water, soil erosion by wind, chemical soil degradation, physical soil degradation, biological degradation, water degradation
- Water availability and quality (5.4): Groundwater table, Availability of surface water
- Cost of inputs needed for establishment (4.4): Total cost of establishing the Technology in USD
- Cost of inputs and recurrent activities needed for maintenance per year (4.6): Total cost of maintaining the Technology in USD

### Optional input data (e.g., as controls)

- Main purpose(s) of the Technology (3.1): 9 categories, and "other"
- Current land use type(s) where the Technology is applied: 8 high-level categories, and "other"
- Land use before the implementation of this Technology (3.3): 8 high-level categories, and "other"
- Water supply: Rainfed, mixed rainfed-irrigated, full irrigated, and "other (e.g. post flooding)"
- Tillage system (3.6): No tillage, reduced tillage (>30% soil cover), full tillage (<30% soil cover)
- Prevention, reduction, or restoration of land degradation (3.8): To prevent/avoid land degradation, to reduce land degradation, to restore/rehabilitate degraded land/reverse land degradation, to adapt to land degradation, not applicable
- Agro-climatic zone (5.1): Humid, sub-humid, semi-arid, arid
- Slopes on average (6.2): 7 levels
- Compiler (1.2): Control for bias
- Date of implementation (2.6): Recent (<10 years), 10-50 years, traditional (50+ years)

### Output data

- Biodiversity variables (5.5): Species diversity (5.5), Habitat diversity (5.5)
- Biodiversity variables (6.1): Vegetation cover, **biomass/above-ground C**, plant diversity, invasive alien species, animal diversity, beneficial species (predators, earthworms, pollinators), harmful species (e.g., mosquitos), habitat diversity, pest/diseases

## Methods and approach

- Discretize output variable at the median (binary classification: high versus low improvements in biomass/above-ground C)
- Random forest analysis: how important are the input features for classifying an SLM Technology as having a high versus low improvement in biodiversity?
- Neural network: Train on a stratified sample of SLM Technologies and predict whether the improvement in biodiversity is high versus low.

## Open questions

- WOCAT is primarily interested in biomass/above-ground C. Should we start with this variable as our output variable, and then conduct a more extensive analysis on biodiversity if necessary/of interest? If using additional biodiversity variables, start with dimensionality reduction?
- Are SLM Technology and measures highly correlated? If so, can we use just SLM Technology?
- Should we use random forest analysis and/or neural networks?
- Can we use the neural network for anything besides predicting the right class?
- Section 5.6 contains information about the land users (e.g., sedentary vs. nomadic, young vs. old). Potentially of interest, but perhaps too much for this assignment?
