class CatalogApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async getOverview() {
    return this.fetchJson("/health");
  }

  async getRuns() {
    return this.fetchJson("/runs?limit=50&sort_by=scraped_at&sort_order=desc");
  }

  async getCategories(runId) {
    const params = new URLSearchParams({
      limit: "50",
      sort_by: "category",
      sort_order: "asc",
    });
    if (runId) {
      params.set("run_id", runId);
    }
    return this.fetchJson(`/categories?${params.toString()}`);
  }

  async getBooks(filters) {
    const params = new URLSearchParams({ limit: "50" });
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== "") {
        params.set(key, value);
      }
    });
    return this.fetchJson(`/books?${params.toString()}`);
  }

  async getBookHistory(upc) {
    return this.fetchJson(`/books/${encodeURIComponent(upc)}/history?limit=10`);
  }

  async fetchJson(path) {
    const response = await fetch(`${this.baseUrl}${path}`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Не удалось получить данные из API.");
    }
    return payload;
  }
}

class CatalogFiltersView {
  constructor(formElement) {
    this.formElement = formElement;
    this.categorySelect = formElement.elements.category;
    this.runSelect = formElement.elements.run_id;
  }

  readFilters() {
    const values = {};
    new FormData(this.formElement).forEach((value, key) => {
      values[key] = String(value).trim();
    });
    return values;
  }

  reset() {
    this.formElement.reset();
  }

  fillRuns(runs) {
    this.runSelect.innerHTML = '<option value="">Последний запуск</option>';
    runs.forEach((run) => {
      const option = document.createElement("option");
      option.value = run.run_id;
      option.textContent = `${formatDate(run.scraped_at)} · ${run.total_books} книг`;
      this.runSelect.append(option);
    });
  }

  fillCategories(categories) {
    const currentValue = this.categorySelect.value;
    this.categorySelect.innerHTML = '<option value="">Все категории</option>';
    categories.forEach((category) => {
      const option = document.createElement("option");
      option.value = category.category;
      option.textContent = `${category.category} (${category.total_books})`;
      this.categorySelect.append(option);
    });
    this.categorySelect.value = currentValue;
  }
}

class MetricsView {
  constructor() {
    this.totalBooksMetric = document.querySelector("#totalBooksMetric");
    this.totalRunsMetric = document.querySelector("#totalRunsMetric");
    this.resultCountLabel = document.querySelector("#resultCountLabel");
    this.selectedRunLabel = document.querySelector("#selectedRunLabel");
  }

  updateOverview(overview) {
    this.totalRunsMetric.textContent = overview.total_runs ?? "-";
  }

  updateBooks(payload) {
    this.totalBooksMetric.textContent = payload.meta.total;
    this.resultCountLabel.textContent = `${payload.meta.returned} из ${payload.meta.total}`;
    this.selectedRunLabel.textContent = `Run: ${payload.selected_run_id}`;
  }
}

class BooksGridView {
  constructor(gridElement, emptyStateElement) {
    this.gridElement = gridElement;
    this.emptyStateElement = emptyStateElement;
  }

  render(books) {
    this.gridElement.innerHTML = "";
    this.emptyStateElement.hidden = books.length > 0;
    books.forEach((book) => this.gridElement.append(this.createCard(book)));
  }

  createCard(book) {
    const card = document.createElement("article");
    card.className = "book-card";
    card.innerHTML = `
      <span class="book-category">${escapeHtml(book.category)}</span>
      <h3>${escapeHtml(book.title)}</h3>
      <div class="price">${formatPrice(book.price_rub)}</div>
      <div class="book-meta">
        <span>${renderStars(book.rating)}</span>
        <span>${formatPrice(book.price_gbp, "GBP")}</span>
        <span>${escapeHtml(book.upc)}</span>
      </div>
      <div class="book-actions">
        <span class="stock ${book.is_in_stock ? "" : "out"}">
          ${book.is_in_stock ? "В наличии" : "Нет в наличии"}
        </span>
        <button class="text-link" type="button" data-upc="${escapeHtml(book.upc)}">
          История цены
        </button>
      </div>
    `;
    return card;
  }
}

