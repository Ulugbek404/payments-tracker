"use strict";

const CURRENCY = "сум";
const MIN_MONTH = "2000-01";

const $ = (id) => document.getElementById(id);
const fmt = (n) => new Intl.NumberFormat("ru-RU").format(n);
const todayISO = () => new Date().toLocaleDateString("sv-SE"); // local date as YYYY-MM-DD
const currentMonth = () => todayISO().slice(0, 7);

const state = {
  month: currentMonth(),
  studentCount: null, // null until the student list has loaded
};

// ---------- DOM helpers ----------

// Build DOM with textContent only: names and phones come from users, never use innerHTML for them.
function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

// Icon paths are constants defined here, so setting innerHTML with them is safe.
const ICONS = {
  "check-circle": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16.5v.01"/>',
  "user-plus": '<circle cx="9" cy="8" r="4"/><path d="M2 20a7 7 0 0 1 14 0M19 8v6M16 11h6"/>',
};

function icon(name, size = 20) {
  const span = el("span", { className: "icon" });
  span.setAttribute("aria-hidden", "true");
  span.innerHTML =
    `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" ` +
    `stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[name]}</svg>`;
  return span;
}

// ---------- Theme ----------

const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
const themeToggle = $("theme-toggle");

// An explicit choice lives in <html data-theme>; without one the system preference decides.
const effectiveTheme = () => document.documentElement.dataset.theme || (darkQuery.matches ? "dark" : "light");

function syncThemeUI() {
  const dark = effectiveTheme() === "dark";
  const label = dark ? "Включить светлую тему" : "Включить тёмную тему";
  themeToggle.classList.toggle("is-dark", dark);
  themeToggle.setAttribute("aria-label", label);
  themeToggle.title = label;
  const bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
  document.querySelector('meta[name="theme-color"]').content = bg;
}

themeToggle.addEventListener("click", () => {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try {
    localStorage.setItem("theme", next);
  } catch { /* storage unavailable: the choice just won't persist */ }
  syncThemeUI();
});

darkQuery.addEventListener("change", syncThemeUI);

// ---------- API ----------

async function api(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!res.ok) {
    let message = `Ошибка ${res.status}`;
    try {
      const { detail } = await res.json();
      message = Array.isArray(detail)
        ? detail.map((d) => `${d.loc.slice(1).join(".")}: ${d.msg}`).join("; ")
        : detail || message;
    } catch { /* response had no JSON body */ }
    throw new Error(message);
  }
  return res.status === 204 ? null : res.json();
}

// ---------- Toast ----------

let msgTimer;
function flash(text, isError = false) {
  const msg = $("msg");
  msg.replaceChildren(icon(isError ? "alert" : "check-circle"), el("span", { textContent: text }));
  msg.className = isError ? "err" : "";
  msg.setAttribute("role", isError ? "alert" : "status");
  msg.hidden = false;
  clearTimeout(msgTimer);
  msgTimer = setTimeout(() => (msg.hidden = true), isError ? 7000 : 4000);
}

// ---------- Month stepper ----------

