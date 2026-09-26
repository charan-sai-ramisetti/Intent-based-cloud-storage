/* ==========================================================================
   INTENT-DRIVEN STORAGE OPTIMIZATION UI CONTROLLER
   TriCloud Vault - LLM + MILP Optimization Interface
   ========================================================================== */

let currentIntentLogId = null;
let currentOptimizationResult = null;

/**
 * Handle user submitting natural language storage intent.
 */
async function submitStorageIntent() {
  const intentInput = document.getElementById("intent-text-input");
  const intentFile = document.getElementById("intentFileInput");
  const intentBtn = document.getElementById("parse-intent-btn");
  const statusDiv = document.getElementById("intent-status-message");
  const resultCard = document.getElementById("intent-result-card");

  if (!intentInput || !intentInput.value.trim()) {
    alert("Please describe your storage requirements (e.g., 'Store my backup with 2 copies under $5/mo')");
    return;
  }

  // Determine file size
  let fileSizeBytes = 104857600; // Default 100MB if no file selected
  let fileName = "unnamed_file";
  let fileType = "application/octet-stream";

  if (intentFile && intentFile.files.length > 0) {
    const file = intentFile.files[0];
    fileSizeBytes = file.size;
    fileName = file.name;
    fileType = file.type || "application/octet-stream";
  }

  // Update UI to loading state
  intentBtn.disabled = true;
  intentBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Analyzing & Optimizing...`;
  statusDiv.innerHTML = `<div class="alert alert-info py-2">Parsing semantic intent with LLM and solving MILP optimization model...</div>`;
  resultCard.classList.add("d-none");

  try {
    const response = await fetch(`${API_BASE_URL}/intent/parse/`, {
      method: "POST",
      headers: {
        ...authHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_text: intentInput.value.trim(),
        file_size_bytes: fileSizeBytes,
        file_name: fileName,
        file_type: fileType,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Failed to process intent");
    }

    currentIntentLogId = data.intent_log_id;
    currentOptimizationResult = data;

    renderOptimizationResults(data);
    statusDiv.innerHTML = "";
    resultCard.classList.remove("d-none");

  } catch (err) {
    console.error("Intent parsing error:", err);
    statusDiv.innerHTML = `<div class="alert alert-danger py-2">Error: ${err.message}</div>`;
  } finally {
    intentBtn.disabled = false;
    intentBtn.innerHTML = "Optimize Placement";
  }
}

/**
 * Render the parsed constraints, MILP recommendation, and baseline comparison.
 */
function renderOptimizationResults(data) {
  const constraints = data.parsed_constraints;
  const rec = data.recommendation;
  const baselines = data.baselines_comparison;
  const meta = data.meta;

  // 1. Render Parsed Constraints
  const constraintsBadgeContainer = document.getElementById("parsed-constraints-badges");
  if (constraintsBadgeContainer) {
    constraintsBadgeContainer.innerHTML = `
      <span class="badge bg-secondary me-1 mb-1">Goal: ${constraints.primary_goal}</span>
      <span class="badge bg-secondary me-1 mb-1">Replicas: ${constraints.redundancy_level}</span>
      <span class="badge bg-secondary me-1 mb-1">Access: ${constraints.access_pattern}</span>
      ${constraints.max_budget_monthly_usd ? `<span class="badge bg-secondary me-1 mb-1">Budget: $${constraints.max_budget_monthly_usd}/mo</span>` : ""}
      ${constraints.max_latency_ms ? `<span class="badge bg-secondary me-1 mb-1">Max SLA: ${constraints.max_latency_ms}ms</span>` : ""}
      ${constraints.geo_restriction ? `<span class="badge bg-secondary me-1 mb-1">Geo: ${constraints.geo_restriction.join(", ")}</span>` : ""}
    `;
  }

  // 2. Render MILP Optimal Recommendation
  const cloudsContainer = document.getElementById("optimal-clouds-list");
  if (cloudsContainer) {
    cloudsContainer.innerHTML = rec.selected_clouds.map(cloud => {
      const tier = rec.selected_tiers[cloud] || "standard";
      const cost = rec.cost_breakdown[`${cloud}_${tier}`] || 0;
      return `
        <div class="d-flex justify-content-between align-items-center border rounded p-2 mb-2 bg-light">
          <div>
            <strong>${cloud}</strong> <span class="badge bg-info text-dark ms-1">${tier}</span>
          </div>
          <span class="text-success fw-semibold">$${cost.toFixed(4)}/mo</span>
        </div>
      `;
    }).join("");
  }

  // 3. Render Metrics
  document.getElementById("optimal-total-cost").innerText = `$${rec.estimated_monthly_cost_usd.toFixed(4)}/mo`;
  document.getElementById("optimal-latency").innerText = `${rec.estimated_latency_ms.toFixed(1)} ms`;
  document.getElementById("optimal-durability").innerText = `${rec.durability_achieved.toFixed(9)}%`;
  document.getElementById("optimal-reasoning").innerText = rec.reasoning;

  // 4. Render Telemetry Metadata
  document.getElementById("optimization-telemetry").innerText =
    `LLM: ${meta.llm_provider} (${meta.parse_latency_ms}ms) | MILP Solver: ${meta.optimization_latency_ms}ms | Confidence: ${(meta.confidence_score * 100).toFixed(0)}%`;

  // 5. Render Baseline Comparisons Table
  const baselineTable = document.getElementById("baseline-comparison-tbody");
  if (baselineTable && baselines) {
    let baselineRows = `
      <tr class="table-success fw-semibold">
        <td>MILP Optimal (Vault)</td>
        <td>${rec.selected_clouds.join(", ")}</td>
        <td>$${rec.estimated_monthly_cost_usd.toFixed(4)}</td>
        <td>${rec.estimated_latency_ms.toFixed(1)} ms</td>
        <td><span class="badge bg-success">Baseline Benchmark</span></td>
      </tr>
    `;

    for (const [name, bRec] of Object.entries(baselines)) {
      const costDiff = bRec.estimated_monthly_cost_usd - rec.estimated_monthly_cost_usd;
      const savingsPct = bRec.estimated_monthly_cost_usd > 0 ? (costDiff / bRec.estimated_monthly_cost_usd * 100).toFixed(1) : "0";

      const readableName = {
        single_cloud_aws: "Single Cloud (AWS S3)",
        greedy_cheapest: "Greedy (Cheapest Tier)",
        round_robin: "Round Robin (3 Clouds)",
        random: "Random Allocation"
      }[name] || name;

      baselineRows += `
        <tr>
          <td>${readableName}</td>
          <td>${bRec.selected_clouds.join(", ")}</td>
          <td>$${bRec.estimated_monthly_cost_usd.toFixed(4)}</td>
          <td>${bRec.estimated_latency_ms.toFixed(1)} ms</td>
          <td>
            ${costDiff > 0 ? `<span class="badge bg-warning text-dark">+${savingsPct}% Cost</span>` : `<span class="badge bg-secondary">Same</span>`}
          </td>
        </tr>
      `;
    }
    baselineTable.innerHTML = baselineRows;
  }
}

/**
 * Execute the optimized upload using presigned direct-to-cloud streams and DB registration.
 */
async function executeOptimizedUpload() {
  if (!currentOptimizationResult || !currentOptimizationResult.recommendation) {
    alert("Please parse and optimize your storage intent first.");
    return;
  }

  const intentFile = document.getElementById("intentFileInput");
  if (!intentFile || intentFile.files.length === 0) {
    alert("Please choose a file to upload in the file input next to the intent prompt.");
    return;
  }

  const file = intentFile.files[0];
  const execBtn = document.getElementById("execute-upload-btn");
  const execStatus = document.getElementById("execution-status-message");
  const selectedClouds = currentOptimizationResult.recommendation.selected_clouds;

  if (!selectedClouds || selectedClouds.length === 0) {
    alert("No cloud targets found in optimization recommendation.");
    return;
  }

  execBtn.disabled = true;
  execBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Replicating to ${selectedClouds.join(", ")}...`;
  execStatus.innerHTML = `<div class="alert alert-info py-2">Streaming file directly to ${selectedClouds.join(", ")} presigned endpoints...</div>`;

  try {
    // Audit execution notification
    if (currentIntentLogId) {
      fetch(`${API_BASE_URL}/intent/execute-upload/`, {
        method: "POST",
        headers: {
          ...authHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          intent_log_id: currentIntentLogId,
          file_name: file.name,
          file_size_bytes: file.size,
          file_type: file.type || "application/octet-stream",
        }),
      }).catch(err => console.warn("Audit execution notice:", err));
    }

    // Direct browser-to-cloud upload to selected targets followed by DB confirmation
    await startDirectUpload(file, selectedClouds, execStatus);

    if (typeof loadFiles === "function") loadFiles();
    if (typeof loadRecentFiles === "function") loadRecentFiles();
    if (typeof loadFolders === "function") loadFolders();
    if (typeof loadStorageSummary === "function") loadStorageSummary();

  } catch (err) {
    console.error("Execute upload error:", err);
    execStatus.innerHTML = `<div class="alert alert-danger py-2">Execution Error: ${err.message || err}</div>`;
  } finally {
    execBtn.disabled = false;
    execBtn.innerHTML = "Execute Multi-Cloud Placement";
  }
}
