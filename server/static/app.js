const state = {
  selections: [],
  comments: [],
  images: [],
  activeTarget: null,
  pickerOn: false,
  pinCounter: 0,
  drawerOpen: false,
};

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderSelections() {
  const container = byId("selected-options");
  if (!container) return;
  if (state.selections.length === 0) {
    container.innerHTML = '<p class="muted">No options selected yet.</p>';
  } else {
    container.innerHTML = state.selections
      .map(
        (item) =>
          `<div class="list-chip">${escapeHtml(item.label)} <button type="button" data-remove-selection="${escapeHtml(item.option_id)}">Remove</button></div>`
      )
      .join("");
  }
  document.querySelectorAll(".option-button").forEach((btn) => {
    const selected = state.selections.some((item) => item.option_id === btn.dataset.optionId);
    btn.dataset.selected = String(selected);
  });
  updateDrawerCounter();
}

function renderComments() {
  const container = byId("comment-list");
  if (!container) return;
  if (state.comments.length === 0) {
    container.innerHTML = '<p class="muted">No comments added yet.</p>';
  } else {
    container.innerHTML = state.comments
      .map((item, index) => {
        const targetChip = item.target
          ? `<span class="target-chip" title="${escapeHtml(item.target.selector)}">📍 ${escapeHtml(
              item.target.tag || "element"
            )}${item.target.snippet ? ` · ${escapeHtml(truncate(item.target.snippet, 60))}` : ""}</span>`
          : "";
        const scope = item.section_id ? escapeHtml(item.section_id) : "general";
        return `<div class="list-card"><div class="row-between" style="width:100%"><strong>${scope}</strong><button type="button" data-remove-comment="${index}">Remove</button></div>${targetChip}<p>${escapeHtml(item.text)}</p></div>`;
      })
      .join("");
  }
  updateDrawerCounter();
}

function renderImages() {
  const container = byId("image-list");
  if (!container) return;
  if (state.images.length === 0) {
    container.innerHTML = '<p class="muted">No references attached yet.</p>';
  } else {
    container.innerHTML = state.images
      .map(
        (item, index) =>
          `<div class="list-card"><div class="row-between" style="width:100%"><strong>${escapeHtml(item.name || item.url || "image")}</strong><button type="button" data-remove-image="${index}">Remove</button></div><p class="muted">${escapeHtml(item.source_type)}</p></div>`
      )
      .join("");
  }
  updateDrawerCounter();
}

function updateDrawerCounter() {
  const counter = byId("drawer-counter");
  if (!counter) return;
  const count = state.selections.length + state.comments.length + state.images.length;
  counter.textContent = String(count);
  counter.hidden = count === 0;
}

function truncate(value, max) {
  const str = String(value ?? "");
  return str.length > max ? `${str.slice(0, max - 1)}…` : str;
}

function renderActiveTarget() {
  const box = byId("active-target");
  if (!box) return;
  if (!state.activeTarget) {
    box.hidden = true;
    box.querySelector(".active-target-text").textContent = "";
    return;
  }
  box.hidden = false;
  const label =
    state.activeTarget.snippet?.trim() ||
    `${state.activeTarget.tag}${state.activeTarget.selector ? ` · ${state.activeTarget.selector}` : ""}`;
  box.querySelector(".active-target-text").textContent = truncate(label, 80);
}

