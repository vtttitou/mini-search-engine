async function request(path, options = {}) {
    const response = await fetch(`/api${path}`, options);

    if (response.status === 204) {
        return null;
    }

    const body = await response.json().catch(() => null);

    if (!response.ok) {
        const message = body?.error?.message
            || (typeof body?.detail === "string" ? body.detail : null)
            || body?.failed?.map(f => f.error).join("; ")
            || `Request failed (${response.status})`;
        throw new Error(message);
    }

    return body;
}

const json = (method, data) => ({
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
});

export const api = {
    methods: () => request("/methods"),
    listCollections: () => request("/collections"),
    createCollection: name => request("/collections", json("POST", { name })),
    deleteCollection: id => request(`/collections/${id}`, { method: "DELETE" }),
    listDocuments: id => request(`/collections/${id}/documents`),
    getDocument: (id, docId) => request(`/collections/${id}/documents/${docId}`),
    deleteDocument: (id, docId) =>
        request(`/collections/${id}/documents/${docId}`, { method: "DELETE" }),
    upload: (id, files) => {
        const form = new FormData();
        for (const file of files) {
            form.append("files", file);
        }
        return request(`/collections/${id}/documents`, { method: "POST", body: form });
    },
    search: (id, q, method, k) => {
        const params = new URLSearchParams({ q, method, k });
        return request(`/collections/${id}/search?${params}`);
    },
};
