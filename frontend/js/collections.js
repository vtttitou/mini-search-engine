import { api } from "./api.js";
import { emit, showError, state } from "./state.js";

const select = document.getElementById("collection-select");
const deleteButton = document.getElementById("delete-collection");

export async function loadCollections(selectId = state.collectionId) {
    const collections = await api.listCollections();

    select.replaceChildren();

    for (const collection of collections) {
        const option = document.createElement("option");
        option.value = collection.id;
        option.textContent = `${collection.name} (${collection.document_count})`;
        select.appendChild(option);
    }

    const stillExists = collections.some(c => c.id === selectId);
    state.collectionId = stillExists ? selectId : (collections[0]?.id ?? null);
    select.value = state.collectionId ?? "";
    select.disabled = deleteButton.disabled = collections.length === 0;

    emit("collection-changed");
}

export function initCollections() {
    select.addEventListener("change", () => {
        state.collectionId = select.value;
        emit("collection-changed");
    });

    document.getElementById("new-collection-form").addEventListener("submit", async event => {
        event.preventDefault();
        const input = document.getElementById("new-collection-name");

        try {
            showError("");
            const created = await api.createCollection(input.value);
            input.value = "";
            await loadCollections(created.id);
        } catch (error) {
            showError(error.message);
        }
    });

    deleteButton.addEventListener("click", async () => {
        if (!state.collectionId || !confirm("Delete this collection and all its documents?")) {
            return;
        }

        try {
            showError("");
            await api.deleteCollection(state.collectionId);
            await loadCollections(null);
        } catch (error) {
            showError(error.message);
        }
    });

    document.addEventListener("documents-changed", () => loadCollections());
}
