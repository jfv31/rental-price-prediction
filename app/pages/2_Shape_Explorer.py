import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import load_shape_data

st.title("🔍 Shape Function Explorer")

st.markdown("""
Vergleich der marginalen Feature-Effekte auf **Mietpreis (€/m²)** und **Laufzeit (Tage)**
laut interpretierbarer Modelle (IGANN oder EBM).
""")

# ── Feature-Mapping: Anzeige-Name → interner Feature-Name ──────────────────
FEATURE_DISPLAY_TO_INTERNAL = {
    "wohnflaeche":                  "wohnflaeche",
    "zimmeranzahl":                 "zimmeranzahl",
    "schlafzimmer":                 "schlafzimmer",
    "badezimmer":                   "badezimmer",
    "alter_bauwerk (Baualter)":     "alter_bauwerk",
    "etage":                        "etage",
    "anzahletagen":                 "anzahletagen",
    "ajahr (Anzeigejahr)":          "ajahr",
    # Räumlich
    "dist_to_center":               "dist_to_center",
    "dist_transit":                 "dist_transit",
    "dist_supermarket":             "dist_supermarket",
    "dist_park":                    "dist_park",
    "dens_transit":                 "dens_transit",
    "dens_supermarket":             "dens_supermarket",
    "dens_park":                    "dens_park",
    # Kategorial
    "heizungsart":                  "heizungsart",
    "objektzustand":                "objektzustand",
    "ausstattung":                  "ausstattung",
    "blid (Bundesland)":            "blid",
    "erg_amd (Arbeitsmarktregion)": "erg_amd",
    # Sonstige numerisch
    "completeness_score":           "completeness_score",
    # Binär
    "balkon":                       "balkon",
    "keller":                       "keller",
    "aufzug":                       "aufzug",
    "einbaukueche":                 "einbaukueche",
    "garten":                       "garten",
    "gaestewc":                     "gaestewc",
    "parkplatz":                    "parkplatz",
    "haustier_erlaubt":             "haustier_erlaubt",
    "wurde_modernisiert":           "wurde_modernisiert",
}

# ── Binäre Features ─────────────────────────────────────────────────────────
BINARY_FEATURES = {"balkon", "keller", "aufzug", "einbaukueche", "garten",
                   "gaestewc", "parkplatz", "rollstuhlgerecht", "foerderung",
                   "denkmalobjekt", "haustier_erlaubt", "wurde_modernisiert",
                   "hat_energieausweis"}
# ── Kategorie-Legenden ───────────────────────────────────────────────────────
CATEGORY_LABELS = {
    "heizungsart": {
        -1: "Unbekannt", 1: "Blockheizkraftwerk", 2: "Elektro",
        3: "Etagenheizung", 4: "Fernwärme", 5: "Fußbodenheizung",
        6: "Gas", 7: "Holzpellets", 8: "Nachtspeicher", 9: "Ofen",
        10: "Öl", 11: "Solar", 12: "Wärmepumpe", 13: "Zentralheizung",
    },
    "objektzustand": {
        -1: "Unbekannt", 1: "Erstbezug", 2: "Erstbezug nach San.",
        3: "Wie Neu", 4: "Saniert", 5: "Modernisiert",
        6: "Vollsaniert", 7: "Gepflegt", 8: "Renovierungsbedarf",
        9: "Nach Vereinbarung", 10: "Abbruchreif",
    },
    "ausstattung": {
        -1: "Unbekannt", 1: "Einfach", 2: "Normal", 3: "Gehoben", 4: "Luxus",
    },
    "blid": {
        1: "Schleswig-Holstein", 2: "Hamburg", 3: "Niedersachsen",
        4: "Bremen", 5: "Nordrhein-Westfalen", 6: "Hessen",
        7: "Rheinland-Pfalz", 8: "Baden-Württemberg", 9: "Bayern",
        10: "Saarland", 11: "Berlin", 12: "Brandenburg",
        13: "Mecklenburg-Vorpommern", 14: "Sachsen",
        15: "Sachsen-Anhalt", 16: "Thüringen",
    },
    # erg_amd = lokale Arbeitsmarktregion nach Kosfeld & Werner (2012)
    # Numerischer Code mit >100 Regionen — kein vollständiges Mapping sinnvoll.
    # Wird im Shape Explorer als Hinweis angezeigt, nicht als Legende.
}