function addSelection(button) {
  const optionId = button.dataset.optionId;
  const label = button.dataset.optionLabel;
  const existingIndex = state.selections.findIndex((item) => item.option_id === optionId);
  if (existingIndex >= 0) {
    state.selections.splice(existingIndex, 1);
  } else {
    state.selections.push({ option_id: optionId, label });
  }
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

/* ---------- questions ---------- */

function focusQuestion(button) {
  const index = button.dataset.questionIndex;
  const text = button.textContent.trim();
  const textarea = byId("comment-text");
  const select = byId("comment-section");
  toggleDrawer(true);
  if (select && select.value === "" && select.options.length > 1) {
    // leave current scope alone
  }
  if (textarea instanceof HTMLTextAreaElement) {
    textarea.dataset.questionIndex = index;
    textarea.placeholder = `Answer: ${text}`;
    textarea.focus({ preventScroll: false });
  }
}

function markQuestionAnswered(index) {
  const button = document.querySelector(`[data-question-index="${index}"]`);
  if (button) button.dataset.answered = "true";
}

/* ---------- drawer ---------- */

function toggleDrawer(open) {
  const drawer = byId("feedback-drawer");
  const scrim = byId("drawer-scrim");
  const fab = byId("drawer-toggle");
  if (!drawer || !scrim || !fab) return;
  const next = typeof open === "boolean" ? open : !state.drawerOpen;
  state.drawerOpen = next;
  drawer.classList.toggle("open", next);
  drawer.setAttribute("aria-hidden", String(!next));
  scrim.hidden = !next;
  requestAnimationFrame(() => scrim.classList.toggle("visible", next));
  fab.setAttribute("aria-expanded", String(next));
  if (next) {
    const textarea = byId("comment-text");
    if (textarea) textarea.focus({ preventScroll: true });
  }
}

/* ---------- element picker ---------- */

const pickerRoot = () => document.querySelector("[data-picker-root]");
const pickerOverlay = () => byId("picker-overlay");

function togglePicker(on) {
  const next = typeof on === "boolean" ? on : !state.pickerOn;
  state.pickerOn = next;
  document.body.classList.toggle("picker-active", next);
  const toggle = byId("picker-toggle");
  if (toggle) toggle.setAttribute("aria-pressed", String(next));
  if (!next) {
    hideOverlay();
  }
}

function hideOverlay() {
  const overlay = pickerOverlay();
  if (overlay) overlay.classList.remove("visible");
}

function positionOverlay(target) {
  const overlay = pickerOverlay();
  const root = pickerRoot();
  if (!overlay || !root) return;
  const targetRect = target.getBoundingClientRect();
  const rootRect = root.parentElement.getBoundingClientRect();
  overlay.style.left = `${targetRect.left - rootRect.left}px`;
  overlay.style.top = `${targetRect.top - rootRect.top}px`;
  overlay.style.width = `${targetRect.width}px`;
  overlay.style.height = `${targetRect.height}px`;
  overlay.classList.add("visible");
}

function describeTarget(element) {
  const root = pickerRoot();
  if (!root || !element || element === root) return null;
  const tag = element.tagName.toLowerCase();
  const text = (element.innerText || element.textContent || "").trim();
  const snippet = truncate(text.replace(/\s+/g, " "), 140);

  const path = [];
  let node = element;
  while (node && node !== root && path.length < 8) {
    const parent = node.parentElement;
    if (!parent) break;
    const siblings = Array.from(parent.children).filter(
      (sibling) => sibling.tagName === node.tagName
    );
    const index = siblings.indexOf(node) + 1;
    let part = node.tagName.toLowerCase();
    if (node.id) {
      part = `${part}#${node.id}`;
    } else if (siblings.length > 1) {
      part = `${part}:nth-of-type(${index})`;
    }
    path.unshift(part);
    if (node.id) break;
    node = parent;
  }
  const selector = path.join(" > ") || tag;

  let sectionId = null;
  let walker = element;
  while (walker && walker !== root) {
    if (walker.id) {
      sectionId = walker.id;
      break;
    }
    walker = walker.parentElement;
  }

  return { selector, tag, snippet, path: selector, section_id: sectionId };
}

function pinTarget(element) {
  const descriptor = describeTarget(element);
  if (!descriptor) return;
  state.activeTarget = descriptor;
  if (descriptor.section_id) {
    const select = byId("comment-section");
    if (select && Array.from(select.options).some((opt) => opt.value === descriptor.section_id)) {
      select.value = descriptor.section_id;
    }
  }
  renderActiveTarget();
  togglePicker(false);
  toggleDrawer(true);
  const textarea = byId("comment-text");
  if (textarea) textarea.focus({ preventScroll: false });
}

function wirePicker() {
  const root = pickerRoot();
  const overlay = pickerOverlay();
  if (!root || !overlay) return;

  root.addEventListener("mousemove", (event) => {
    if (!state.pickerOn) return;
    const target = event.target;
    if (!(target instanceof HTMLElement) || target === root) {
      hideOverlay();
      return;
    }
    positionOverlay(target);
  });

  root.addEventListener("mouseleave", () => {
    if (state.pickerOn) hideOverlay();
  });

  root.addEventListener(
    "click",
    (event) => {
      if (!state.pickerOn) return;
      const target = event.target;
      if (!(target instanceof HTMLElement) || target === root) return;
      event.preventDefault();
      event.stopPropagation();
      pinTarget(target);
    },
    true
  );

  window.addEventListener("scroll", hideOverlay, true);
  window.addEventListener("resize", hideOverlay);
}

/* ---------- submit ---------- */

async function submitSession() {
  const shell = document.querySelector("[data-session-id]");
  const feedback = byId("submit-feedback");
  const button = byId("submit-session");
  if (!shell || !feedback || !button) return;
  button.disabled = true;
  feedback.textContent = "Submitting…";
  try {
    const response = await fetch(`/api/sessions/${shell.dataset.sessionId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        selections: state.selections,
        comments: state.comments.map(({ section_id, text, target, question_index }) => ({
          section_id,
          text,
          target: target
            ? {
                selector: target.selector,
                tag: target.tag,
                snippet: target.snippet,
                path: target.path,
              }
            : undefined,
          question_index,
        })),
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
    if (status) {
      status.textContent = payload.status;
      status.dataset.status = payload.status;
    }
  } catch (error) {
    feedback.textContent = error instanceof Error ? error.message : "Submit failed";
  } finally {
    button.disabled = false;
  }
}

/* ---------- wiring ---------- */

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;

  const actionable = target.closest("[data-remove-selection], [data-remove-comment], [data-remove-image], [data-question-index], .option-button, #add-comment, #add-image-url, #submit-session, #picker-toggle, #clear-target, #drawer-toggle, #drawer-close, #drawer-scrim");
  if (!actionable) return;

  if (actionable.matches("[data-question-index]")) {
    focusQuestion(actionable);
    return;
  }

  if (actionable.matches(".option-button")) {
    addSelection(actionable);
    return;
  }
  if (actionable.id === "drawer-toggle") {
    toggleDrawer(true);
    return;
  }
  if (actionable.id === "drawer-close" || actionable.id === "drawer-scrim") {
    toggleDrawer(false);
    return;
  }
  if (actionable.id === "picker-toggle") {
    togglePicker();
    return;
  }
  if (actionable.id === "clear-target") {
    state.activeTarget = null;
    renderActiveTarget();
    return;
  }
  if (actionable.dataset.removeSelection) {
    state.selections = state.selections.filter(
      (item) => item.option_id !== actionable.dataset.removeSelection
    );
    renderSelections();
    return;
  }
  if (actionable.id === "add-comment") {
    const commentText = byId("comment-text");
    const sectionSelect = byId("comment-section");
    if (commentText instanceof HTMLTextAreaElement && sectionSelect instanceof HTMLSelectElement) {
      const text = commentText.value.trim();
      if (!text) return;
      const entry = {
        section_id: sectionSelect.value || state.activeTarget?.section_id || null,
        text,
      };
      if (state.activeTarget) {
        entry.target = { ...state.activeTarget };
      }
      const questionIndex = commentText.dataset.questionIndex;
      if (questionIndex !== undefined) {
        entry.question_index = Number(questionIndex);
        markQuestionAnswered(questionIndex);
        delete commentText.dataset.questionIndex;
        commentText.placeholder = "Add a note, constraint, or question…";
      }
      state.comments.push(entry);
      commentText.value = "";
      state.activeTarget = null;
      renderActiveTarget();
      renderComments();
    }
    return;
  }
  if (actionable.dataset.removeComment) {
    removeByIndex(state.comments, Number(actionable.dataset.removeComment));
    renderComments();
    return;
  }
  if (actionable.id === "add-image-url") {
    const imageUrl = byId("image-url");
    if (imageUrl instanceof HTMLInputElement) {
      const url = imageUrl.value.trim();
      if (!url) return;
      state.images.push({ source_type: "url", url, name: url });
      imageUrl.value = "";
      renderImages();
    }
    return;
  }
  if (actionable.dataset.removeImage) {
    removeByIndex(state.images, Number(actionable.dataset.removeImage));
    renderImages();
    return;
  }
  if (actionable.id === "submit-session") {
    submitSession();
    return;
  }
});

document.addEventListener("change", (event) => {
  const target = event.target;
  if (target instanceof HTMLInputElement && target.id === "image-file") {
    addSelectedFile();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (state.pickerOn) {
      togglePicker(false);
      return;
    }
    if (state.drawerOpen) {
      toggleDrawer(false);
      return;
    }
  }
  const tag = (event.target instanceof HTMLElement ? event.target.tagName : "").toLowerCase();
  const isTyping = tag === "input" || tag === "textarea" || tag === "select";
  if (isTyping) return;
  if (event.key === "p" || event.key === "P") {
    event.preventDefault();
    togglePicker();
  } else if (event.key === "f" || event.key === "F") {
    event.preventDefault();
    toggleDrawer();
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

wirePicker();
renderSelections();
renderComments();
renderImages();
renderActiveTarget();
