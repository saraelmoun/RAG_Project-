"""Interface Gradio (format chat) pour explorer le RAG.

Conversation : chaque question -> une reponse claire (Avec RAG), avec « Sans RAG » et les
sources en volets repliables. Barre laterale = choix de la base (drag&drop fichiers OU
dataset neural-bridge). Aucune logique RAG nouvelle : on reutilise ingest.py / query.py.
Direction artistique alignee sur site/index.html. Page d'accueil servie a '/', app sous '/app'.

Lancer depuis la racine :  PYTHONPATH=. python app.py   (ou : make app)
"""

import html
import os
import random
import re

import gradio as gr

import config
from ingest.ingest import ingest_documents
from query.query import answer_with_rag, answer_without_rag, source_rows

DATASET_NAME = "neural-bridge/rag-dataset-12000"


# ----------------------------------------------------------------------------
# Handlers de base (LOGIQUE INCHANGEE — reutilisent ingest.py / query.py)
# ----------------------------------------------------------------------------
def handle_upload(files):
    """Vide la table puis ingere les fichiers deposes. Retourne un statut lisible."""
    if not files:
        return "Aucun fichier depose. Glisse des .md ou .txt puis clique sur Ingerer."

    documents = []
    for path in files:
        source = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            documents.append((source, f.read()))

    stats = ingest_documents(documents, reset=True)  # un seul corpus a la fois
    return f"● base active : {stats['files']} fichier(s) · {stats['inserted']} chunks"


def handle_load_dataset(n):
    """Vide la base puis ingere le champ `context` des N premieres lignes du dataset.

    Retourne (statut, lignes_chargees) ; lignes = [{question, answer}] -> gr.State.
    """
    from datasets import load_dataset  # import paresseux

    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 100
    n = max(1, n)

    ds = load_dataset(DATASET_NAME, split="train")
    n = min(n, len(ds))
    ds = ds.select(range(n))

    documents = [(f"neural-bridge#{i}", row["context"]) for i, row in enumerate(ds)]
    stats = ingest_documents(documents, reset=True)

    loaded = [{"question": row["question"], "answer": row["answer"]} for row in ds]
    status = f"● base active : {stats['files']} lignes · {stats['inserted']} chunks"
    return status, loaded


def handle_draw_question(loaded):
    """Tire une ligne au hasard : remplit le champ question + memorise sa reponse attendue."""
    if not loaded:
        return "", ""
    row = random.choice(loaded)
    return row["question"], row["answer"]


# ----------------------------------------------------------------------------
# Rendu du fil de conversation (HTML — repliables natifs <details>)
# ----------------------------------------------------------------------------
def _md(text):
    """Mini markdown -> HTML : echappe, gere **gras** et les retours a la ligne."""
    safe = html.escape((text or "").strip())
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
    return safe.replace("\n", "<br>")


def _sources_cards(passages):
    """Cartes de sources (pour l'interieur d'un <details>)."""
    cartes = []
    for i, source, distance, extrait in source_rows(passages):
        cartes.append(
            '<div class="src-card">'
            f'<div class="src-h"><span class="src-n">{html.escape(source)}</span>'
            f'<span class="src-d">#{i} · {distance:.3f}</span></div>'
            f'<div class="src-e">{html.escape(extrait)}…</div>'
            "</div>"
        )
    return "".join(cartes)


def render_thread(history):
    """Construit tout le fil : bulle question + reponse RAG + repliables (sources / sans RAG / attendu)."""
    if not history:
        return (
            '<div class="thread"><div class="empty">'
            "Pose ta première question — la réponse s'appuie sur ta base et cite ses sources."
            "</div></div>"
        )

    turns = []
    for t in history:
        q = html.escape(t["question"])
        turn = [f'<div class="turn"><div class="you">{q}</div>']

        if t.get("pending"):
            turn.append(
                '<div class="answer"><div class="alabel"><span class="dot"></span>réponse · avec RAG</div>'
                '<p class="miss">⏳ génération en cours…</p></div></div>'
            )
            turns.append("".join(turn))
            continue

        turn.append('<div class="answer">')
        turn.append('<div class="alabel"><span class="dot"></span>réponse · avec RAG</div>')
        turn.append(f"<p>{_md(t['avec'])}</p>")

        # Sources repliables
        n = t.get("n_sources", 0)
        if n:
            turn.append(
                f'<details class="dd src-dd"><summary>▾ {n} source'
                f'{"s" if n > 1 else ""}</summary>{t["sources"]}</details>'
            )

        # Sans RAG repliable (muted)
        turn.append(
            '<details class="dd norag"><summary>▸ et sans RAG ? (modèle seul)</summary>'
            f"<p>{_md(t['sans'])}</p></details>"
        )

        # Reponse attendue (dataset) repliable, si dispo
        if t.get("expected"):
            turn.append(
                '<details class="dd expect"><summary>▸ réponse attendue (dataset)</summary>'
                f"<p>{_md(t['expected'])}</p></details>"
            )

        turn.append("</div></div>")  # close .answer + .turn
        turns.append("".join(turn))

    return '<div class="thread">' + "".join(turns) + "</div>"