col1, col2, col3 = st.columns(3)

FEATURES_PLACEHOLDER = sorted(FEATURE_DISPLAY_TO_INTERNAL.keys())

with col1:
    selected_display = st.selectbox("Feature", FEATURES_PLACEHOLDER)
    selected_feature = FEATURE_DISPLAY_TO_INTERNAL[selected_display]
with col2:
    selected_model = st.radio("Modell", ["IGANN", "EBM"], horizontal=True, index=1)
    selected_models = [selected_model]
with col3:
    selected_targets = st.multiselect("Zielgröße", ["price", "duration"], default=["price", "duration"])

if not selected_models or not selected_targets:
    st.warning("Bitte mindestens ein Modell und eine Zielgröße auswählen.")
    st.stop()

if selected_model == "IGANN":
    st.warning(
        "⚠️ **IGANN-Hinweis:** IGANN erreicht in diesem Setup schwächere Prognosegüte für die Zielgrößen "
        "(höhere Fehler, geringere erklärte Varianz) als die führenden Modelle. Entsprechend sind die "
        "abgeleiteten Shape-Funktionen nur eingeschränkt belastbar und sollten nicht isoliert interpretiert "
        "werden; für inhaltliche Interpretation EBM-Patterns und Metrikvergleich priorisieren."
    )

is_binary = selected_feature in BINARY_FEATURES
has_legend = selected_feature in CATEGORY_LABELS

# ── Kategorie-Legende anzeigen ────────────────────────────────────────────
if has_legend:
    legend = CATEGORY_LABELS[selected_feature]
    legend_str = "  |  ".join(f"**{k}** = {v}" for k, v in sorted(legend.items()) if isinstance(k, int))
    st.info(f"📋 Kodierung: {legend_str}")
elif selected_feature == "erg_amd":
    st.info("📋 **erg_amd** = Lokale Arbeitsmarktregion nach Kosfeld & Werner (2012). "
            "Der numerische Code entspricht einer von >100 deutschen Arbeitsmarktregionen — "
            "der Shape zeigt den regionalen Effekt auf der x-Achse.")

colors = {"IGANN": "#636EFA", "EBM": "#EF553B"}
any_data = False

