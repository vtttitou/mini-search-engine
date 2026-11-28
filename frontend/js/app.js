import { loadCollections, initCollections } from "./collections.js";
import { loadMethods, initSearch } from "./search.js";
import { showError } from "./state.js";
import { initUpload } from "./upload.js";

initCollections();
initUpload();
initSearch();

try {
    await loadMethods();
    await loadCollections();
} catch (error) {
    showError(`Cannot reach the server: ${error.message}`);
}
