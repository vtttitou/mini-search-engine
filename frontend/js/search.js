import { api } from "./api.js";
import { showError, state } from "./state.js";

const form = document.getElementById("search-form");
const resultsContainer = document.getElementById("results");
const statusElement = document.getElementById("status");
const methodSelect = document.getElementById("method");

const METHOD_LABELS = {
    bm25: "BM25",
    tfidf: "TF-IDF",
};

export async function loadMethods() {
    const { methods, default: defaultMethod } = await api.methods();

    for (const method of methods) {
        const option = document.createElement("option");
        option.value = method;
        option.textContent = METHOD_LABELS[method] || method;
        methodSelect.appendChild(option);
    }

    methodSelect.value = defaultMethod;
}

const escapeRegex = text => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function highlight(text, query) {
    const words = [...new Set(query.toLowerCase().match(/[a-z0-9]{2,}/g) || [])];
    const fragment = document.createDocumentFragment();

    if (words.length === 0) {
        fragment.append(text);
        return fragment;
    }

    const pattern = new RegExp(`(${words.map(escapeRegex).join("|")})`, "gi");
    text.split(pattern).forEach((part, index) => {
        if (index % 2 === 1) {
            const mark = document.createElement("mark");
            mark.textContent = part;
            fragment.appendChild(mark);
        } else {
            fragment.append(part);
        }
    });

    return fragment;
}

function createResultCard(hit, query) {
    const card = document.createElement("article");
    card.className = "card";

    const head = document.createElement("div");
    head.className = "card-head";

    const rank = document.createElement("span");
    rank.className = "rank";
    rank.textContent = hit.rank;

    const title = document.createElement("h3");
    title.textContent = hit.filename;

    const score = document.createElement("span");
    score.className = "score";
    score.textContent = `score ${hit.score.toFixed(3)}`;

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "small secondary";
    toggle.textContent = "Full text";

    head.append(rank, title, score, toggle);

    const snippet = document.createElement("p");
    snippet.appendChild(highlight(hit.snippet, query));

    card.append(head, snippet);

    let fullText = null;
    toggle.addEventListener("click", async () => {
        if (fullText) {
            fullText.remove();
            fullText = null;
            toggle.textContent = "Full text";
            return;
        }

        try {
            const doc = await api.getDocument(state.collectionId, hit.doc_id);
            fullText = document.createElement("pre");
            fullText.className = "fulltext";
            fullText.textContent = doc.text;
            card.appendChild(fullText);
            toggle.textContent = "Hide";
        } catch (error) {
            showError(error.message);
        }
    });

    return card;
}

export function initSearch() {
    document.addEventListener("collection-changed", () => {
        resultsContainer.replaceChildren();
        statusElement.textContent = "";
    });

    form.addEventListener("submit", async event => {
        event.preventDefault();

        const query = document.getElementById("query").value.trim();
        resultsContainer.replaceChildren();

        if (!state.collectionId) {
            statusElement.textContent = "Create a collection and upload documents first.";
            return;
        }
        if (!query) {
            statusElement.textContent = "Enter some search words.";
            return;
        }

        try {
            showError("");
            const k = document.getElementById("top-k").value;
            const response = await api.search(state.collectionId, query, methodSelect.value, k);

            let status = `${response.total_returned} result(s) with ${METHOD_LABELS[response.method]}. ` +
                `Ranking took ${response.search_ms.toFixed(2)} ms.`;
            if (response.index_build_ms !== null) {
                status += ` Index built first (${response.index_build_ms.toFixed(1)} ms).`;
            }
            statusElement.textContent = status;

            for (const hit of response.results) {
                resultsContainer.appendChild(createResultCard(hit, query));
            }
        } catch (error) {
            statusElement.textContent = "";
            showError(error.message);
        }
    });
}
