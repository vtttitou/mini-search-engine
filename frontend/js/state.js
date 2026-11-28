export const state = { collectionId: null };

export function emit(name) {
    document.dispatchEvent(new CustomEvent(name));
}

export function showError(message) {
    const banner = document.getElementById("banner");
    banner.textContent = message || "";
    banner.hidden = !message;
}
