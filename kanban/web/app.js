const columns = [
  { id: "todo", title: "To Do", hint: "Ready when you are." },
  { id: "in-progress", title: "In Progress", hint: "Room for the work underway." },
  { id: "done", title: "Done", hint: "Good work belongs here." },
];
const board = document.querySelector("#board");
const dialog = document.querySelector("#task-dialog");
const form = document.querySelector("#task-form");
const search = document.querySelector("#search");
const notice = document.querySelector("#notice");
const formError = document.querySelector("#form-error");
const newButton = document.querySelector("#new-task");
const saveButton = document.querySelector("#save-task");
const deleteButton = document.querySelector("#delete-task");
let tasks = [];
let readOnly = true;
let activeTask = null;
let pending = false;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function statusOptions(select, value) {
  for (const column of columns) {
    const option = element("option", "", column.title);
    option.value = column.id;
    select.append(option);
  }
  select.value = value;
}

function showError(target, error) {
  target.textContent = error.message;
  target.hidden = false;
}

async function request(path, method = "GET", data) {
  const options = { method, cache: "no-store" };
  if (method !== "GET") options.headers = { "Content-Type": "application/json" };
  if (data !== undefined) {
    options.body = JSON.stringify(data);
  }
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try { message = (await response.json()).error || message; } catch {}
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function card(task) {
  const article = element("article", "card");
  article.dataset.id = task.id;
  const top = element("div", "card-top");
  top.append(element("span", "task-key", task.id.slice(0, 8)));
  const priority = element("span", `priority priority-${task.priority}`, task.priority);
  top.append(priority);
  const title = element("button", "card-title", task.title);
  title.type = "button";
  title.addEventListener("click", () => openTask(task));
  article.append(top, title);
  if (task.description) article.append(element("p", "card-description", task.description));
  if (task.labels.length) {
    const labels = element("div", "labels");
    for (const label of task.labels) labels.append(element("span", "label", label));
    article.append(labels);
  }
  if (task.acceptanceCriteria.length) {
    const count = task.acceptanceCriteria.length;
    article.append(element("p", "criteria-count", `${count} acceptance ${count === 1 ? "criterion" : "criteria"}`));
  }
  const bottom = element("div", "card-bottom");
  const assignee = element("div", "assignee");
  const initials = task.assignee.trim().split(/\s+/).map((word) => word[0]).slice(0, 2).join("").toUpperCase();
  const avatar = element("span", "avatar", initials || "?");
  avatar.setAttribute("aria-hidden", "true");
  assignee.append(avatar, element("span", "assignee-name", task.assignee || "Unassigned"));
  bottom.append(assignee);
  if (!readOnly) {
    const select = element("select", "move-select");
    select.setAttribute("aria-label", `Move ${task.title}`);
    select.disabled = pending;
    statusOptions(select, task.status);
    select.addEventListener("change", () => moveTask(task, select.value));
    bottom.append(select);
    article.draggable = !pending;
    article.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData("text/plain", task.id);
      event.dataTransfer.effectAllowed = "move";
      article.classList.add("dragging");
    });
    article.addEventListener("dragend", () => {
      article.classList.remove("dragging");
      document.querySelectorAll(".drop-target").forEach((node) => node.classList.remove("drop-target"));
    });
  }
  article.append(bottom);
  return article;
}

function render() {
  board.replaceChildren();
  const query = search.value.trim().toLowerCase();
  const matches = tasks.filter((task) => [task.title, task.description, task.assignee, ...task.labels].join(" ").toLowerCase().includes(query));
  document.querySelector("#total").textContent = tasks.length;
  for (const column of columns) {
    const section = element("section", `column column-${column.id}`);
    section.dataset.status = column.id;
    section.setAttribute("aria-labelledby", `heading-${column.id}`);
    const heading = element("div", "column-heading");
    const marker = element("span", "status-marker");
    marker.setAttribute("aria-hidden", "true");
    const title = element("h2", "", column.title);
    title.id = `heading-${column.id}`;
    const columnTasks = matches.filter((task) => task.status === column.id);
    heading.append(marker, title, element("span", "count", columnTasks.length));
    if (!readOnly) {
      const add = element("button", "column-add", "+");
      add.type = "button";
      add.disabled = pending;
      add.setAttribute("aria-label", `Add task to ${column.title}`);
      add.addEventListener("click", () => openTask(null, column.id));
      heading.append(add);
      section.addEventListener("dragover", (event) => {
        if (pending || !event.dataTransfer.types.includes("text/plain")) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        section.classList.add("drop-target");
      });
      section.addEventListener("dragleave", (event) => {
        if (!section.contains(event.relatedTarget)) section.classList.remove("drop-target");
      });
      section.addEventListener("drop", (event) => {
        event.preventDefault();
        section.classList.remove("drop-target");
        const task = tasks.find((item) => item.id === event.dataTransfer.getData("text/plain"));
        if (task) moveTask(task, column.id);
      });
    }
    section.append(heading);
    if (!columnTasks.length) {
      const empty = element("div", "empty");
      empty.append(element("p", "", query ? "No matching tasks" : "No tasks yet"), element("span", "", query ? "Try another search." : column.hint));
      section.append(empty);
    }
    for (const task of columnTasks) section.append(card(task));
    board.append(section);
  }
}

