let deleteTarget = {
  fileId: null,
  clouds: []
};


// Load files when dashboard opens
document.addEventListener("DOMContentLoaded", loadFiles);

function loadFiles() {
  // authFetch automatically refreshes an expired token before this request
  // so a user who has been on the page for 2+ hours still sees their files
  authFetch(`${API_BASE_URL}/files/`, {
    method: "GET",
    headers: authHeaders()
  })
    .then(res => res.json())
    .then(data => {
      const table = document.getElementById("filesTable");
      table.innerHTML = "";

      data.forEach(file => {
        const clouds = [];

        if (file.aws_path) clouds.push("AWS");
        if (file.azure_path) clouds.push("AZURE");
        if (file.gcp_path) clouds.push("GCP");

        const row = document.createElement("tr");

        row.innerHTML = `
          <td>${file.file_name}</td>
          <td>${clouds.join(", ")}</td>
          <td class="actions">
            <div class="action-buttons">
              <button class="btn-download">Download</button>
              <button class="btn-delete">Delete</button>
            </div>
          </td>
        `;

        table.appendChild(row);

        // Download
        row.querySelector(".btn-download").addEventListener("click", () => {
          downloadFile(file.id);
        });

        // Delete (open modal)
        row.querySelector(".btn-delete").addEventListener("click", () => {
          openDeleteModal(file.id, clouds);
        });
      });
    })
    .catch(() => alert("Failed to load files"));
}


/* ===============================
   DOWNLOAD FILE
   =============================== */
function downloadFile(fileId) {
  // authFetch handles token refresh automatically — this was returning 400
  // "Authentication credentials were not provided" because the access token
  // had expired (120 min lifetime) and authHeaders() was sending
  // "Authorization: Bearer null" or an expired token. authFetch silently
  // refreshes the token and retries so the download works without reloading.
  authFetch(`${API_BASE_URL}/files/${fileId}/presign/download/`, {
    method: "GET",
    headers: authHeaders()
  })
    .then(res => {
      if (!res.ok) {
        // Surface the actual error rather than silently failing
        return res.json().then(err => {
          throw new Error(err.error || err.detail || `HTTP ${res.status}`);
        });
      }
      return res.json();
    })
    .then(data => {
      window.open(data.download_url, "_blank");
    })
    .catch(err => alert(`Download failed: ${err.message}`));
}

document.getElementById("confirmDeleteBtn").onclick = function () {
  const checked = Array.from(
    document.querySelectorAll("#deleteCloudOptions input:checked")
  ).map(cb => cb.value.toUpperCase());

  if (checked.length === 0) {
    alert("Select at least one cloud");
    return;
  }

  authFetch(`${API_BASE_URL}/files/${deleteTarget.fileId}/`, {
    method: "DELETE",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ clouds: checked })
  })
    .then(res => {
      if (!res.ok) throw new Error();
      closeDeleteModal();
      loadFiles();
      loadRecentFiles();
      loadFolders();
      loadStorageSummary();
    })
    .catch(() => alert("Delete failed"));
};


function openDeleteModal(fileId, clouds) {
  deleteTarget.fileId = fileId;
  deleteTarget.clouds = clouds;

  const container = document.getElementById("deleteCloudOptions");
  container.innerHTML = "";

  clouds.forEach(cloud => {
    const label = document.createElement("label");
    label.style.display = "block";
    label.style.marginBottom = "8px";

    label.innerHTML = `
      <input type="checkbox" value="${cloud}" checked>
      ${cloud}
    `;

    container.appendChild(label);
  });

  document.getElementById("deleteModal").classList.remove("hidden");
}

function closeDeleteModal() {
  document.getElementById("deleteModal").classList.add("hidden");
}