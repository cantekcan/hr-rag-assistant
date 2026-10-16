// Chat page for the HR assistant. Plain JavaScript, no build step.
// All text from the server is inserted with textContent, never as HTML.

const EXAMPLES = [
  "5 yıldır çalışıyorum, kaç gün yıllık izin hakkım var?",
  "Karım doğum yaptı, ikimiz ne kadar izin alabiliriz?",
  "Deneme süresi ne kadar?",
  "Yemek kartına ne kadar yükleniyor?",
];
const SIGNED_IN_EXAMPLE = "Bu yıl kaç gün yıllık iznim kaldı?";

const ERROR_MESSAGES = {
  429: "Kısa sürede çok fazla soru soruldu. Lütfen biraz sonra tekrar deneyin.",
  503: "Dil modeline şu an ulaşılamıyor. Birkaç dakika sonra tekrar deneyin.",
  404: "Seçilen çalışan bulunamadı. Sayfayı yenileyip tekrar seçin.",
  422: "Soru boş olamaz ve en fazla 1000 karakter olabilir.",
};

const els = {
  employee: document.getElementById("employee"),
  banner: document.getElementById("banner"),
  messages: document.getElementById("messages"),
  welcome: document.getElementById("welcome"),
  examples: document.getElementById("examples"),
  form: document.getElementById("composer"),
  question: document.getElementById("question"),
  send: document.getElementById("send"),
  source: document.getElementById("source"),
  sourceNumber: document.getElementById("source-number"),
  sourcePath: document.getElementById("source-path"),
  sourceText: document.getElementById("source-text"),
  sourcePage: document.getElementById("source-page"),
  sourceClose: document.getElementById("source-close"),
  sourceOpen: document.getElementById("source-open"),
  openDocument: document.getElementById("open-document"),
  viewer: document.getElementById("viewer"),
  viewerFrame: document.getElementById("viewer-frame"),
  viewerNewTab: document.getElementById("viewer-new-tab"),
  viewerClose: document.getElementById("viewer-close"),
};

// Phones open the PDF in a new tab: most mobile browsers cannot show a PDF inside a page
const WIDE_SCREEN = window.matchMedia("(min-width: 761px)");

let employees = [];
let activeChip = null;
let activePage = null;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function scrollToEnd() {
  els.messages.scrollTop = els.messages.scrollHeight;
}

function addToChat(node) {
  els.welcome.hidden = true;
  els.messages.appendChild(node);
  scrollToEnd();
  return node;
}

// ---------- Startup ----------

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (response.status === 503) {
      showBanner("Yönetmelik henüz yüklenmemiş. Önce şu komutu çalıştırın: python -m hr_assistant.ingest");
    }
  } catch {
    showBanner("Sunucuya ulaşılamıyor. API'nin çalıştığından emin olun.");
  }
}

function showBanner(text) {
  els.banner.textContent = text;
  els.banner.hidden = false;
}

async function loadEmployees() {
  try {
    const response = await fetch("/employees");
    if (!response.ok) return;
    employees = await response.json();
    for (const e of employees) {
      const option = el("option", "", `${e.name} (${e.department})`);
      option.value = e.id;
      els.employee.appendChild(option);
    }
  } catch {
    // The chat still works without signing in
  }
}

function renderExamples() {
  const list = els.employee.value ? [SIGNED_IN_EXAMPLE, ...EXAMPLES] : EXAMPLES;
  els.examples.replaceChildren(...list.map((text) => {
    const item = el("li");
    const button = el("button", "", text);
    button.type = "button";
    button.addEventListener("click", () => ask(text));
    item.appendChild(button);
    return item;
  }));
}

// ---------- Asking ----------

let busy = false;

async function ask(question) {
  question = question.trim();
  if (!question || busy) return;  // one question at a time, also for the example buttons

  const user = el("div", "msg msg-user");
  user.appendChild(el("p", "", question));
  addToChat(user);

  const pending = addToChat(el("div", "msg msg-bot"));
  pending.appendChild(el("p", "answer thinking", "Yönetmelik taranıyor"));
  setBusy(true);

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, employee_id: els.employee.value || null }),
    });
    if (!response.ok) {
      renderError(pending, ERROR_MESSAGES[response.status] || `Beklenmeyen bir hata oluştu (${response.status}).`);
    } else {
      renderAnswer(pending, await response.json());
    }
  } catch {
    renderError(pending, "Sunucuya ulaşılamadı. Bağlantınızı ve API'nin çalıştığını kontrol edin.");
  } finally {
    setBusy(false);
    els.question.focus();
  }
}

function setBusy(value) {
  busy = value;
  els.send.disabled = value;
  els.employee.disabled = value;  // the pending answer belongs to the employee it was asked as
  els.send.textContent = value ? "Yanıtlanıyor" : "Sor";
}

function renderError(container, text) {
  container.replaceChildren(el("p", "error", text));
  scrollToEnd();
}