def handle_ask(question, history, pending_expected):
    """Generateur : affiche un tour 'en cours' immediat, puis la reponse RAG complete.

    Reutilise answer_without_rag / answer_with_rag (aucune logique nouvelle).
    Sorties : (history, fil_html, champ_question_vide, pending_expected_reset).
    """
    q = (question or "").strip()
    if not q:
        yield history, render_thread(history), gr.update(), pending_expected
        return

    # 1) feedback immediat : tour 'en cours', champ vide.
    pending = history + [{"question": q, "pending": True}]
    yield history, render_thread(pending), "", pending_expected

    # 2) calcul reel.
    sans = answer_without_rag(q)
    avec, passages = answer_with_rag(q)
    turn = {
        "question": q,
        "avec": avec.strip(),
        "sans": sans.strip(),
        "n_sources": len(passages),
        "sources": _sources_cards(passages),
    }
    if pending_expected:
        turn["expected"] = pending_expected

    history = history + [turn]
    yield history, render_thread(history), "", ""  # reset pending_expected


# ----------------------------------------------------------------------------
# Apparence : DA de site/mockup.html (chat epure, sombre / vert / ambre)
# ----------------------------------------------------------------------------
THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.green,
    neutral_hue=gr.themes.colors.gray,
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg:#0A0A0F; --bg-2:#16161D; --surface:#1C1C24;
  --border:rgba(255,255,255,.08); --border-strong:rgba(255,255,255,.16);
  --accent:#22C55E; --neon:#4ADE80; --amber:#F59E0B; --amber-l:#FBBF24;
  --text:#F4F4F5; --text-bright:#E4E4E7; --text-dim:#A0A0AB;
  --radius:12px; --t:150ms ease;
  --mono:"JetBrains Mono",ui-monospace,Menlo,monospace;
  --sans:"Inter",system-ui,-apple-system,sans-serif;
}
.gradio-container, .gradio-container * { font-family: var(--sans); }
html, body, gradio-app, .gradio-container { background: var(--bg) !important; }
.gradio-container { color: var(--text) !important; max-width: 100% !important; padding: 0 !important; }
.gradio-container .gap { gap: 0 !important; }
.gradio-container .block, .gradio-container .form { background: transparent !important; border: none !important; }
footer { display: none !important; }
.muted { color: var(--text-dim) !important; }

/* ===== Layout : sidebar + main ===== */
#layout { gap: 0 !important; align-items: stretch !important; min-height: 100vh; flex-wrap: nowrap !important; }
.side { background: var(--bg-2) !important; border-right: 1px solid var(--border) !important;
  padding: 18px 16px !important; gap: 18px !important; }
.side .brand { font-weight: 600; font-size: 15px; }
.side .brand .mono { color: var(--neon); font-family: var(--mono); }
.side .brand .hl { background: linear-gradient(100deg,var(--neon),var(--accent)); -webkit-background-clip:text; background-clip:text; color:transparent; }
.side h4 { font-family: var(--mono); color: var(--neon); font-size: 11px; letter-spacing:.04em; text-transform:uppercase; margin: 4px 0 -2px; }

/* selecteur de source en segmente */
.seg { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 10px !important; padding: 3px !important; }
.seg .wrap, .seg fieldset { border: none !important; background: transparent !important; gap: 3px !important; }
.seg label { background: transparent !important; border: none !important; color: var(--text-dim) !important; border-radius: 7px !important; padding: 7px 10px !important; font-size: 12.5px !important; }
.seg label.selected, .seg input:checked + span { color: var(--neon) !important; }
.seg label:has(input:checked) { background: rgba(34,197,94,.14) !important; color: var(--neon) !important; font-weight: 600 !important; }