function openTask(task, status = "todo") {
  activeTask = task;
  form.reset();
  formError.hidden = true;
  document.querySelector("#dialog-title").textContent = readOnly ? "Task details" : task ? "Edit task" : "New task";
  document.querySelector("#task-id").textContent = task ? `CARDINAL / ${task.id.slice(0, 8)}` : "CARDINAL / TASK";
  const values = task || { title: "", description: "", assignee: "", status, priority: "medium", labels: [], acceptanceCriteria: [] };
  for (const name of ["title", "description", "assignee", "status", "priority"]) form.elements[name].value = values[name];
  form.elements.labels.value = values.labels.join(", ");
  form.elements.acceptanceCriteria.value = values.acceptanceCriteria.join("\n");
  for (const input of form.querySelectorAll("input, textarea, select")) input.disabled = readOnly;
  deleteButton.hidden = readOnly || !task;
  saveButton.hidden = readOnly;
  saveButton.textContent = task ? "Save changes" : "Create task";
  document.querySelector("#cancel-dialog").textContent = readOnly ? "Close" : "Cancel";
  document.querySelector("#readonly-help").hidden = !readOnly;
  dialog.showModal();
}

function setPending(value) {
  pending = value;
  saveButton.disabled = value;
  deleteButton.disabled = value;
  newButton.disabled = value;
  document.querySelector("#close-dialog").disabled = value;
  document.querySelector("#cancel-dialog").disabled = value;
  render();
}

function keepTask(task) {
  const index = tasks.findIndex((item) => item.id === task.id);
  if (index === -1) tasks.push(task);
  else tasks[index] = task;
}

async function moveTask(task, status) {
  if (readOnly || pending || task.status === status) return;
  notice.hidden = true;
  setPending(true);
  try {
    const { id, ...fields } = task;
    keepTask(await request(`./api/tasks/${id}`, "PUT", { ...fields, status }));
  } catch (error) { showError(notice, error); }
  finally { setPending(false); }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (readOnly || pending) return;
  const values = Object.fromEntries(new FormData(form));
  values.labels = values.labels.split(",").map((value) => value.trim()).filter(Boolean);
  values.acceptanceCriteria = values.acceptanceCriteria.split(/\r?\n/).map((value) => value.trim()).filter(Boolean);
  formError.hidden = true;
  notice.hidden = true;
  setPending(true);
  try {
    const task = await request(activeTask ? `./api/tasks/${activeTask.id}` : "./api/tasks", activeTask ? "PUT" : "POST", values);
    keepTask(task);
    dialog.close();
  } catch (error) { showError(formError, error); }
  finally { setPending(false); }
});

deleteButton.addEventListener("click", async () => {
  if (readOnly || pending || !activeTask || !confirm(`Delete "${activeTask.title}"? This removes its Markdown file.`)) return;
  formError.hidden = true;
  notice.hidden = true;
  setPending(true);
  try {
    await request(`./api/tasks/${activeTask.id}`, "DELETE");
    tasks = tasks.filter((task) => task.id !== activeTask.id);
    dialog.close();
  } catch (error) { showError(formError, error); }
  finally { setPending(false); }
});

for (const id of ["close-dialog", "cancel-dialog"]) document.querySelector(`#${id}`).addEventListener("click", () => dialog.close());
dialog.addEventListener("cancel", (event) => { if (pending) event.preventDefault(); });
newButton.addEventListener("click", () => openTask(null));
search.addEventListener("input", render);
statusOptions(form.elements.status, "todo");

async function load() {
  try {
    const data = await request("./board.json");
    tasks = data.tasks;
    readOnly = data.readOnly;
    document.querySelector("#mode").textContent = readOnly ? "Read-only board" : "Local editing";
    document.querySelector("#mode").classList.toggle("editable", !readOnly);
    document.querySelector("#board-help").textContent = readOnly ? "Published snapshot. Open any task to view its details." : "Drag tasks between columns or use their status menu. Changes save to kanban/tasks/.";
    newButton.hidden = readOnly;
    render();
  } catch (error) {
    document.querySelector("#mode").textContent = "Unavailable";
    showError(notice, new Error(`Could not load the board. ${error.message} Refresh to try again.`));
  } finally { document.querySelector("#loading").hidden = true; }
}

load();
