import streamlit as st
import pandas as pd
import math

# Funzione per caricare il file Excel (modifica il path se necessario)
@st.cache_data
def load_data():
    # Carica il file Excel (metti il file nel repo o caricalo manualmente)
    df = pd.read_excel('stima_p_id_pfd.xlsx')
    return df

# Funzione per lookup ore drafting
def lookup_ore(df, tipo_doc, tool, emissioni, complessita):
    filtro = (
        (df['TIPO DI DOCUMENTO'] == tipo_doc) &
        (df['TOOL UTILIZZATO'] == tool) &
        (df['NUMERO DI EMISSIONI'] == emissioni) &
        (df['COMPLESSITA\''] == complessita)
    )
    risultati = df.loc[filtro, 'ORE TOTALI']
    if len(risultati) == 1:
        return risultati.values[0]
    else:
        return None

# Parametri pesi per tipologia P&ID
pesi_tipologia = {
    "processo": 1.0,
    "distributivo": 0.8,
    "legenda": 0.8,
    "interconnetting": 0.8,
    "tipico": 0.8,
    "macchine": 0.8
}

# Coefficienti per tool e partenza
tool_factor = {
    "AutoCAD": 1.0,
    "Microstation": 1.0,
    "SmartPlant P&ID": 1.5
}
start_type_factor = {
    "Da zero": 1.2,
    "Da semilavorato": 1.0,
    "Solo drafting": 0.8
}

# Funzione stima rapida ore drafting P&ID
def stima_ore_parametrica(numero_p_id, tipologie_selezionate, tool, partenza, emissioni):
    totale_pesato = 0
    for tip in tipologie_selezionate:
        peso = pesi_tipologia.get(tip, 0.8)
        totale_pesato += peso
    emission_factor = 1 + 0.1 * (emissioni - 1)
    ore = totale_pesato * 8 * tool_factor.get(tool, 1.0) * start_type_factor.get(partenza, 1.0) * emission_factor
    # Moltiplico per numero P&ID
    ore_tot = ore * numero_p_id
    return ore_tot

# Calcolo ore gestione progetto (solo se SOLO DRAFTING)
def calcola_ore_gestione(numero_p_id, durata_mesi):
    pid_per_persona = 150
    ore_mese_persona = 160
    numero_risorse = math.ceil(numero_p_id / pid_per_persona)
    ore_gestione = numero_risorse * durata_mesi * ore_mese_persona
    return ore_gestione, numero_risorse

def main():
    st.title("Stima ore per PFD e P&ID")

    df = load_data()

    # Input utente
    tipo_doc = st.selectbox("Tipo di documento", ["PFD", "P&ID"])
    tool = st.selectbox("Tool utilizzato", ["AutoCAD", "Microstation", "SmartPlant P&ID"])
    emissioni = st.slider("Numero di emissioni", 1, 5, 1)
    durata_progetto = st.number_input("Durata progetto (mesi)", min_value=1, max_value=60, value=6)

    numero_p_id = 0
    numero_pfd = 0

    if tipo_doc == "PFD":
        numero_pfd = st.number_input("Numero di PFD da realizzare", min_value=0, value=1)
    else:
        numero_p_id = st.number_input("Numero di P&ID da realizzare", min_value=0, value=1)

    partenza = "Solo drafting"
    complessita = "SOLO DRAFTING P&ID STANDARD"
    if tipo_doc == "P&ID":
        partenza = st.selectbox("Partenza", ["Da zero", "Da semilavorato", "Solo drafting"])
        complessita = st.selectbox("Complessità P&ID", [
            "SOLO DRAFTING P&ID STANDARD",
            "SOLO DRAFTING P&ID COMPLESSO",
            "PARTENDO DA ZERO",
            "PARTENDO DA SEMILAVORATO",
            "AS BUILT"
        ])

        tipologie_selezionate = st.multiselect(
            "Tipologia P&ID (scegli una o più opzioni)",
            list(pesi_tipologia.keys()),
            default=["processo"]
        )
    else:
        tipologie_selezionate = []

    metodo_stima = st.radio("Metodo di stima", ["Lookup da tabella", "Stima parametrica"])

    if st.button("Calcola stima"):
        if metodo_stima == "Lookup da tabella":
            # Cerca nella tabella
            ore_disegno = lookup_ore(df, tipo_doc, tool, emissioni, complessita)
            if ore_disegno is None:
                st.error("Nessun dato trovato nella tabella per i parametri scelti.")
                return
            else:
                st.write(f"Ore disegno (lookup): {ore_disegno:.2f}")

            # Ore gestione solo se P&ID e complessità SOLO DRAFTING
            if tipo_doc == "P&ID" and "SOLO DRAFTING" in complessita:
                ore_gestione, risorse = calcola_ore_gestione(numero_p_id, durata_progetto)
                st.write(f"Ore gestione progetto: {ore_gestione:.2f}")
                st.write(f"Numero minimo risorse: {risorse}")
            else:
                ore_gestione = 0
                st.write("Ore gestione progetto: 0 (incluso nella stima)")

            ore_totali = ore_disegno * max(numero_p_id if tipo_doc=="P&ID" else numero_pfd, 1) + ore_gestione
            st.write(f"Ore totali stimate: {ore_totali:.2f}")

        else:
            # Stima parametrica
            ore_disegno = 0
            if tipo_doc == "P&ID":
                ore_disegno = stima_ore_parametrica(numero_p_id, tipologie_selezionate, tool, partenza, emissioni)
                ore_gestione, risorse = calcola_ore_gestione(numero_p_id, durata_progetto)
                st.write(f"Ore disegno (parametrica): {ore_disegno:.2f}")
                st.write(f"Ore gestione progetto: {ore_gestione:.2f}")
                st.write(f"Numero minimo risorse: {risorse}")
                ore_totali = ore_disegno + ore_gestione
                st.write(f"Ore totali stimate: {ore_totali:.2f}")
            else:
                # PFD
                ore_disegno = lookup_ore(df, tipo_doc, tool, emissioni, "SOLO DRAFTING STANDARD")
                if ore_disegno is None:
                    st.error("Nessun dato trovato nella tabella per i parametri scelti.")
                    return
                ore_totali = ore_disegno * numero_pfd
                st.write(f"Ore disegno (parametrica per PFD): {ore_totali:.2f}")

if __name__ == "__main__":
    main()