/* dropzone visible — TOUT en sombre (plus aucun fond clair Gradio) */
.dropzone { border: 1.5px dashed var(--border-strong) !important; border-radius: 12px !important; }
.dropzone, .dropzone *,
.dropzone [class*="upload"], .dropzone [data-testid], .dropzone .wrap,
.dropzone [class*="file"], .dropzone table, .dropzone tr, .dropzone td {
  background-color: var(--surface) !important; color: var(--text) !important;
}
.dropzone svg { background: transparent !important; color: var(--accent) !important; }
.dropzone .download, .dropzone a { color: var(--accent) !important; background: transparent !important; }

/* gr.Number + conteneurs de groupe de la sidebar : fond sombre, aucun blanc */
.side input, .side input[type="number"], .side [data-testid="number-input"] {
  background: var(--bg-2) !important; color: var(--text) !important;
  border: 1px solid var(--border) !important; border-radius: 10px !important;
}
.side .block, .side .form, .side .wrap, .side .group, .side fieldset {
  background: transparent !important; border: none !important;
}

/* boutons sobres : contour vert sur fond sombre (accent, pas aplat dominant) */
.btn-green button, button.btn-green {
  background: transparent !important; color: var(--accent) !important;
  border: 1px solid var(--accent) !important;
  border-radius: 9px !important; font-weight: 500 !important; font-size: 12.5px !important;
  min-height: 30px !important; height: auto !important; padding: 6px 12px !important;
  width: 100% !important; transition: background var(--t) !important;
}
.btn-green button:hover { background: rgba(34,197,94,.12) !important; }
.status, .status * { color: var(--text-bright) !important; font-family: var(--mono); font-size: 12px; }

.badges { display:flex; flex-direction:column; gap:6px; margin-top: 6px; }
.cfg { font-family: var(--mono); font-size: 11px; color: var(--text-dim); border:1px solid var(--border); border-radius:999px; padding:4px 10px; }
.cfg .g { color: var(--neon); }

/* ===== Zone principale ===== */
.maincol { padding: 0 !important; }
.thread { padding: 28px 30px; display:flex; flex-direction:column; gap: 28px; overflow-y:auto; max-height: calc(100vh - 96px); }
.empty { color: var(--text-dim); text-align:center; margin: 14vh auto; max-width: 420px; font-size: 15px; }
.turn { display:flex; flex-direction:column; gap:12px; max-width: 760px; width:100%; margin:0 auto; }
.you { align-self:flex-end; max-width:80%; background:var(--surface); border:1px solid var(--border);
  border-radius:14px 14px 4px 14px; padding:11px 15px; font-size:14.5px; color:var(--text-bright); }
.answer .alabel { display:flex; align-items:center; gap:8px; font-family:var(--mono); font-size:11px;
  text-transform:uppercase; letter-spacing:.04em; color:var(--accent); margin-bottom:8px; }
.answer .alabel .dot { width:7px; height:7px; border-radius:50%; background:var(--accent); box-shadow:0 0 8px var(--accent); }
.answer > p { font-size:15.5px; line-height:1.6; color:var(--text-bright); margin:0; }
.answer .miss { color: var(--text-dim); font-style: italic; }
.answer b { color: var(--neon); font-weight: 600; }

/* volets repliables */
.dd { margin-top:10px; border:1px solid var(--border); border-radius:8px; padding:9px 12px; background:rgba(255,255,255,.015); }
.dd summary { cursor:pointer; font-family:var(--mono); font-size:12px; color:var(--text-dim); list-style:none; }
.dd summary::-webkit-details-marker { display:none; }
.dd summary::marker { content:""; }
.dd[open] summary { margin-bottom: 8px; }
.src-dd summary { color: var(--neon); }
.norag p, .expect p { font-size:13.5px; color:var(--text-dim); font-style:italic; line-height:1.5; margin:0; }
.src-card { background:var(--bg-2); border:1px solid var(--border); border-radius:8px; padding:10px 12px; margin-bottom:8px; }
.src-card:last-child { margin-bottom:0; }
.src-h { display:flex; justify-content:space-between; font-family:var(--mono); font-size:11.5px; margin-bottom:3px; }
.src-h .src-n { color:var(--accent); font-weight:600; }
.src-h .src-d { color:var(--text-dim); }
.src-e { color:var(--text-dim); font-size:12.5px; line-height:1.45; }

/* ===== Composer ===== */
.composer { border-top:1px solid var(--border) !important; padding: 14px 30px 18px !important;
  background: var(--bg) !important; gap: 10px !important; align-items: center !important; }
