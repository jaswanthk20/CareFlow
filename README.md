# CareFlow

**CareFlow** is an in-progress research project exploring how emergency department data can be used to better understand and eventually predict short-term ED pressure.

The project is currently in the **problem-definition and data-understanding stage**.

The main idea is to investigate whether historical ED arrival patterns and patient-level ED information can be used to estimate how busy an emergency department may become over the next **6–24 hours**, while also considering patients who are already present in the department.

---

## Project Idea

Emergency Department congestion is influenced by more than just the number of new patients arriving.

At any given time, ED pressure may depend on:

* how many patients are currently in the ED
* how many new patients are expected to arrive
* patient acuity and treatment requirements
* how long patients are expected to remain in the ED
* how quickly existing patients are discharged or admitted

The initial goal of CareFlow is to explore how these factors could eventually be combined into a framework for estimating future ED pressure.

A later stage of the project may explore whether potential operational bottlenecks can be identified and whether different interventions can be evaluated using simulation.

---

## Initial Research Question

> Can historical ED demand patterns and patient-level characteristics be used to estimate Emergency Department pressure 6–24 hours in advance?

The project will also explore questions such as:

* What patterns exist in hourly ED arrivals?
* How should current ED occupancy be considered alongside future arrivals?
* Which patient characteristics may influence ED length of stay?
* How can expected arrivals and expected departures eventually be combined into a useful measure of ED pressure?

---

## Datasets Identified

Two datasets are currently being considered for different parts of the research.

### Dryad ED Forecasting Dataset

The Dryad dataset provides information on **hourly patient arrivals to an Emergency Department**.

This dataset is being considered for studying:

* hourly arrival patterns
* time-of-day effects
* day-of-week patterns
* demand variability
* short-term ED arrival forecasting

The primary purpose of this dataset within CareFlow would be to understand **how many patients may arrive during upcoming time periods**.

---

### MIMIC-IV-ED

MIMIC-IV-ED contains patient-level Emergency Department data.

Available information includes variables related to areas such as:

* triage
* vital signs
* diagnosis
* medications
* treatment
* length of stay
* patient disposition

This dataset is being considered for understanding how different patient characteristics may relate to **ED workload and time spent in the department**.

---

## Dataset Strategy

The Dryad and MIMIC-IV-ED datasets come from different healthcare environments.

They will therefore **not be treated as if they represent patients from the same hospital**.

Instead, the current idea is to use them as complementary research datasets:

* **Dryad** → understand and forecast ED arrival demand
* **MIMIC-IV-ED** → investigate patient-level factors related to ED workload and length of stay

One of the research challenges will be determining how insights from these separate datasets can be used appropriately within a broader conceptual framework.

---

## Current Understanding

An important distinction in the project is between **ED arrivals** and **ED occupancy**.

### ED Arrivals

The number of patients entering the Emergency Department during a given period.

### ED Occupancy

The number of patients currently being treated or waiting within the Emergency Department.

Forecasting arrivals alone may not accurately describe future ED pressure.

For example, a moderate number of incoming patients could still create congestion if many existing patients are already occupying ED resources.

The current conceptual idea is therefore:

```text
Current ED Patients
        +
Expected Patient Arrivals
        -
Expected Patient Departures
        ↓
Potential Future ED Pressure
```

This is currently a research concept and has not yet been implemented.

---

## Planned Implementation

The project is expected to progress through several stages.

### 1. Data Understanding

* examine the structure of the Dryad dataset
* examine the structure of MIMIC-IV-ED
* identify usable variables
* assess data quality and limitations
* understand how ED arrivals and patient journeys are represented

### 2. Exploratory Analysis

For the arrival dataset:

* hourly demand patterns
* daily and weekly patterns
* variation in patient arrivals
* possible seasonality

For MIMIC-IV-ED:

* patient length-of-stay distributions
* triage characteristics
* diagnosis and treatment patterns
* factors potentially associated with longer ED stays

### 3. Arrival Forecasting

Develop and compare approaches for forecasting future ED arrivals over approximately **6–24 hours**.

Initial approaches may include simple statistical baselines before exploring more advanced forecasting methods.

### 4. Patient Workload Analysis

Explore whether patient-level information from MIMIC-IV-ED can help estimate expected ED length of stay or workload for different types of patients.

### 5. ED Pressure Framework

Investigate how the following components could eventually be combined:

```text
Current Occupancy
        +
Forecasted Arrivals
        +
Expected Patient Workload
        -
Expected Departures
```

The exact definition of an ED pressure metric has not yet been determined.

### 6. Simulation

If the forecasting and workload components are feasible, a later stage may explore a simplified Emergency Department simulation.

Potential questions could include:

* What happens when arrival volume increases?
* What happens when patient length of stay increases?
* How might changes in staffing or treatment capacity affect congestion?

This stage is currently only part of the project plan.

---

## Planned Tools

The project is expected to primarily use:

* Python
* Pandas
* NumPy
* Jupyter Notebook
* Matplotlib / data visualization libraries
* statistical and machine-learning libraries as required

Additional tools will be selected as the methodology develops.

---

## Project Status

**Current stage: Research and problem definition**

Completed so far:

* Defined the initial CareFlow project idea
* Identified short-term ED pressure forecasting as the primary problem
* Identified Dryad ED arrival data as a potential demand dataset
* Identified MIMIC-IV-ED as a potential patient-level ED dataset
* Established the distinction between ED arrivals and ED occupancy
* Identified the need to account for patients already present in the ED

Next steps:

* inspect both datasets in greater detail
* document available variables
* determine the initial target variable for forecasting
* begin exploratory analysis of ED arrival patterns
* define a simple baseline forecasting approach

---

## Project Goal

The long-term research direction of CareFlow is to explore whether data analytics, forecasting, and operations research can be combined to provide a clearer view of upcoming Emergency Department conditions.

The project is currently exploratory, and the methodology will evolve as the datasets are analyzed and the feasibility of each component is evaluated.

---

## Disclaimer

CareFlow is an independent research and portfolio project.

It is not a clinical decision-support system and is not intended for use in real-world medical or hospital operational decisions.