function renderAnswer(container, data) {
  container.replaceChildren();
  container.classList.toggle("refused", data.refused);

  // The server appends the "not covered" sentence to the answer; here it is shown as a separate note
  const note = data.missing_info_note;
  const body = note && data.answer.endsWith(note) ? data.answer.slice(0, -note.length).trimEnd() : data.answer;
  container.appendChild(el("p", "answer", body));
  if (note) container.appendChild(el("p", "not-covered", note));

  // Every cited section gets a label; it opens the text only when the text is available
  if (data.sections.length) {
    const textBySection = new Map(data.sources.map((source) => [source.section, source]));
    const basis = el("div", "basis");
    basis.appendChild(el("span", "basis-label", "Dayanak:"));
    for (const section of data.sections) {
      const source = textBySection.get(section);
      if (source) {
        const chip = el("button", "chip", section);
        chip.type = "button";
        chip.setAttribute("aria-pressed", "false");
        chip.setAttribute("aria-label", `Madde ${section} metnini göster`);
        chip.addEventListener("click", () => openSource(source, chip));
        basis.appendChild(chip);
      } else {
        const label = el("span", "chip chip-static", section);
        label.title = "Bu maddenin metni şu an gösterilemiyor";
        basis.appendChild(label);
      }
    }
    container.appendChild(basis);
  }

  if (data.tools_used.length || data.model) {
    const trace = el("details", "trace");
    trace.appendChild(el("summary", "", "Yanıt nasıl hazırlandı"));
    const list = el("ul");
    for (const tool of data.tools_used) list.appendChild(el("li", "", describeTool(tool)));
    if (data.model) list.appendChild(el("li", "", `Yanıtı yazan model: ${data.model}`));
    trace.appendChild(list);
    container.appendChild(trace);
  }
  scrollToEnd();
}

function describeTool(tool) {
  if (tool.startsWith("search_regulation:")) {
    return `Yönetmelikte arandı: "${tool.slice("search_regulation:".length).trim()}"`;
  }
  if (tool === "get_my_leave_balance") return "İzin kaydınıza bakıldı";
  return tool;
}

// ---------- Cited section ----------

function openSource(source, chip) {
  if (activeChip) activeChip.setAttribute("aria-pressed", "false");
  activeChip = chip;
  chip.setAttribute("aria-pressed", "true");

  els.sourceNumber.textContent = source.section;
  els.sourcePath.textContent = source.path || "Yönetmeliğin ana maddesi";
  // The stored text starts with its own number ("5.7.4.2. ..."), which is already shown as the title
  const prefix = `${source.section}.`;
  els.sourceText.textContent = source.text.startsWith(prefix) ? source.text.slice(prefix.length).trimStart() : source.text;
  els.sourcePage.textContent = `Sayfa ${source.page}`;
  activePage = source.page;
  els.sourceOpen.href = documentUrl(source.page);
  els.source.hidden = false;
  els.source.scrollTop = 0;
  els.sourceClose.focus();
}

function closeSource() {
  els.source.hidden = true;
  if (activeChip) {
    activeChip.setAttribute("aria-pressed", "false");
    activeChip.focus();
    activeChip = null;
  }
}

// ---------- Regulation PDF ----------

function documentUrl(page) {
  // Browser PDF viewers jump to the page given after #page=
  return page ? `/document#page=${page}` : "/document";
}

function openDocument(event, page) {
  if (!WIDE_SCREEN.matches) return;  // let the link open a new tab
  event.preventDefault();
  const url = documentUrl(page);
  const frame = el("iframe");
  frame.title = "Yönetmelik PDF";
  frame.src = url;  // a new frame each time, so the viewer always jumps to the page
  els.viewerFrame.replaceChildren(frame);
  els.viewerNewTab.href = url;
  els.viewer.showModal();
}

// ---------- Events ----------

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy) return;
  const question = els.question.value;
  els.question.value = "";
  resizeInput();
  void ask(question);  // errors are handled inside ask
});

els.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    els.form.requestSubmit();
  }
});

function resizeInput() {
  els.question.style.height = "auto";
  els.question.style.height = `${els.question.scrollHeight}px`;
}
els.question.addEventListener("input", resizeInput);

els.employee.addEventListener("change", () => {
  renderExamples();
  if (!els.welcome.hidden) return;  // nothing asked yet, no need to announce
  const selected = employees.find((e) => e.id === els.employee.value);
  const text = selected ? `${selected.name} olarak soruyorsunuz.` : "Giriş yapmadan soruyorsunuz.";
  addToChat(el("p", "msg divider", text));
});

els.sourceClose.addEventListener("click", closeSource);
document.addEventListener("keydown", (event) => {
  // While the PDF is open, Escape belongs to the viewer; while typing, it belongs to the question box
  if (event.key !== "Escape" || els.viewer.open || els.source.hidden) return;
  if (event.target === els.question) return;
  closeSource();
});

els.openDocument.addEventListener("click", (event) => openDocument(event));
els.sourceOpen.addEventListener("click", (event) => openDocument(event, activePage));
els.viewerClose.addEventListener("click", () => els.viewer.close());
els.viewer.addEventListener("click", (event) => {
  if (event.target === els.viewer) els.viewer.close();  // click on the dimmed background
});
els.viewer.addEventListener("close", () => els.viewerFrame.replaceChildren());

renderExamples();
void checkHealth();    // both handle their own errors
void loadEmployees();
els.question.focus();
