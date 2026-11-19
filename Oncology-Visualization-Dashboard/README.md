# Interactive Oncology Data Visualization Dashboard

An interactive dashboard for exploring oncology data across cancer types, metastatic sites, and histological subtypes, with clinical filtering and survival visualizations.

## Visual walkthrough

### Default interface

![Default dashboard — overview 1](images/Screenshot%202026-05-23%20110201.png)

![Default dashboard — overview 2](images/Screenshot%202026-05-23%20110225.png)

![Default dashboard — overview 3](images/Screenshot%202026-05-23%20110241.png)

### Interface with a selected element

Selecting an element highlights only the nodes and connections associated with that selection.

#### Selecting a cancer type

![Cancer type selected](images/Screenshot%202026-05-23%20110311.png)

#### Selecting a metastatic site

![Metastatic site selected](images/Pasted%20image%2020260523112504.png)

### Example with filters applied

<img src="images/Pasted%20image%2020260523111540.png" alt="Dashboard filter selection" width="157"> <img src="images/Pasted%20image%2020260523111523.png" alt="Dashboard with filters applied" width="493">

### Exploring a single cancer type

When a single cancer type is selected, the dashboard allows users to explore it as a whole or examine its individual histological subtypes.

#### Single cancer overview

<img src="images/Pasted%20image%2020260523112021.png" alt="Single cancer selection" width="151"> <img src="images/Pasted%20image%2020260523111946.png" alt="Single cancer overview" width="495">

#### Histology overview

<img src="images/Pasted%20image%2020260523112153.png" alt="Histology selection" width="134"> <img src="images/Pasted%20image%2020260523112218.png" alt="Histology overview" width="496">

#### Selecting a histological subtype

<img src="images/Pasted%20image%2020260523112352.png" alt="Selected histological subtype" width="648">

### Project structure

- `app.py` — Dash interface and callbacks.
- `loader.py` — clinical data loading and preparation.
- `transforms.py` — filtering and data transformations.
- `charts/` — Sankey, age-related, and Kaplan–Meier survival visualizations.
- `filtering.ipynb` — data-processing notebook.
- `images/` — screenshots used in this README.

### Running the dashboard locally

With Python installed, install the main dependencies:
```bash
pip install dash plotly pandas
```

then run:
```bash
python app.py
```