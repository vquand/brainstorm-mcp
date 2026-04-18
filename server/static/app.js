const state = {
  selections: [],
  comments: [],
  images: [],
};

function byId(id) {
  return document.getElementById(id);
}

function renderSelections() {
  const container = byId("selected-options");
  if (!container) return;
  if (state.selections.length === 0) {
    container.innerHTML = '<p class="muted">No options selected yet.</p>';
    return;
  }
  container.innerHTML = state.selections
    .map((item) => `<div class="list-chip">${escapeHtml(item.label)} <button type="button" data-remove-selection="${escapeHtml(item.option_id)}">Remove</button></div>`)
    .join("");
}

function renderComments() {
  const container = byId("comment-list");
  if (!container) return;
  if (state.comments.length === 0) {
    container.innerHTML = '<p class="muted">No comments added yet.</p>';
    return;
  }
  container.innerHTML = state.comments
    .map(
      (item, index) =>
        `<div class="list-card"><strong>${escapeHtml(item.section_id || "general")}</strong><p>${escapeHtml(item.text)}</p><button type="button" data-remove-comment="${index}">Remove</button></div>`
    )
    .join("");
}

function renderImages() {
  const container = byId("image-list");
  if (!container) return;
  if (state.images.length === 0) {
    container.innerHTML = '<p class="muted">No images attached yet.</p>';
    return;
  }
  container.innerHTML = state.images
    .map(
      (item, index) =>
        `<div class="list-card"><strong>${escapeHtml(item.name || item.url || "image")}</strong><p>${escapeHtml(item.source_type)}</p><button type="button" data-remove-image="${index}">Remove</button></div>`
    )
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function addSelection(button) {
  const optionId = button.dataset.optionId;
  const label = button.dataset.optionLabel;
  if (state.selections.some((item) => item.option_id === optionId)) {
    return;
  }
  state.selections.push({ option_id: optionId, label });
  renderSelections();
}

function removeByIndex(collection, index) {
  collection.splice(index, 1);
}

async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const [, data] = result.split(",", 2);
      resolve(data || "");
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

async function addSelectedFile() {
  const input = byId("image-file");
  const [file] = input.files || [];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    byId("submit-feedback").textContent = "Only image files are allowed.";
    input.value = "";
    return;
  }
  const dataBase64 = await fileToBase64(file);
  state.images.push({
    source_type: "upload",
    name: file.name,
    media_type: file.type || "application/octet-stream",
    data_base64: dataBase64,
  });
  input.value = "";
  renderImages();
}

async function submitSession() {
  const shell = document.querySelector("[data-session-id]");
  const feedback = byId("submit-feedback");
  const button = byId("submit-session");
  if (!shell || !feedback || !button) return;
  button.disabled = true;
  feedback.textContent = "Submitting...";
  try {
    const response = await fetch(`/api/sessions/${shell.dataset.sessionId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        selections: state.selections,
        comments: state.comments,
        images: state.images,
      }),
    });
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.detail || "Submit failed");
    }
    const payload = await response.json();
    feedback.textContent = `Submitted at ${payload.submitted_at || "unknown time"}.`;
    const status = byId("status-chip");
    if (status) status.textContent = payload.status;
  } catch (error) {
    feedback.textContent = error instanceof Error ? error.message : "Submit failed";
  } finally {
    button.disabled = false;
  }
}

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (target.matches(".option-button")) {
    addSelection(target);
  } else if (target.dataset.removeSelection) {
    state.selections = state.selections.filter((item) => item.option_id !== target.dataset.removeSelection);
    renderSelections();
  } else if (target.id === "add-comment") {
    const commentText = byId("comment-text");
    const sectionSelect = byId("comment-section");
    if (commentText instanceof HTMLTextAreaElement && sectionSelect instanceof HTMLSelectElement) {
      const text = commentText.value.trim();
      if (!text) return;
      state.comments.push({ section_id: sectionSelect.value || null, text });
      commentText.value = "";
      renderComments();
    }
  } else if (target.dataset.removeComment) {
    removeByIndex(state.comments, Number(target.dataset.removeComment));
    renderComments();
  } else if (target.id === "add-image-url") {
    const imageUrl = byId("image-url");
    if (imageUrl instanceof HTMLInputElement) {
      const url = imageUrl.value.trim();
      if (!url) return;
      state.images.push({ source_type: "url", url, name: url });
      imageUrl.value = "";
      renderImages();
    }
  } else if (target.dataset.removeImage) {
    removeByIndex(state.images, Number(target.dataset.removeImage));
    renderImages();
  } else if (target.id === "submit-session") {
    submitSession();
  }
});

document.addEventListener("change", (event) => {
  const target = event.target;
  if (target instanceof HTMLInputElement && target.id === "image-file") {
    addSelectedFile();
  }
});

document.addEventListener("paste", async (event) => {
  const items = event.clipboardData?.items || [];
  for (const item of items) {
    if (!item.type.startsWith("image/")) continue;
    const file = item.getAsFile();
    if (!file) continue;
    const dataBase64 = await fileToBase64(file);
    state.images.push({
      source_type: "clipboard",
      name: file.name || `clipboard-${Date.now()}.png`,
      media_type: file.type || "image/png",
      data_base64: dataBase64,
    });
    renderImages();
    break;
  }
});

if (window.location.search.includes("token=")) {
  window.history.replaceState({}, "", window.location.pathname);
}

renderSelections();
renderComments();
renderImages();
