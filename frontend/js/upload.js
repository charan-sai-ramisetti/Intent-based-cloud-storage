let lastUploadMeta = null;
let uploadResults = {};

const CHUNK_SIZE = 10 * 1024 * 1024;
const MAX_PARALLEL_UPLOADS = 3;
const BREATHING_DELAY = 50;

const MAX_CHUNK_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 2000; // 2s → 4s → 8s


/* ===============================
   FILE LABEL
================================ */
document.addEventListener("change", function (e) {
  if (e.target && e.target.id === "fileInput") {
    const label = document.getElementById("selected-file-text");
    if (!label) return;
    label.innerText = e.target.files.length > 0 ? e.target.files[0].name : "Select file";
  }
});


/* ===============================
   BUTTON CONTROL
================================ */
function setUploadButton(disabled, text) {
  const btn = document.getElementById("uploadBtn");
  if (!btn) return;
  btn.disabled = disabled;
  if (text) btn.innerText = text;
}


/* ===============================
   RESET FORM
================================ */
function resetUploadForm() {
  const wrapper = document.getElementById("file-input-wrapper");
  if (!wrapper) return;
  wrapper.innerHTML = `
    <label class="file-picker">
      <input type="file" id="fileInput" hidden />
      <span id="selected-file-text">Select file</span>
    </label>
  `;
  document
    .querySelectorAll("#cloudSelect input[type='checkbox']")
    .forEach(cb => (cb.checked = false));
}


