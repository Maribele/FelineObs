# FelineObs 🐈🔬

**FelineObs** is an early-stage, locally run application for recording, structuring, and reviewing observations of domestic cat behaviour. It is designed to support careful descriptions of observable events and transparent, source-linked scientific coding without automatically inferring emotions or intentions.

> **Project status:** Initial prototype (V23). The scientific catalogue is incomplete, and automated suggestions have **not** undergone independent scientific validation. FelineObs is not a veterinary diagnostic tool.

## What the initial version does

- Add and manage multiple cats; delete a cat only when no observations are linked to that record, to avoid accidental data loss.
- Record observations with date, time, focal cat, and free-text description.
- Break observations into chronological moments and observable elements (actions, posture/locomotion, ears, tail, eye orientation, and vocalisations).
- Review and edit saved observations and moments.
- Select a scientific publication for assisted coding; inspect candidate codes and supporting references; confirm or leave decisions pending.
- Keep observation data in a **local SQLite database** (`felineobs.db`).

## Scientific publications currently represented in the coding interface

The following are **separate coding sources**, not interchangeable definitions:

1. **Haywood et al. (2021)** — *Providing Humans With Practical, Best Practice Handling Guidelines During Human-Cat Interactions Increases Cats' Affiliative Behaviour and Reduces Aggression and Signs of Conflict*. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC8381768/) · [DOI](https://doi.org/10.3389/fvets.2021.714143). Initial subset of human-directed behavioural entries.
2. **Kappel, Riedel & Ganslosser (2024)** — *Ethogram of the Domestic Cat*. [Article](https://www.mdpi.com/2813-9372/1/3/21) · [DOI](https://doi.org/10.3390/pets1030021). The publication presents 117 behaviours in 12 categories; **only three entries** are represented in this prototype.
3. **Van Belle et al. (2025)** — *Development of the Ethogram of Feline Social Interactions (EFSI) to study intraspecific interactions between cats in multicat households*. [Article](https://www.sciencedirect.com/science/article/pii/S0168159125003600) · [DOI](https://doi.org/10.1016/j.applanim.2025.106862). The prototype represents the 23 behaviour labels and optional modifiers, with abbreviated descriptions. This is **not** a claim that all original operational criteria have been independently verified or that the implementation reproduces the published reliability results.

### Other scientific literature and resources considered

These resources inform possible future directions or provide background. **They are not bundled datasets, installed dependencies, or implemented coding systems in FelineObs.**

- **CatMeows** — Ludovico et al., *CatMeows: A Publicly-Available Dataset of Cat Vocalizations* (Zenodo, 2020; dataset described in a 2021 publication). [Dataset](https://zenodo.org/records/4008297) · [DOI](https://doi.org/10.5281/zenodo.4008297). A set of 440 meow recordings from 21 cats across three elicitation contexts; potentially relevant to future bioacoustics work. **No audio files or audio classifier are included.** Review the dataset's stated research/non-commercial terms before reuse.
- **Vitale & Udell (2019)** — *The quality of being sociable: The influence of human attentional state, population, and human familiarity on domestic cat sociability*. [PubMed](https://pubmed.ncbi.nlm.nih.gov/30391492/) · [DOI](https://doi.org/10.1016/j.beproc.2018.10.026). Background on human–cat sociability and the effects of human attention.
- **de Mouzon & Leboucher (2023)** — *Multimodal Communication in the Human–Cat Relationship: A Pilot Study*. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC10177025/) · [DOI](https://doi.org/10.3390/ani13091528). Background on visual, vocal, and combined human communication cues and observable feline responses. **Not an implemented coding source.**
- **Finka et al. (2022)** — *Investigation of humans individual differences as predictors of their animal interaction styles, focused on the domestic cat*. [Scientific Reports article](https://www.nature.com/articles/s41598-022-15194-7) · [DOI](https://doi.org/10.1038/s41598-022-15194-7). Background on variation in human–cat interaction styles. **Not an implemented coding source.**
- **Additional PubMed Central article supplied for review:** [PMC7536207](https://pmc.ncbi.nlm.nih.gov/articles/PMC7536207/). Bibliographic details and relevance should be confirmed before assigning it a specific role in the project; it is **not** represented as an implemented coding source.

### Related tools and applications considered

The following independent tools were considered as references to the wider feline welfare and behaviour landscape. **FelineObs does not integrate their software, models, scoring systems, or datasets, and no formal comparative benchmark has been performed.**

- **Feline Grimace Scale (FGS)** — [Official website](https://www.felinegrimacescale.com/). A validated facial-expression-based tool for assessing **acute pain** in cats. FelineObs does **not** implement FGS scoring or provide pain assessment; observational coding must not be confused with clinical pain evaluation.
- **PurrTrait Mood** — [Website](https://purrtrait.app/). A separate application describing photo/video-based feline body-language analysis and mood suggestions. FelineObs does **not** use its AI models or claim to infer emotions from visual cues.

The project's own interface is built with Streamlit. No third-party cat-observation application is claimed to be integrated or formally benchmarked.

## Research and literature review workflow

The development of FelineObs was informed by a literature review supported by **Google NotebookLM**. Scientific publications, feline ethograms, behavioural research, and publicly available datasets were collected as reference materials to explore approaches to feline behavioural observation and coding.

NotebookLM was used to support the organisation and comparison of those sources during early research and planning. The source collection included materials on cat vocalisations, domestic-cat ethograms, feline social interactions, human–cat communication, and human–cat interaction styles.

**Research use is not implementation:** Uploading or reviewing a source in NotebookLM does not mean its full ethogram, dataset, analytical method, or software has been implemented in FelineObs. Scientific coding definitions and coverage must be verified against the original publications, independently of AI-assisted summaries.

## Limitations and planned work

- Expand and verify the remaining definitions from Kappel's 117-behaviour ethogram and the relevant measures from Haywood et al.
- Check every incorporated EFSI definition and modifier against the original publication and its applicable social context.
- Evaluate coding reproducibility, accuracy, inter-observer agreement, and false suggestions using an independent test dataset.
- Extend the catalogue without conflating distinct operational definitions from different studies.
- Consider audio-based methods only after evaluating consent, data governance, and dataset usage terms.

**Important:** A keyword-based candidate suggestion is a prompt for review, **not** evidence that a published operational definition has been met. An uncoded observation does not imply that a behaviour is absent from the scientific literature.

## Run locally

Requirements: Python and the packages used by the app, including Streamlit. From the FelineObs project folder, with the existing virtual environment activated:

```bash
source .venv/bin/activate
python -m streamlit run app.py
```

Open the local URL printed by Streamlit (typically `http://localhost:8501`). The database is local; back it up before installing a new app version or making schema changes. If setting up a fresh project, initialise the required database tables before running the app; do **not** replace an existing database with an empty one.

## Privacy and data handling

- **Never commit `felineobs.db` or real observations to a public repository.**
- Keep `.gitignore` in the repository root and exclude `*.db`, SQLite journal/WAL files, `.venv/`, secrets, and backups.
- `.gitignore` does **not** remove files already tracked by Git or previously published in Git history. Verify before pushing, for example with `git status` and `git ls-files`.
- Running locally does not by itself guarantee security against anyone with access to the computer. Review hosting and access controls before deploying online.

## Technology

Python · Streamlit · SQLite

## Attribution and research integrity

Scientific publications and datasets remain the work of their respective authors. Links are provided for attribution and checking original definitions. FelineObs is an independent prototype; mentioning a publication does not imply endorsement by its authors or validation of the application. Do not redistribute third-party datasets or copyrighted material without checking the applicable licence.

## Project stage

**Initial prototype — scientific catalogue under development.** This README documents the current scope and the work still required; it is not a claim of a complete or scientifically validated ethogram implementation.

## License

FelineObs is an open-source project released under the **MIT License (2026)**.

You are free to use, modify, and distribute the software, provided that the original copyright and license notices are retained.

Scientific publications, datasets, and third-party resources remain subject to their respective licenses.
