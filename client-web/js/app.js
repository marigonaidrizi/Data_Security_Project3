(function () {
  const DEFAULT_API_BASE = "http://127.0.0.1:8000";

  function getApiBase() {
    const saved = localStorage.getItem("secureFtpApiBase");
    if (saved) {
      return saved.replace(/\/+$/, "");
    }
    if (window.location.protocol === "http:" || window.location.protocol === "https:") {
      return window.location.origin;
    }
    return DEFAULT_API_BASE;
  }

  function setupApiBaseControl() {
    const input = document.querySelector("[data-api-base]");
    if (!input) {
      return;
    }
    input.value = getApiBase();
    input.addEventListener("change", () => {
      const value = input.value.trim().replace(/\/+$/, "");
      localStorage.setItem("secureFtpApiBase", value || DEFAULT_API_BASE);
    });
  }

  function setStatus(title, message, append) {
    const statusTitle = document.getElementById("status-title");
    const log = document.getElementById("transfer-log");
    if (statusTitle) {
      statusTitle.textContent = title;
    }
    if (log && message) {
      log.textContent = append ? `${log.textContent}\n${message}` : message;
    }
  }

  function formatBytes(size) {
    const value = Number(size || 0);
    const units = ["B", "KB", "MB", "GB"];
    let scaled = value;
    for (const unit of units) {
      if (scaled < 1024 || unit === units[units.length - 1]) {
        return unit === "B" ? `${scaled} ${unit}` : `${scaled.toFixed(1)} ${unit}`;
      }
      scaled /= 1024;
    }
    return `${value} B`;
  }

  function formatDate(value) {
    if (!value) {
      return "Unknown";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function verifiedCount(files) {
    return files.filter((file) => file.hash_verified && file.signature_verified).length;
  }

  function downloadCount(files) {
    return files.reduce((sum, file) => sum + Number(file.download_count || 0), 0);
  }

  function statusBadge(file) {
    const verified = file.hash_verified && file.signature_verified;
    return `<span class="badge ${verified ? "" : "bad"}">${verified ? "✓ Verified" : "Verification issue"}</span>`;
  }

  function fileTableRows(files, includeActions) {
    if (!files.length) {
      return '<tr><td colspan="6" class="empty-cell">No files are available yet.</td></tr>';
    }
    return files
      .map((file) => `
        <tr>
          <td><span class="file-name"><span class="file-icon">□</span>${file.filename}</span></td>
          <td>${statusBadge(file)}</td>
          <td>${formatDate(file.uploaded_at)}</td>
          <td>${formatBytes(file.original_size)}</td>
          <td>${Number(file.download_count || 0)}</td>
          <td class="action-cell">${
            includeActions
              ? `<button class="button secondary" type="button" data-download-id="${file.file_id}">Download</button>`
              : '<a class="button secondary" href="download.html">Open</a>'
          }</td>
        </tr>
      `)
      .join("");
  }

  async function fetchJson(path, options) {
    const response = await fetch(`${getApiBase()}${path}`, options);
    const data = await response.json().catch(() => ({
      success: false,
      error: "INVALID_RESPONSE",
      message: "Server returned a non-JSON response.",
    }));
    if (!response.ok || data.success === false) {
      const message = data.message || `HTTP ${response.status}`;
      const error = new Error(message);
      error.payload = data;
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function loadDashboard() {
    const total = document.getElementById("dashboard-total-files");
    if (!total) {
      return;
    }
    const healthTitle = document.getElementById("dashboard-health-title");
    const healthCopy = document.getElementById("dashboard-health-copy");
    const healthDot = document.querySelector("#dashboard-health-card .status-dot");
    const verified = document.getElementById("dashboard-verified-files");
    const downloads = document.getElementById("dashboard-download-count");
    const table = document.getElementById("dashboard-recent-files");

    try {
      const [health, filesResponse] = await Promise.all([fetchJson("/api/health"), fetchJson("/api/files")]);
      const files = filesResponse.files || [];
      healthTitle.textContent = "System healthy";
      healthCopy.textContent = `${health.files_stored} stored file(s). API is running.`;
      total.textContent = files.length;
      verified.textContent = verifiedCount(files);
      downloads.textContent = downloadCount(files);
      table.innerHTML = fileTableRows(files.slice(0, 5), false);
      if (healthDot) {
        healthDot.classList.remove("bad");
      }
    } catch (error) {
      healthTitle.textContent = "Server unavailable";
      healthCopy.textContent = error.message;
      table.innerHTML = '<tr><td colspan="6" class="empty-cell error">Could not load files.</td></tr>';
      if (healthDot) {
        healthDot.classList.add("bad");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupApiBaseControl();
    loadDashboard();
  });

  window.SecureApp = {
    getApiBase,
    setupApiBaseControl,
    setStatus,
    formatBytes,
    formatDate,
    verifiedCount,
    downloadCount,
    fileTableRows,
    fetchJson,
  };
})();