/* ===============================
   CREATE STATUS BOX
================================ */
function createStatusBox(file, cloud, targetContainer) {
  const container = targetContainer || document.getElementById("upload-status-container");
  if (!container) return null;

  let title = container.querySelector(".upload-title");
  if (!title) {
    title = document.createElement("div");
    title.className = "upload-title mb-2";
    title.innerHTML = `<strong>${file.name}</strong> <span class="text-muted small">(${(file.size / (1024 * 1024)).toFixed(2)} MB)</span>`;
    container.appendChild(title);
  }

  const statusBox = document.createElement("div");
  statusBox.className = "upload-status mb-2 p-2 border rounded bg-white shadow-sm";
  statusBox.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-1">
      <strong class="text-primary">${cloud}</strong>
      <span class="status-text small text-muted">Starting… 0%</span>
    </div>
    <div class="progress" style="height: 6px;">
      <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" style="width: 0%"></div>
    </div>
  `;
  container.appendChild(statusBox);
  return statusBox;
}


/* ===============================
   DIRECT UPLOAD (REUSABLE PIPELINE)
================================ */
function startDirectUpload(file, clouds, targetContainer) {
  const container = targetContainer || document.getElementById("upload-status-container");
  if (container) container.innerHTML = "";

  return fetch(`${API_BASE_URL}/files/presign/upload/`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      file_name: file.name,
      file_size: file.size,
      file_type: file.type || "application/octet-stream",
      clouds: clouds
    })
  })
    .then(res => {
      if (!res.ok) throw new Error("Failed to generate presigned upload URLs");
      return res.json();
    })
    .then(data => {
      if (data.upload_type === "single") {
        return startSingleUpload(file, clouds, data, container);
      } else {
        return startMultipartUpload(file, clouds, container);
      }
    });
}


/* ===============================
   START MANUAL UPLOAD
================================ */
function startUpload() {
  setUploadButton(true, "Uploading...");
  const fileInput = document.getElementById("fileInput");
  const selectedClouds = document.querySelectorAll("#cloudSelect input[type='checkbox']:checked");

  if (!fileInput || !fileInput.files.length) {
    alert("Please select a file");
    setUploadButton(false, "Upload");
    return;
  }

  if (selectedClouds.length === 0) {
    alert("Please select at least one cloud");
    setUploadButton(false, "Upload");
    return;
  }

  const file = fileInput.files[0];
  const clouds = Array.from(selectedClouds).map(cb => cb.value);

  startDirectUpload(file, clouds, document.getElementById("upload-status-container"))
    .catch(err => {
      console.error("Upload error:", err);
      alert("Upload failed: " + (err.message || err));
      setUploadButton(false, "Upload");
    });
}


/* ===============================
   SINGLE UPLOAD
================================ */
function startSingleUpload(file, clouds, data, targetContainer) {
  uploadResults = {};
  clouds.forEach(c => uploadResults[c] = false);
  lastUploadMeta = { file_name: file.name, file_size: file.size, aws_path: null, azure_path: null, gcp_path: null };

  const uploads = clouds.map(cloud => {
    const box = createStatusBox(file, cloud, targetContainer);
    return uploadSingleFile(file, cloud, data.upload_urls[cloud], box)
      .then(() => {
        uploadResults[cloud] = true;
        if (cloud === "AWS") lastUploadMeta.aws_path = data.paths.aws_path;
        if (cloud === "AZURE") lastUploadMeta.azure_path = data.paths.azure_path;
        if (cloud === "GCP") lastUploadMeta.gcp_path = data.paths.gcp_path;
      });
  });

  return Promise.allSettled(uploads).then(() => {
    const success = Object.keys(uploadResults).filter(c => uploadResults[c]);
    if (success.length === 0) {
      alert("Upload failed for all selected clouds.");
      setUploadButton(false, "Upload");
      throw new Error("Upload failed for all selected clouds.");
    }
    return confirmUpload(success, targetContainer);
  });
}


/* ===============================
   SINGLE FILE UPLOAD
================================ */
function uploadSingleFile(file, cloud, uploadUrl, statusBox) {
  return new Promise((resolve, reject) => {
    const progressEl = statusBox ? statusBox.querySelector(".progress-bar") : null;
    const statusText = statusBox ? statusBox.querySelector(".status-text") : null;
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl, true);

    // Azure single-blob PUT requires this header to set the blob type
    if (cloud === "AZURE") {
      xhr.setRequestHeader("x-ms-blob-type", "BlockBlob");
    }

    // GCP signed URLs include content_type="application/octet-stream" in the signature.
    if (cloud === "GCP") {
      xhr.setRequestHeader("Content-Type", "application/octet-stream");
    }

    xhr.upload.onprogress = e => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        if (progressEl) progressEl.style.width = percent + "%";
        if (statusText) statusText.innerText = `Uploading… ${percent}%`;
      }
    };

    xhr.onload = () => {
      if (xhr.status === 200 || xhr.status === 201) {
        if (progressEl) {
          progressEl.style.width = "100%";
          progressEl.classList.remove("progress-bar-animated");
          progressEl.classList.add("bg-success");
        }
        if (statusText) statusText.innerText = "Uploaded 100%";
        resolve();
      } else {
        if (statusText) statusText.innerText = `Failed (HTTP ${xhr.status})`;
        reject(new Error(`HTTP ${xhr.status}`));
      }
    };

    xhr.onerror = () => {
      if (statusText) statusText.innerText = "Network Error";
      reject(new Error("Network Error"));
    };

    const body = (cloud === "GCP") ? new Blob([file], { type: "application/octet-stream" }) : file;
    xhr.send(body);
  });
}


/* ===============================
   MULTIPART UPLOAD
================================ */
async function startMultipartUpload(file, clouds, targetContainer) {
  lastUploadMeta = { file_name: file.name, file_size: file.size, aws_path: null, azure_path: null, gcp_path: null };

  const uploads = clouds.map(cloud => multipartForCloud(file, cloud, targetContainer));
  const results = await Promise.allSettled(uploads);
  const success = [];
  results.forEach((r, i) => { if (r.status === "fulfilled") success.push(clouds[i]); });

  if (success.length === 0) {
    alert("Upload failed. Check your connection and try again.");
    setUploadButton(false, "Upload");
    throw new Error("Multipart upload failed for all selected clouds.");
  }
  return confirmUpload(success, targetContainer);
}


/* ===============================
   MULTIPART PER CLOUD
================================ */
async function multipartForCloud(file, cloud, targetContainer) {
  const statusBox = createStatusBox(file, cloud, targetContainer);
  const progressEl = statusBox ? statusBox.querySelector(".progress-bar") : null;
  const statusText = statusBox ? statusBox.querySelector(".status-text") : null;

  const start = await fetch(`${API_BASE_URL}/files/multipart/start/`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ file_name: file.name, file_type: file.type || "application/octet-stream", cloud: cloud })
  });
  if (!start.ok) throw new Error(`Failed to initialize multipart upload on ${cloud}`);
  const startData = await start.json();

  // GCP: POST to the signed RESUMABLE URL to initiate the session.
  if (cloud === "GCP") {
    const initRes = await fetch(startData.upload_url, {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Goog-Resumable": "start",
        "Content-Length": "0",
      },
    });
    if (!initRes.ok) throw new Error(`GCP session init failed: ${initRes.status}`);
    startData.upload_url = initRes.headers.get("Location");
    if (!startData.upload_url) throw new Error("GCP session init returned no Location header");
  }

  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  const bytesUploadedPerChunk = new Array(totalChunks).fill(0);

  function onChunkProgress(chunkIndex, bytesLoaded) {
    bytesUploadedPerChunk[chunkIndex] = bytesLoaded;
    const totalUploaded = bytesUploadedPerChunk.reduce((a, b) => a + b, 0);
    const percent = Math.min(99, Math.round((totalUploaded / file.size) * 100));
    if (progressEl) progressEl.style.width = percent + "%";
    if (statusText) statusText.innerText = `Uploading… ${percent}%`;
  }

  const parts = [];
  const concurrency = (cloud === "GCP") ? 1 : MAX_PARALLEL_UPLOADS;

  for (let i = 0; i < totalChunks; i += concurrency) {
    const batch = [];
    for (let j = i; j < i + concurrency && j < totalChunks; j++) {
      batch.push(uploadChunkWithRetry(file, cloud, startData, j, onChunkProgress));
    }
    const results = await Promise.all(batch);
    parts.push(...results);
    await sleep(BREATHING_DELAY);
  }

  if (cloud === "AWS") {
    const completeRes = await fetch(`${API_BASE_URL}/files/multipart/complete/`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ cloud, key: startData.key, upload_id: startData.upload_id, parts })
    });
    if (!completeRes.ok) throw new Error("AWS multipart complete failed");
    lastUploadMeta.aws_path = startData.key;
  }

  if (cloud === "AZURE") {
    const completeRes = await fetch(`${API_BASE_URL}/files/multipart/complete/`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ cloud, blob_name: startData.blob_name, blocks: parts.map(p => p.block_id) })
    });
    if (!completeRes.ok) throw new Error("Azure block commit failed");
    lastUploadMeta.azure_path = startData.blob_name;
  }

  if (cloud === "GCP") {
    lastUploadMeta.gcp_path = startData.blob_name;
  }

  if (progressEl) {
    progressEl.style.width = "100%";
    progressEl.classList.remove("progress-bar-animated");
    progressEl.classList.add("bg-success");
  }
  if (statusText) statusText.innerText = "Uploaded 100%";
}


/* ===============================
   UPLOAD CHUNK WITH RETRY
================================ */
async function uploadChunkWithRetry(file, cloud, startData, index, onProgress) {
  let lastError;
  for (let attempt = 1; attempt <= MAX_CHUNK_RETRIES; attempt++) {
    try {
      return await uploadChunk(file, cloud, startData, index, onProgress);
    } catch (err) {
      lastError = err;
      if (attempt < MAX_CHUNK_RETRIES) {
        const delay = RETRY_BASE_DELAY_MS * Math.pow(2, attempt - 1);
        console.warn(`Chunk ${index + 1} failed (attempt ${attempt}/${MAX_CHUNK_RETRIES}): ${err}. Retrying in ${delay / 1000}s…`);
        if (onProgress) onProgress(index, 0);
        await sleep(delay);
      }
    }
  }
  console.error(`Chunk ${index + 1} permanently failed after ${MAX_CHUNK_RETRIES} attempts: ${lastError}`);
  throw new Error(`Chunk ${index + 1} failed after ${MAX_CHUNK_RETRIES} attempts`);
}


/* ===============================
   UPLOAD CHUNK
================================ */
function uploadChunk(file, cloud, startData, index, onProgress) {
  return new Promise(async (resolve, reject) => {
    try {
      const start = index * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);

      let payload;
      let blockId = null;

      if (cloud === "AWS") {
        payload = { cloud, key: startData.key, upload_id: startData.upload_id, part_number: index + 1 };
      }

      if (cloud === "AZURE") {
        blockId = btoa(String(index + 1).padStart(6, "0"));
        payload = { cloud, blob_name: startData.blob_name, block_id: blockId };
      }

      if (cloud === "GCP") {
        const sessionUri = startData.upload_url;
        const fileSize = file.size;
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", sessionUri, true);
        xhr.setRequestHeader("Content-Type", "application/octet-stream");
        xhr.setRequestHeader("Content-Range", `bytes ${start}-${end - 1}/${fileSize}`);
        xhr.upload.onprogress = e => {
          if (e.lengthComputable && onProgress) onProgress(index, e.loaded);
        };
        xhr.onload = () => {
          if (xhr.status === 200 || xhr.status === 201 || xhr.status === 308) {
            if (onProgress) onProgress(index, end - start);
            resolve({ part_number: index + 1 });
          } else {
            reject(`GCP HTTP ${xhr.status} on chunk ${index + 1}`);
          }
        };
        xhr.onerror = () => reject(`GCP connection reset on chunk ${index + 1}`);
        xhr.send(chunk);
        return;
      }

      const presign = await fetch(`${API_BASE_URL}/files/multipart/presign-part/`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload)
      });
      const presignData = await presign.json();

      if (!presignData.url) { reject("Failed to generate upload URL"); return; }

      const xhr = new XMLHttpRequest();
      xhr.open("PUT", presignData.url, true);

      xhr.upload.onprogress = e => {
        if (e.lengthComputable && onProgress) onProgress(index, e.loaded);
      };

      xhr.onload = () => {
        if (xhr.status === 200 || xhr.status === 201) {
          if (onProgress) onProgress(index, end - start);
          const etag = xhr.getResponseHeader("ETag");
          if (cloud === "AWS") resolve({ ETag: etag, PartNumber: index + 1 });
          if (cloud === "AZURE") resolve({ block_id: blockId });
        } else {
          reject(`HTTP ${xhr.status} on chunk ${index + 1}`);
        }
      };

      xhr.onerror = () => reject(`Connection reset on chunk ${index + 1}`);
      xhr.send(chunk);

    } catch (err) {
      reject(err);
    }
  });
}


/* ===============================
   CONFIRM UPLOAD
================================ */
function confirmUpload(successClouds, targetContainer) {
  const payload = {
    file_name: lastUploadMeta.file_name,
    file_size: lastUploadMeta.file_size
  };
  if (successClouds.includes("AWS")) payload.aws_path = lastUploadMeta.aws_path;
  if (successClouds.includes("AZURE")) payload.azure_path = lastUploadMeta.azure_path;
  if (successClouds.includes("GCP")) payload.gcp_path = lastUploadMeta.gcp_path;

  return fetch(`${API_BASE_URL}/files/confirm-upload/`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload)
  })
    .then(res => {
      if (!res.ok) throw new Error("Failed to confirm file registration in database");
      return res.json();
    })
    .then(data => {
      if (typeof loadFiles === "function") loadFiles();
      if (typeof loadRecentFiles === "function") loadRecentFiles();
      if (typeof loadFolders === "function") loadFolders();
      if (typeof loadStorageSummary === "function") loadStorageSummary();
      resetUploadForm();
      const statusCont = targetContainer || document.getElementById("upload-status-container");
      if (statusCont) {
        statusCont.innerHTML = `<div class="alert alert-success py-2"><strong>Success!</strong> File uploaded and registered across: ${successClouds.join(", ")}</div>`;
      }
      setUploadButton(false, "Upload");
      return data;
    })
    .catch(err => {
      console.error("Confirm upload error:", err);
      alert("Upload verification failed");
      setUploadButton(false, "Upload");
      throw err;
    });
}


/* ===============================
   SLEEP
================================ */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
