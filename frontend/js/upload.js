import { api } from "./api.js";
import { emit, showError, state } from "./state.js";

const container = document.getElementById("documents");
const statusElement = document.getElementById("upload-status");
const fileInput = document.getElementById("file-input");

function formatSize(bytes) {
    return bytes < 1024 * 1024
        ? `${(bytes / 1024).toFixed(1)} KB`
        : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function createDocumentCard(doc) {
    const card = document.createElement("article");
    card.className = "card";

    const head = document.createElement("div");
    head.className = "card-head";

    const title = document.createElement("h3");
    title.textContent = doc.filename;

    const meta = document.createElement("span");
    meta.className = "score";
    meta.textContent = `${formatSize(doc.size_bytes)} · ${doc.num_chars.toLocaleString()} characters`;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "small danger";
    remove.textContent = "Delete";
    remove.addEventListener("click", async () => {
        try {
            showError("");
            await api.deleteDocument(state.collectionId, doc.id);
            emit("documents-changed");
        } catch (error) {
            showError(error.message);
        }
    });

    head.append(title, meta, remove);
    card.appendChild(head);

    return card;
}

export async function renderDocuments() {
    container.replaceChildren();

    if (!state.collectionId) {
        statusElement.textContent = "Create a collection first.";
        return;
    }

    const documents = await api.listDocuments(state.collectionId);
    statusElement.textContent = documents.length === 0 ? "No documents yet." : "";

    for (const doc of documents) {
        container.appendChild(createDocumentCard(doc));
    }
}

export function initUpload() {
    document.addEventListener("collection-changed", () => {
        renderDocuments().catch(error => showError(error.message));
    });

    document.getElementById("upload-form").addEventListener("submit", async event => {
        event.preventDefault();

        if (!state.collectionId || fileInput.files.length === 0) {
            statusElement.textContent = "Choose a collection and at least one file.";
            return;
        }

        statusElement.textContent = "Uploading…";

        try {
            showError("");
            const result = await api.upload(state.collectionId, fileInput.files);
            const skipped = result.failed.map(f => `${f.filename}: ${f.error}`);

            fileInput.value = "";
            emit("documents-changed");
            statusElement.textContent =
                `${result.uploaded.length} file(s) uploaded.` +
                (skipped.length ? ` Skipped — ${skipped.join("; ")}` : "");
        } catch (error) {
            statusElement.textContent = "";
            showError(error.message);
        }
    });
}
