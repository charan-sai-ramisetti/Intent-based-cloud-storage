/* ===============================
   DASHBOARD INIT
   =============================== */

document.addEventListener("DOMContentLoaded", () => {
  loadSubscriptionStatus();
  loadStorageSummary();
  loadFolders();
  loadRecentFiles();
});

document.getElementById("fileInput").addEventListener("change", function () {
  const label = document.getElementById("selected-file-text");
  if (this.files.length > 0) {
    label.innerText = this.files[0].name;
  } else {
    label.innerText = "Select file";
  }
});


/* ===============================
   SUBSCRIPTION STATUS
   =============================== */

function loadSubscriptionStatus() {
  fetch(`${API_BASE_URL}/payments/subscription/status/`, {
    headers: authHeaders()
  })
    .then(res => res.json())
    .then(data => {
      const planEl = document.getElementById("plan-name");
      const upgradeBtn = document.getElementById("upgrade-btn");

      if (planEl) {
        planEl.innerText = data.plan;
      }

      if (data.plan === "PRO" && upgradeBtn) {
        upgradeBtn.style.display = "none";
      }
    })
    .catch(err => console.error("Subscription error", err));
}

/* ===============================
   STORAGE SUMMARY
   =============================== */

function loadStorageSummary() {
  fetch(`${API_BASE_URL}/storage/summary/`, {
    headers: authHeaders()
  })
    .then(res => res.json())
    .then(data => {
      updateStorageBar("aws", data.aws);
      updateStorageBar("azure", data.azure);
      updateStorageBar("gcp", data.gcp);
    })
    .catch(err => console.error("Storage summary error", err));
}
function updateStorageBar(cloud, info) {
  const bar = document.getElementById(`${cloud}-bar`);
  const text = document.getElementById(`${cloud}-text`);

  if (!bar || !text) return;

  // Text always correct
  text.innerText = `${info.used_mb} MB / ${info.limit_mb} MB`;

  // Case 1: truly zero
  if (info.used_mb === 0) {
    bar.style.width = "0%";
    bar.style.display = "none";
    return;
  }

  // Case 2: very small but non-zero
  let percent = (info.used_mb / info.limit_mb) * 100;

  // ensure visibility without lying
  if (percent < 0.5) {
    percent = 0.5;
  }

  bar.style.display = "block";
  bar.style.width = `${percent}%`;
}

/* ===============================
   FOLDER SUMMARY
   =============================== */

function loadFolders() {
  fetch(`${API_BASE_URL}/storage/folders/`, {
    headers: authHeaders()
  })
    .then(res => res.json())
    .then(folders => {
      const container = document.getElementById("folders-container");
      if (!container) return;

      container.innerHTML = "";

      folders.forEach(folder => {
        const card = document.createElement("div");
        card.className = "folder-card";
        card.innerHTML = `
          <strong>${folder.name}</strong>
          <div>${folder.count} files</div>
          <div>${folder.size_mb} MB</div>
        `;
        container.appendChild(card);
      });
    })
    .catch(err => console.error("Folders error", err));
}

/* ===============================
   RECENT FILES
   =============================== */

function loadRecentFiles() {
  fetch(`${API_BASE_URL}/storage/recent-files/`, {
    headers: authHeaders()
  })
    .then(res => res.json())
    .then(files => {
      const table = document.getElementById("recent-files-table");
      if (!table) return;

      table.innerHTML = "";

      files.forEach(file => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${file.file_name}</td>
          <td>${file.size_mb} MB</td>
          <td>${file.clouds.join(", ")}</td>
          <td>${new Date(file.uploaded_at).toLocaleDateString()}</td>
        `;
        table.appendChild(row);
      });
    })
    .catch(err => console.error("Recent files error", err));
}
