# Truth Matrix: TeX-Konsistenzcheck

Stand: 2026-07-12

## Rahmen

- Ziel: minimale, belegbasierte Korrekturen in den TeX-Kapiteln.
- Modus: nur Analyse- und Entscheidungsdokument, keine TeX-Edits.
- Team-Annahme: TabICLv2 und XGBoost-Finallaeufe kamen von Kollegen-Rechner.
- Externer Log (`log_gpu_vollversuch_2026-07-11.txt`) lokal nicht vorhanden.

## Source-of-Truth-Hierarchie

1. Laufartefakte (`models/*.json`, `models/*.csv`, belastbare Run-Logs)
2. Notebook-Code plus ausgegebene Notebook-Outputs
3. TeX-Prosa und TeX-Tabellen

Regel: Bei Konflikt wird Ebene 3 an Ebene 1/2 angepasst.

## Konfliktregister und Entscheidungen

### T01 TabICLv2-Protokoll in Section 4.3 (512/CPU/CV)

- Ist-Konflikt:
	- TeX sagt 512 Beobachtungen pro CV-Fold auf Standard-CPU.
	- Ergebnisabschnitte nutzen TabICLv2 als regulaeren Testset-Resultatpunkt.
- Harte Evidenz lokal:
	- [tex/Section4.3.tex](tex/Section4.3.tex#L120)
	- [tex/Section5.2.tex](tex/Section5.2.tex#L22)
	- [tex/Section5.3.tex](tex/Section5.3.tex#L17)
- Externe Evidenz:
	- Kollegenangabe: 100000 Kontextzeilen, GPU (RTX 5070 Ti, 16 GB), OOT-Test.
- Entscheidung:
	- 4.3-Absatz als veraltet markieren und auf Team-Protokoll umstellen.
	- Im Text transparent machen: TabICLv2/XGBoost auf separatem Rechner gerechnet.
	- Kein CV-Wording fuer TabICLv2 in Methoden- und Ergebnistext.

### T02 TabICLv2 in Modelltabelle als "Post-hoc via SHAP"

- Ist-Konflikt:
	- Tabelle behauptet SHAP fuer TabICLv2.
	- SHAP-Pipeline bezieht sich auf XGBoost, nicht TabICLv2.
- Evidenz:
	- [tex/Section4.3.tex](tex/Section4.3.tex#L56)
	- [notebooks/05_shape_comparison.ipynb](notebooks/05_shape_comparison.ipynb#L662)
	- [notebooks/05_shape_comparison.ipynb](notebooks/05_shape_comparison.ipynb#L679)
- Entscheidung:
	- TabICLv2-Interpretability in Tabelle auf "Keine studienspezifische post-hoc Analyse" (oder aequivalent) setzen.

### T03 32 vs 38 Features

- Ist-Konflikt:
	- 5.2 sagt 32 Features.
	- 4.3 und Shape-Artefakte sind konsistent mit 38.
- Evidenz:
	- [tex/Section5.2.tex](tex/Section5.2.tex#L5)
	- [tex/Section4.3.tex](tex/Section4.3.tex#L6)
	- [notebooks/05_shape_comparison.ipynb](notebooks/05_shape_comparison.ipynb#L42)
- Entscheidung:
	- 5.2 auf 38 Features korrigieren.

### T04 IGANN-Prosa in 5.1 widerspricht Tabelle und Artefakten

- Ist-Konflikt:
	- Prosa nennt 0.133 vs 0.001, 500 vs 1000, "only three trials".
	- Tabelle und `best_params` zeigen identische A/B-Parameter.
- Evidenz:
	- [tex/Section5.1.tex](tex/Section5.1.tex#L97)
	- [tex/Section5.1.tex](tex/Section5.1.tex#L66)
	- [models/best_params_igann_price.json](models/best_params_igann_price.json#L1)
	- [models/best_params_igann_duration.json](models/best_params_igann_duration.json#L1)
	- [models/hpa_trials_igann_price.csv](models/hpa_trials_igann_price.csv#L1)
	- [models/hpa_trials_igann_duration.csv](models/hpa_trials_igann_duration.csv#L1)
- Entscheidung:
	- IGANN-Interpretationsabsatz komplett neu auf realen Artefakten formulieren.
	- Trial-Anzahl einheitlich definieren (completed trials) und entsprechend schreiben.

### T05 Optuna-Zitat in 4.4

- Ist-Konflikt:
	- Optuna wird mit Molnar zitiert.
- Evidenz:
	- [tex/Section4.4.tex](tex/Section4.4.tex#L56)
	- [tex/Quellen (1).bib](tex/Quellen%20(1).bib#L410)
- Entscheidung:
	- Zitat auf `akiba_optuna_2019` umstellen.

### T06 Decision Tree "mediocre" bei MAE 1.78

- Ist-Konflikt:
	- 1.78 waere besser als bestes Modell in 5.2.
- Evidenz:
	- [tex/Section4.3.tex](tex/Section4.3.tex#L28)
	- [tex/Section5.2.tex](tex/Section5.2.tex#L34)
- Entscheidung:
	- Ausschlussbegruendung neu formulieren, ohne unvereinbare Kennzahl.
	- Wenn kein reproduzierbarer Split-Beleg fuer 1.78 vorliegt: Zahl entfernen.

### T07 Imputation- und Encoding-Widerspruch 4.3/4.4 vs Notebook-Implementierung

- Ist-Konflikt:
	- 4.3 sagt fuer EBM: Imputation plus Ordinal-Encoding.
	- NB06 sagt fuer EBM: nur Imputation, kein Encoder.
	- Tree-Modelle nativ NaN in Theorie, aber in NB03/04 teils defensives Preprocessing.
- Evidenz:
	- [tex/Section4.3.tex](tex/Section4.3.tex#L178)
	- [tex/Section4.3.tex](tex/Section4.3.tex#L100)
	- [notebooks/06_hyperparameter_analysis.ipynb](notebooks/06_hyperparameter_analysis.ipynb#L425)
	- [notebooks/06_hyperparameter_analysis.ipynb](notebooks/06_hyperparameter_analysis.ipynb#L25)
- Entscheidung:
	- Methodenbeschreibung strikt auf finale Pipeline angleichen:
		- EBM: Imputation ohne OrdinalEncoder (wenn so final gefahren).
		- LR/IGANN/TabICL: Imputation plus OHE-Variante ohne `erg_amd`.
		- XGB/LGBM: konsistent dokumentieren, ob nativ oder mit vorgelagerter defensiver Kodierung.

### T08 "Uniform feature matrix" vs `erg_amd`-Drop

- Ist-Konflikt:
	- Text behauptet uniforme Feature-Matrix fuer alle Modelle.
	- Notebooks droppen `erg_amd` fuer LR/IGANN/TabICL.
- Evidenz:
	- [tex/Section4.3.tex](tex/Section4.3.tex#L118)
	- [notebooks/03_model_A_price.ipynb](notebooks/03_model_A_price.ipynb#L327)
	- [notebooks/04_model_B_duration.ipynb](notebooks/04_model_B_duration.ipynb#L340)
	- [notebooks/06_hyperparameter_analysis.ipynb](notebooks/06_hyperparameter_analysis.ipynb#L395)
- Entscheidung:
	- Uniform-Claim praezisieren: gemeinsame Kernvariablen, aber modellspezifische Kodierung/Dimensionalitaetsreduktion.

### T09 HPO-Sample-Groesse 117k und moegliches Temporal Leakage

- Ist-Konflikt:
	- 4.4 sagt 1% Training ~117k.
	- NB06 zeigt 1% gesamt ~115k, nach Zeitfilter `ajahr <= 2021` nur ~92k.
- Evidenz:
	- [tex/Section4.4.tex](tex/Section4.4.tex#L42)
	- [notebooks/06_hyperparameter_analysis.ipynb](notebooks/06_hyperparameter_analysis.ipynb#L199)
	- [notebooks/06_hyperparameter_analysis.ipynb](notebooks/06_hyperparameter_analysis.ipynb#L200)
- Entscheidung:
	- HPO-Sampletext umstellen auf tatsaechlichen Ablauf:
		- erst 1%-Stratified aus Gesamtbasis,
		- dann temporaler Filter fuer HPO-Trainingsjahre.
	- Jahresgrenze (2021 oder 2022) konsistent mit finalem Notebook-Lauf festhalten.

### T10 Zahlendreher in 5.2 bei TabICL vs IGANN

- Ist-Konflikt:
	- Satz stellt MAE-Reihenfolge missverstaendlich/verdreht dar.
- Evidenz:
	- [tex/Section5.2.tex](tex/Section5.2.tex#L62)
	- [tex/Section5.2.tex](tex/Section5.2.tex#L36)
- Entscheidung:
	- Satz auf eindeutige Form bringen: TabICLv2 (2.791) vor IGANN (2.837) in MAE.

### T11 Zero-shot-Label fuer TabICLv2

- Ist-Konflikt:
	- "zero-shot" in Ergebnisteilen, gleichzeitig widerspruechliche Protokollbeschreibung in 4.3.
- Evidenz:
	- [tex/Section5.2.tex](tex/Section5.2.tex#L22)
	- [tex/Section5.3.tex](tex/Section5.3.tex#L17)
	- [tex/Section4.3.tex](tex/Section4.3.tex#L120)
- Entscheidung:
	- Begriff beibehalten nur wenn methodisch exakt zutreffend fuer den Team-Run.
	- Sonst neutralisieren auf "ohne targetspezifisches HPO".

## Minimaler Eingriffsplan (Reihenfolge)

1. Harte Konsistenzfehler zuerst: T05, T10, T03.
2. Methodenwahrheit angleichen: T01, T07, T08, T09, T11.
3. Narrative Korrektur: T04, T06, T02.
4. Abschliessender Konsistenz-Readthrough zwischen 4.3, 4.4, 5.1, 5.2, 5.3.

## Offene Entscheidungen vor Edit-Phase

- O01: Endgueltige Formulierung fuer TabICLv2-Rechenumgebung ohne lokalen Log.
- O02: Exakte Definition von "Trials" in 5.1 (completed vs attempted).
- O03: Exakte Jahresgrenze fuer HPO-Filter im Text (Notebook zeigt `<= 2021`).
- O04: Ob "zero-shot" fuer TabICLv2 im Paper beibehalten oder neutralisiert wird.

## Soll-Satzbausteine (minimal, copy-ready)

### S01 Ersatz fuer TabICLv2-Absatz in Section 4.3

TabICLv2 was evaluated as an external reference model without target-specific hyperparameter optimization.
Due to memory constraints of in-context inference, the model used a fixed-size random subset of the training data as context and was evaluated once on the same held-out temporal test set (2023--2025) used for the other models.
Implementation and execution were performed on a separate team machine; results are reported for comparability, while interpretability analysis in this study focuses on EBM/IGANN shape functions and TreeSHAP for gradient-boosted trees.

### S02 Ersatz fuer TabICLv2-Interpretability in Tabelle 4.3

`TabICLv2 | TFM | No model-specific interpretation in this study | No |`

### S03 32-zu-38-Feature-Korrektur in 5.2

... (968,884 observations; 84.2\,\% of the full 10\,\% sample; 38 features) ...

### S04 IGANN-Prosa in 5.1 (konsistent mit Artefakten)

For IGANN, the best configurations selected by Optuna were identical across both targets in this run (\texttt{n\_hid}=64, \texttt{n\_estimators}=500, \texttt{boost\_rate}=0.190, \texttt{elm\_scale}=0.773, \texttt{elm\_alpha}=0.133).
This pattern indicates that, under the given timeout and search setup, the optimizer converged to the same parameter region for both tasks rather than yielding strongly target-specific IGANN settings.

### S05 Optuna-Zitat in 4.4

Hyperparameter optimization is conducted using the \textit{Optuna} framework \parencite{akiba_optuna_2019} with the Tree-structured Parzen Estimator (TPE) as the acquisition function.

### S06 Decision-Tree-Begruendung neutral

A Decision Tree regressor was tested in preliminary experiments but excluded from the main model portfolio because it did not add analytical value beyond the selected baseline and ensemble/interpretable model set under the final evaluation protocol.

### S07 Imputation/Encoding konsistent formulieren

For non-tree models, preprocessing was fitted inside the corresponding training workflow to avoid leakage.
Numeric features were median-imputed; categorical/binary features were imputed with the most frequent value.
For LR/IGANN/TabICLv2, one-hot encoding was used in the linearized feature space (with \texttt{erg\_amd} excluded for dimensionality control), while EBM was trained on imputed features without additional ordinal encoding.

### S08 Uniform-Feature-Matrix praezisieren

All models are based on the same core feature set, while model-family-specific preprocessing (encoding and dimensionality control) was applied where required by the respective estimator.

### S09 HPO-Sampletext korrigieren

During hyperparameter search, we first drew a 1\,\% stratified sample by listing year from the full processed dataset and then restricted this sample to pre-cutoff years used for model training, yielding the final HPO sample used in 3-fold cross-validation.

### S10 MAE-Satz in 5.2 korrekt

IGANN achieves $R^2 = 0.491$ and places fifth despite hyperparameter tuning, with a higher MAE than TabICLv2 (2.837 vs. 2.791\,EUR/m\textsuperscript{2}).

### S11 Zero-shot neutralisieren (Option)

TabICLv2\textsuperscript{$\dagger$} evaluated without target-specific hyperparameter tuning.