function shiftMonth(ym, delta) {
  const [year, month] = ym.split("-").map(Number);
  const d = new Date(year, month - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(ym) {
  const [year, month] = ym.split("-").map(Number);
  const text = new Date(year, month - 1, 1)
    .toLocaleDateString("ru-RU", { month: "long", year: "numeric" })
    .replace(/\s*г\.$/, "");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function syncMonthUI() {
  $("month-label").textContent = monthLabel(state.month);
  $("month-prev").disabled = state.month <= MIN_MONTH;
  $("month-next").disabled = state.month >= currentMonth(); // debts for future months make no sense
}

function setMonth(ym) {
  state.month = ym;
  syncMonthUI();
  loadDebtors();
}

$("month-prev").addEventListener("click", () => setMonth(shiftMonth(state.month, -1)));
$("month-next").addEventListener("click", () => setMonth(shiftMonth(state.month, 1)));

// ---------- Debtors ----------

const initials = (name) =>
  name.trim().split(/\s+/).slice(0, 2).map((word) => Array.from(word)[0] ?? "").join("").toUpperCase();

// Stable colour per name, so the same student always gets the same avatar.
function hueOf(name) {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.codePointAt(0)) % 360;
  return h;
}

function debtorCard(d) {
  // floor, not round: 99.6% paid must not read as 100% while a debt remains
  const percent = Math.min(100, Math.floor((d.paid / d.monthly_fee) * 100));
  const avatar = el("span", { className: "avatar", textContent: initials(d.name) });
  avatar.style.setProperty("--hue", hueOf(d.name));
  avatar.setAttribute("aria-hidden", "true");

  const phone = el("a", { className: "phone", href: "tel:" + d.phone.replace(/[^\d+]/g, ""), textContent: d.phone });
  const progress = el("div", { className: "progress" }, el("span", { className: "progress-fill" }));
  progress.firstChild.style.width = `${percent}%`;
  progress.setAttribute("role", "progressbar");
  progress.setAttribute("aria-label", "Оплачено");
  progress.setAttribute("aria-valuemin", "0");
  progress.setAttribute("aria-valuemax", "100");
  progress.setAttribute("aria-valuenow", String(percent));

  const payButton = el("button", {
    type: "button",
    className: "btn btn-secondary btn-sm",
    textContent: "Принять оплату",
    onclick: () => prefillPayment(d),
  });
  payButton.setAttribute("aria-label", `Принять оплату: ${d.name}`);

  return el("li", { className: "debtor" },
    el("div", { className: "debtor-top" },
      avatar,
      el("div", { className: "debtor-info" },
        el("div", { className: "debtor-name", textContent: d.name }),
        el("div", { className: "debtor-meta" }, el("span", { className: "chip", textContent: d.group }), phone)),
      el("div", { className: "debt-amount" },
        el("strong", { textContent: fmt(d.debt) }),
        el("span", { textContent: `${CURRENCY} долг` }))),
    progress,
    el("div", { className: "debtor-foot" },
      el("span", { className: "paid-text", textContent: `Оплачено ${fmt(d.paid)} из ${fmt(d.monthly_fee)} ${CURRENCY} · ${percent}%` }),
      payButton));
}

function showEmpty({ tone, iconName, title, text, action }) {
  const box = $("empty");
  box.className = `empty is-${tone}`;
  box.replaceChildren(
    el("div", { className: "empty-icon" }, icon(iconName, 28)),
    el("h3", { textContent: title }),
    el("p", { textContent: text }),
    ...(action ? [el("button", { type: "button", className: "btn btn-secondary", textContent: action.label, onclick: action.run })] : []));
  box.hidden = false;
}

function setStats(count, total) {
  $("stat-count").textContent = count === null ? "—" : String(count);
  const totalNode = $("stat-total");
  totalNode.replaceChildren(
    ...(total === null ? ["—"] : [el("span", { className: "num", textContent: fmt(total) }), " ", el("small", { textContent: CURRENCY })]));
  $("stats").classList.toggle("is-clear", count === 0);
  $("stats").classList.toggle("is-pending", count === null);
}

function renderDebtors(data) {
  const label = monthLabel(data.month);
  setStats(data.count, data.total_debt);
  $("summary").textContent = data.count
    ? `${label}: должников ${data.count}, общий долг ${fmt(data.total_debt)} ${CURRENCY}`
    : `${label}: должников нет`;
  $("debtors").replaceChildren(...data.debtors.map(debtorCard));

  if (data.count) {
    $("empty").hidden = true;
  } else if (state.studentCount === 0) {
    showEmpty({
      tone: "neutral", iconName: "user-plus",
      title: "Пока нет учеников",
      text: "Добавьте первого ученика, чтобы вести учёт оплат.",
      action: { label: "Добавить ученика", run: openStudentForm },
    });
  } else {
    showEmpty({
      tone: "ok", iconName: "check-circle",
      title: "Все оплатили",
      text: `За ${label.toLowerCase()} должников нет.`,
    });
  }
}

function renderLoadError(err) {
  setStats(null, null);
  $("summary").textContent = "Не удалось загрузить список должников";
  $("debtors").replaceChildren();
  showEmpty({
    tone: "error", iconName: "alert",
    title: "Не удалось загрузить",
    text: err.message,
    action: { label: "Повторить", run: loadDebtors },
  });
}

let loadSeq = 0;
async function loadDebtors() {
  const seq = ++loadSeq; // a slower, older response must not overwrite a newer one
  const list = $("debtors");
  list.setAttribute("aria-busy", "true");
  list.classList.add("is-loading");
  if (!list.children.length) {
    $("empty").hidden = true;
    list.replaceChildren(...[1, 2, 3].map(() => el("li", { className: "skeleton" })));
  }
  try {
    const data = await api(`/debtors?month=${encodeURIComponent(state.month)}`);
    if (seq === loadSeq) renderDebtors(data);
  } catch (err) {
    if (seq === loadSeq) renderLoadError(err);
  } finally {
    if (seq === loadSeq) {
      list.removeAttribute("aria-busy");
      list.classList.remove("is-loading");
    }
  }
}

// ---------- Students ----------

async function loadStudents() {
  const select = $("pay-student");
  const previous = select.value;
  try {
    const students = await api("/students");
    state.studentCount = students.length;
    select.replaceChildren(
      ...(students.length
        ? students.map((s) => new Option(`${s.name} — ${s.group}`, s.id))
        : [new Option("Сначала добавьте ученика", "")]));
    if ([...select.options].some((option) => option.value === previous)) select.value = previous;
  } catch (err) {
    flash("Не удалось загрузить учеников: " + err.message, true);
  }
}

function openStudentForm() {
  $("student-details").open = true;
  $("student-details").scrollIntoView({ behavior: "smooth", block: "nearest" });
  $("st-name").focus({ preventScroll: true });
}

function prefillPayment(d) {
  const section = $("pay-section");
  $("pay-student").value = d.student_id;
  $("pay-amount").value = d.debt;

  // On wide screens the form is already visible next to the list: only scroll when it is not.
  const rect = section.getBoundingClientRect();
  if (rect.top < 0 || rect.bottom > window.innerHeight) {
    section.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  section.classList.remove("is-flash");
  void section.offsetWidth; // restart the highlight animation
  section.classList.add("is-flash");
  $("pay-amount").focus({ preventScroll: true });
}

// ---------- Forms ----------

// Disable the submit button while the request is in flight so a double tap doesn't send twice.
async function submitting(form, action) {
  const button = form.querySelector("button[type=submit]");
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Сохранение…";
  try {
    await action();
  } catch (err) {
    flash(err.message, true);
  } finally {
    button.disabled = false;
    button.textContent = label;
  }
}

$("payment-form").addEventListener("submit", (e) => {
  e.preventDefault();
  submitting(e.target, async () => {
    const payment = await api("/payments", {
      method: "POST",
      body: JSON.stringify({
        student_id: Number($("pay-student").value),
        amount: Number($("pay-amount").value),
        date: $("pay-date").value,
      }),
    });
    // reset() also clears the browser's "user touched this" state, so the now-empty amount isn't
    // flagged red; the student and date stay, because several payments are usually entered in a row.
    const keep = { student: $("pay-student").value, date: $("pay-date").value };
    e.target.reset();
    $("pay-student").value = keep.student;
    $("pay-date").value = keep.date;
    flash(`Оплата ${fmt(payment.amount)} ${CURRENCY} сохранена`);
    await loadDebtors();
  });
});

$("student-form").addEventListener("submit", (e) => {
  e.preventDefault();
  submitting(e.target, async () => {
    const student = await api("/students", {
      method: "POST",
      body: JSON.stringify({
        name: $("st-name").value,
        phone: $("st-phone").value,
        group: $("st-group").value,
        monthly_fee: Number($("st-fee").value),
      }),
    });
    e.target.reset();
    flash(`Ученик «${student.name}» добавлен`);
    await loadStudents(); // the debtors empty state depends on the student count
    await loadDebtors();
  });
});

// ---------- Start ----------

document.querySelectorAll("[data-currency]").forEach((node) => (node.textContent = CURRENCY));
$("pay-date").value = todayISO();
syncThemeUI();
syncMonthUI();
loadStudents().then(loadDebtors);