.composer .field textarea, .composer .field input {
  background: var(--bg-2) !important; border:1px solid var(--border) !important; border-radius:12px !important;
  color: var(--text) !important; font-size:14.5px !important; padding: 12px 15px !important; }
.composer .field textarea:focus { border-color: var(--accent) !important; }
.send button, button.send {
  background: var(--amber) !important; color:#1A1205 !important; border:none !important;
  border-radius:12px !important; font-weight:700 !important; font-size:18px !important;
  min-width:48px !important; min-height:48px !important; }
.send button:hover { background: var(--amber-l) !important; }
"""


# ----------------------------------------------------------------------------
# Construction de l'UI (format chat)
# ----------------------------------------------------------------------------
def build_ui():
    with gr.Blocks(title="RAG explicable") as demo:
        history = gr.State([])           # tours de conversation
        dataset_state = gr.State([])     # lignes dataset chargees
        pending_expected = gr.State("")  # reponse attendue de la question tiree

        with gr.Row(elem_id="layout"):
            # ===================== Barre laterale =====================
            with gr.Column(scale=0, min_width=290, elem_classes="side"):
                gr.HTML('<div class="brand"><span class="mono">~/</span>RAG <span class="hl">explicable</span></div>')
                gr.HTML('<h4>// source</h4>')
                mode = gr.Radio(
                    ["Mes fichiers", "Dataset"],
                    value="Mes fichiers",
                    show_label=False,
                    elem_classes="seg",
                )

                with gr.Group(visible=True) as files_group:
                    f_file = gr.File(
                        file_count="multiple",
                        file_types=[".md", ".txt"],
                        label="Glisse-dépose tes .md / .txt",
                        elem_classes="dropzone",
                    )
                    f_ingest = gr.Button("Ingérer", elem_classes="btn-green")
                    f_status = gr.Markdown(elem_classes="status")

                with gr.Group(visible=False) as dataset_group:
                    d_n = gr.Number(value=100, precision=0, label="Nombre de lignes (N)")
                    d_load = gr.Button("Charger N lignes", elem_classes="btn-green")
                    d_status = gr.Markdown(elem_classes="status")
                    d_draw = gr.Button("Tirer une question", elem_classes="btn-green")

                gr.HTML(
                    '<div class="badges">'
                    '<span class="cfg"><span class="g">●</span> local</span>'
                    f'<span class="cfg">Ollama · {config.GEN_MODEL}</span>'
                    f'<span class="cfg">bge-m3 · {config.EMBED_DIM}d</span>'
                    f'<span class="cfg">pgvector(' + str(config.EMBED_DIM) + ")</span>"
                    "</div>"
                )

            # ===================== Zone principale =====================
            with gr.Column(scale=1, elem_classes="maincol"):
                thread = gr.HTML(render_thread([]))
                with gr.Row(elem_classes="composer"):
                    composer = gr.Textbox(
                        show_label=False,
                        placeholder="Écris ta question…",
                        elem_classes="field",
                        scale=1,
                        container=False,
                    )
                    send = gr.Button("↑", elem_classes="send", scale=0)

        # ---- Bascule de source (sidebar) ----
        def switch(m):
            files = m == "Mes fichiers"
            return gr.update(visible=files), gr.update(visible=not files)

        mode.change(switch, inputs=mode, outputs=[files_group, dataset_group])

        # ---- Ingestion / dataset (feedback immediat puis traitement) ----
        f_ingest.click(lambda: "⏳ ingestion…", outputs=f_status).then(
            handle_upload, inputs=f_file, outputs=f_status
        )
        d_load.click(lambda: "⏳ chargement…", outputs=d_status).then(
            handle_load_dataset, inputs=d_n, outputs=[d_status, dataset_state]
        )
        d_draw.click(
            handle_draw_question, inputs=dataset_state, outputs=[composer, pending_expected]
        )

        # ---- Envoi d'une question (generateur : 'en cours' puis reponse) ----
        ask_io = dict(
            fn=handle_ask,
            inputs=[composer, history, pending_expected],
            outputs=[history, thread, composer, pending_expected],
        )
        send.click(**ask_io)
        composer.submit(**ask_io)

    return demo


def make_server():
    """Serveur unique : page d'accueil a '/', app Gradio (RAG) montee sous '/app'."""
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    site_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")

    web = FastAPI()
    web = gr.mount_gradio_app(web, build_ui(), path="/app", theme=THEME, css=CSS)
    web.mount("/", StaticFiles(directory=site_dir, html=True), name="site")
    return web


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(make_server(), host="127.0.0.1", port=7860)