class AlertView {
  constructor(alertElement) {
    this.alertElement = alertElement;
  }

  show(message) {
    this.alertElement.textContent = message;
    this.alertElement.hidden = false;
  }

  hide() {
    this.alertElement.hidden = true;
    this.alertElement.textContent = "";
  }
}

class HistoryDialogView {
  constructor(dialogElement) {
    this.dialogElement = dialogElement;
    this.contentElement = dialogElement.querySelector("#historyContent");
    dialogElement.querySelector(".dialog-close").addEventListener("click", () => this.close());
  }

  show(payload) {
    this.contentElement.innerHTML = payload.items.map((item) => this.renderItem(item)).join("");
    this.dialogElement.showModal();
  }

  showError(message) {
    this.contentElement.innerHTML = `<p>${escapeHtml(message)}</p>`;
    this.dialogElement.showModal();
  }

  close() {
    this.dialogElement.close();
  }

  renderItem(item) {
    return `
      <div class="history-item">
        <div>
          <strong>${formatDate(item.scraped_at)}</strong>
          <span>${escapeHtml(item.run_id)}</span>
        </div>
        <strong>${formatPrice(item.price_rub)}</strong>
      </div>
    `;
  }
}

class CatalogController {
  constructor(apiClient, filtersView, metricsView, booksView, alertView, historyDialog) {
    this.apiClient = apiClient;
    this.filtersView = filtersView;
    this.metricsView = metricsView;
    this.booksView = booksView;
    this.alertView = alertView;
    this.historyDialog = historyDialog;
  }

  bind() {
    this.filtersView.formElement.addEventListener("submit", (event) => {
      event.preventDefault();
      this.loadBooks();
    });
    document.querySelector("#resetFilters").addEventListener("click", () => {
      this.filtersView.reset();
      this.loadBooks();
    });
    this.filtersView.runSelect.addEventListener("change", () => this.loadCategories());
    document.querySelector("#booksGrid").addEventListener("click", (event) => {
      const button = event.target.closest("[data-upc]");
      if (button) {
        this.openHistory(button.dataset.upc);
      }
    });
  }

  async start() {
    this.bind();
    await Promise.all([this.loadOverview(), this.loadRuns()]);
    await this.loadCategories();
    await this.loadBooks();
  }

  async loadOverview() {
    try {
      const payload = await this.apiClient.getOverview();
      this.metricsView.updateOverview(payload.overview);
    } catch (error) {
      this.alertView.show(error.message);
    }
  }

  async loadRuns() {
    try {
      const payload = await this.apiClient.getRuns();
      this.filtersView.fillRuns(payload.items);
    } catch (error) {
      this.alertView.show(error.message);
    }
  }

  async loadCategories() {
    try {
      const payload = await this.apiClient.getCategories(this.filtersView.runSelect.value);
      this.filtersView.fillCategories(payload.items);
    } catch (error) {
      this.alertView.show(error.message);
    }
  }

  async loadBooks() {
    try {
      this.alertView.hide();
      const payload = await this.apiClient.getBooks(this.filtersView.readFilters());
      this.metricsView.updateBooks(payload);
      this.booksView.render(payload.items);
    } catch (error) {
      this.booksView.render([]);
      this.alertView.show(error.message);
    }
  }

  async openHistory(upc) {
    try {
      const payload = await this.apiClient.getBookHistory(upc);
      this.historyDialog.show(payload);
    } catch (error) {
      this.historyDialog.showError(error.message);
    }
  }
}

function formatPrice(value, currency = "RUB") {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency,
    maximumFractionDigits: currency === "RUB" ? 0 : 2,
  }).format(value);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function renderStars(rating) {
  const count = Number(rating || 0);
  return "★".repeat(count) + "☆".repeat(Math.max(0, 5 - count));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
  const controller = new CatalogController(
    new CatalogApiClient("/api/v1"),
    new CatalogFiltersView(document.querySelector("#catalogFilters")),
    new MetricsView(),
    new BooksGridView(document.querySelector("#booksGrid"), document.querySelector("#emptyState")),
    new AlertView(document.querySelector("#alertBox")),
    new HistoryDialogView(document.querySelector("#historyDialog")),
  );
  controller.start();
});