# ── Binäre Features: Balkendiagramm ──────────────────────────────────────
if is_binary:
    # Struktur: pro Target ein Subplot, pro Modell 2 Balken (Nein | Ja)
    # x-Werte: min(x) = Nein, max(x) = Ja — unabhängig vom EBM-Encoding (0/0.5 vs 0/1)
    target_labels_map = {"price": "Preis (€/m²)", "duration": "Laufzeit (log₁p Tage)"}
    targets_to_plot = [t for t in selected_targets]
    ncols = len(targets_to_plot)

    fig_bar = make_subplots(
        rows=1, cols=ncols,
        subplot_titles=[target_labels_map[t] for t in targets_to_plot],
    )

    igann_anchor_note = False  # wird True wenn IGANN-Nein-Balken herausgefiltert wird

    for ci, target in enumerate(targets_to_plot, start=1):
        for model_name in selected_models:
            df_shape = load_shape_data(model_name, target, selected_feature)
            if df_shape is None or df_shape.empty:
                continue
            any_data = True
            xs = df_shape["x"].values
            ys = df_shape["y"].values
            # Sortieren: erster Wert = Nein (kleinster x), zweiter = Ja
            order = xs.argsort()
            xs, ys = xs[order], ys[order]

            # IGANN ankert die Referenzklasse (Nein=0) immer bei y=0.
            # Diese Nullbalken werden herausgefiltert — nur "Ja"-Balken sind informativ.
            if model_name == "IGANN":
                mask = ys != 0.0
                if mask.sum() < len(ys):
                    igann_anchor_note = True
                xs, ys = xs[mask], ys[mask]

            # Labels ableiten
            if len(xs) >= 2:
                bar_labels = ["Nein", "Ja"]
            elif len(xs) == 1:
                bar_labels = ["Ja"] if xs[0] >= 0.5 else ["Nein"]
            else:
                bar_labels = []

            if not bar_labels:
                continue

            fig_bar.add_trace(
                go.Bar(
                    x=bar_labels[:len(xs)],
                    y=ys[:len(bar_labels)],
                    name=f"{model_name}",
                    marker_color=colors[model_name],
                    legendgroup=model_name,
                    showlegend=(ci == 1),
                    hovertemplate="%{x}: %{y:.4f}<extra>" + model_name + "</extra>",
                ),
                row=1, col=ci,
            )
        fig_bar.update_xaxes(title_text=f"{selected_feature} (0 = Nein, 1 = Ja)", row=1, col=ci)
        fig_bar.update_yaxes(title_text="Marginaler Effekt" if ci == 1 else "", row=1, col=ci)

    if not any_data:
        st.warning(f"⏳ Keine Shape-Daten für **{selected_display}** vorhanden.")
    else:
        fig_bar.update_layout(height=420, title_text=f"Shape — {selected_feature} (binär)",
                              barmode="group")
        st.plotly_chart(fig_bar, use_container_width=True)
        if igann_anchor_note:
            st.caption(
                "ℹ️ **IGANN:** Die Referenzklasse (Nein = 0) ist immer bei y = 0 geankert "
                "und wird nicht dargestellt. Der angezeigte Balken zeigt den marginalen Effekt "
                "von **Ja** relativ zum Basiszustand (Nein)."
            )

# ── Kontinuierliche / kategorische Features: Liniendiagramm ───────────────
else:
    target_labels_map = {"price": "Preis (€/m²)", "duration": "Laufzeit (log₁p Tage)"}
    fig = make_subplots(
        rows=1,
        cols=len(selected_targets),
        subplot_titles=[target_labels_map[t] for t in selected_targets],
        shared_yaxes=False,
    )
    for col_idx, target in enumerate(selected_targets, start=1):
        for model_name in selected_models:
            df_shape = load_shape_data(model_name, target, selected_feature)
            if df_shape is not None:
                any_data = True
                x_vals = df_shape["x"]
                # Kategorie-Achse: numerische Werte durch Labels ersetzen
                if has_legend:
                    legend = CATEGORY_LABELS[selected_feature]
                    x_labels = [legend.get(int(v), str(int(v))) for v in x_vals]
                else:
                    x_labels = x_vals
                fig.add_trace(
                    go.Scatter(
                        x=x_labels,
                        y=df_shape["y"],
                        mode="lines+markers" if has_legend else "lines",
                        name=f"{model_name}",
                        line=dict(color=colors[model_name], width=2),
                        hovertemplate=(
                            f"{selected_feature}: %{{x}}<br>"
                            f"Effekt: %{{y:.4f}}<extra>{model_name}</extra>"
                        ),
                    ),
                    row=1, col=col_idx,
                )
        y_label = "Mietpreis-Effekt (€/m²)" if target == "price" else "Laufzeit-Effekt (log₁p Tage)"
        fig.update_xaxes(title_text=selected_display, row=1, col=col_idx)
        fig.update_yaxes(title_text=y_label if col_idx == 1 else "", row=1, col=col_idx)

    if not any_data:
        st.warning(
            f"⏳ Keine Shape-Daten für **{selected_display}** vorhanden. "
            "NB03 & NB04 zuerst ausführen."
        )
    else:
        fig.update_layout(height=470, title_text=f"Shape Functions — {selected_display}")
        fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Shape Functions zeigen den marginalen Effekt eines Features bei konstanten anderen Variablen. "
    "IGANN nutzt neuronale Netz-Kurven; EBM nutzt Gradient-Boosting mit Binning."
)
