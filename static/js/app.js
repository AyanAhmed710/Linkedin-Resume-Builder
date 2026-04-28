/* ═══════════════════════════════════════════════════════════════════════
   ResumeForge AI — Frontend Logic
   ═══════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    // ── DOM refs ────────────────────────────────────────────────────────
    const $ = (s, p = document) => p.querySelector(s);
    const $$ = (s, p = document) => [...p.querySelectorAll(s)];

    const tabBtns = $$(".tab-btn");
    const tabSlider = $("#tab-slider");
    const panels = $$(".tab-panel");

    // scraper
    const inpKeyword = $("#inp-keyword");
    const inpCountries = $("#inp-countries");
    const inpCount = $("#inp-count");
    const inpDate = $("#inp-date");
    const btnScrape = $("#btn-scrape");
    const scraperTerm = $("#scraper-term");
    const scraperResult = $("#scraper-result");
    const scraperBody = $("#scraper-result-body");

    // generator
    const dropZone = $("#drop-zone");
    const fileInput = $("#file-input");
    const browseBtn = $("#browse-btn");
    const uploadInfo = $("#upload-info");
    const fileNameEl = $("#file-name");
    const fileRemove = $("#file-remove");
    const csvPreview = $("#csv-preview-card");
    const csvRowCount = $("#csv-row-count");
    const csvThead = $("#csv-thead");
    const csvTbody = $("#csv-tbody");
    const genBar = $("#generate-bar");
    const btnGenerate = $("#btn-generate");
    const genTermCard = $("#gen-terminal-card");
    const genTerm = $("#gen-term");
    const pdfResultCard = $("#pdf-result-card");
    const pdfList = $("#pdf-list");

    let uploadedFilename = null;

    // ── Toast ───────────────────────────────────────────────────────────
    function toast(msg, type = "info") {
        const el = document.createElement("div");
        el.className = `toast ${type}`;
        el.textContent = msg;
        $("#toast-container").appendChild(el);
        setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 4000);
    }

    // ── Tabs ────────────────────────────────────────────────────────────
    function positionSlider(btn) {
        tabSlider.style.width = btn.offsetWidth + "px";
        tabSlider.style.transform = `translateX(${btn.offsetLeft - btn.parentElement.getBoundingClientRect().left + btn.parentElement.scrollLeft - 4}px)`;
    }

    function switchTab(name) {
        tabBtns.forEach(b => b.classList.toggle("active", b.dataset.tab === name));
        panels.forEach(p => {
            p.classList.toggle("active", p.id === `panel-${name}`);
        });
        const activeBtn = tabBtns.find(b => b.dataset.tab === name);
        if (activeBtn) positionSlider(activeBtn);
    }

    tabBtns.forEach(btn => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));
    // initial slider position
    requestAnimationFrame(() => {
        const active = tabBtns.find(b => b.classList.contains("active"));
        if (active) positionSlider(active);
    });
    window.addEventListener("resize", () => {
        const active = tabBtns.find(b => b.classList.contains("active"));
        if (active) positionSlider(active);
    });

    // ── Terminal helpers ────────────────────────────────────────────────
    function termClear(term) {
        term.innerHTML = "";
    }

    function termAppend(term, msg) {
        const div = document.createElement("div");
        div.className = "term-line";
        div.innerHTML = `<span class="prompt">❯</span> ${escapeHtml(msg)}`;
        term.appendChild(div);
        term.scrollTop = term.scrollHeight;
    }

    function escapeHtml(s) {
        const d = document.createElement("div");
        d.textContent = s;
        return d.innerHTML;
    }

    // ── SSE log streamer ────────────────────────────────────────────────
    function streamLogs(taskId, term, onDone) {
        const es = new EventSource(`/api/logs/${taskId}`);
        es.onmessage = (ev) => {
            const data = JSON.parse(ev.data);
            if (data.type === "log") {
                termAppend(term, data.message);
            } else if (data.type === "status") {
                es.close();
                if (onDone) onDone(data.status, data.result);
            }
        };
        es.onerror = () => {
            es.close();
            termAppend(term, "⚠️ Connection to server lost.");
            if (onDone) onDone("failed", null);
        };
    }

    // ── Button state helpers ────────────────────────────────────────────
    function btnLoading(btn, loading) {
        const content = $(".btn-content", btn);
        const loader = $(".btn-loader", btn);
        if (loading) {
            content.classList.add("hidden");
            loader.classList.remove("hidden");
            btn.disabled = true;
        } else {
            content.classList.remove("hidden");
            loader.classList.add("hidden");
            btn.disabled = false;
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // SCRAPER
    // ═════════════════════════════════════════════════════════════════════
    btnScrape.addEventListener("click", async () => {
        const keyword = inpKeyword.value.trim();
        const countries = inpCountries.value.split(",").map(c => c.trim()).filter(Boolean);
        const count = parseInt(inpCount.value, 10) || 5;
        const datep = inpDate.value;

        if (!keyword) { toast("Please enter a search keyword.", "error"); return; }
        if (!countries.length) { toast("Please enter at least one country.", "error"); return; }

        btnLoading(btnScrape, true);
        scraperResult.classList.add("hidden");
        termClear(scraperTerm);
        termAppend(scraperTerm, `Starting scrape: "${keyword}" in ${countries.join(", ")} (${count}/country, ${datep})…`);

        try {
            const res = await fetch("/api/scrape", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    search_keyword: keyword,
                    countries: countries,
                    jobs_per_country: count,
                    date_posted: datep,
                }),
            });
            const { task_id } = await res.json();

            streamLogs(task_id, scraperTerm, (status, result) => {
                btnLoading(btnScrape, false);
                if (status === "completed" && result) {
                    toast("Scraping completed! CSV ready.", "success");
                    scraperResult.classList.remove("hidden");
                    scraperBody.innerHTML = `
            <div class="dl-chip">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              ${escapeHtml(result)}
            </div>
            <button class="dl-btn" onclick="window.open('/api/download/${encodeURIComponent(result)}')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Download CSV
            </button>
          `;
                } else {
                    toast("Scraping failed. Check terminal for details.", "error");
                }
            });
        } catch (err) {
            btnLoading(btnScrape, false);
            toast("Failed to start scraper: " + err.message, "error");
        }
    });

    // ═════════════════════════════════════════════════════════════════════
    // FILE UPLOAD (drag-drop + browse)
    // ═════════════════════════════════════════════════════════════════════
    browseBtn.addEventListener("click", (e) => { e.stopPropagation(); fileInput.click(); });
    dropZone.addEventListener("click", () => fileInput.click());

    ["dragenter", "dragover"].forEach(ev =>
        dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); })
    );
    ["dragleave", "drop"].forEach(ev =>
        dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.remove("drag-over"); })
    );

    dropZone.addEventListener("drop", (e) => {
        const file = e.dataTransfer.files[0];
        if (file && file.name.endsWith(".csv")) handleFile(file);
        else toast("Please drop a .csv file.", "error");
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files[0]) handleFile(fileInput.files[0]);
    });

    fileRemove.addEventListener("click", () => {
        uploadedFilename = null;
        uploadInfo.classList.add("hidden");
        dropZone.style.display = "";
        csvPreview.classList.add("hidden");
        genBar.classList.add("hidden");
        fileInput.value = "";
    });

    async function handleFile(file) {
        const fd = new FormData();
        fd.append("file", file);

        try {
            const res = await fetch("/api/upload-csv", { method: "POST", body: fd });
            const data = await res.json();
            uploadedFilename = data.filename;

            fileNameEl.textContent = file.name;
            uploadInfo.classList.remove("hidden");
            dropZone.style.display = "none";

            toast(`Uploaded: ${file.name}`, "success");
            loadPreview(uploadedFilename);
        } catch (err) {
            toast("Upload failed: " + err.message, "error");
        }
    }

    async function loadPreview(filename) {
        try {
            const res = await fetch(`/api/csv/preview/${encodeURIComponent(filename)}`);
            const { columns, rows, total } = await res.json();

            csvRowCount.textContent = `${total} jobs`;

            // Only show relevant columns in a readable way
            const displayCols = columns.filter(c => c !== "job_description");

            csvThead.innerHTML = "<tr>" + displayCols.map(c =>
                `<th>${escapeHtml(c)}</th>`
            ).join("") + "</tr>";

            csvTbody.innerHTML = rows.map(r =>
                "<tr>" + displayCols.map(c => {
                    let val = String(r[c] || "—");
                    if (c === "job_url" && val.startsWith("http")) {
                        val = `<a href="${val}" target="_blank" style="color:var(--cyan);text-decoration:none">🔗 Link</a>`;
                        return `<td>${val}</td>`;
                    }
                    if (val.length > 60) val = val.substring(0, 57) + "…";
                    return `<td title="${escapeHtml(String(r[c] || ""))}">${escapeHtml(val)}</td>`;
                }).join("") + "</tr>"
            ).join("");

            csvPreview.classList.remove("hidden");
            genBar.classList.remove("hidden");
        } catch (err) {
            toast("Could not preview CSV: " + err.message, "error");
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // RESUME GENERATOR
    // ═════════════════════════════════════════════════════════════════════
    btnGenerate.addEventListener("click", async () => {
        if (!uploadedFilename) {
            toast("Please upload a CSV file first.", "error");
            return;
        }

        btnLoading(btnGenerate, true);
        genTermCard.classList.remove("hidden");
        pdfResultCard.classList.add("hidden");
        termClear(genTerm);
        termAppend(genTerm, `Starting resume generation for: ${uploadedFilename}…`);

        try {
            const res = await fetch("/api/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ csv_filename: uploadedFilename }),
            });
            const { task_id } = await res.json();

            streamLogs(task_id, genTerm, (status, result) => {
                btnLoading(btnGenerate, false);
                if (status === "completed" && result && result.length) {
                    toast(`Generated ${result.length} resume(s)!`, "success");
                    showPdfs(result);
                } else if (status === "completed") {
                    toast("Completed but no resumes generated.", "info");
                } else {
                    toast("Generation failed. Check logs.", "error");
                }
            });
        } catch (err) {
            btnLoading(btnGenerate, false);
            toast("Failed to start generation: " + err.message, "error");
        }
    });

    function showPdfs(filenames) {
        pdfResultCard.classList.remove("hidden");
        pdfList.innerHTML = `<div class="pdf-grid">${filenames.map(f => `
      <div class="pdf-item">
        <div class="pdf-item-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div class="pdf-item-info">
          <div class="pdf-item-name">${escapeHtml(f)}</div>
          <div class="pdf-item-size">Tailored Resume</div>
        </div>
        <button class="btn-sm" onclick="window.open('/api/download/${encodeURIComponent(f)}')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Download
        </button>
      </div>
    `).join("")}</div>`;
    }

    // ── fetch existing PDFs on load ─────────────────────────────────────
    (async () => {
        try {
            const res = await fetch("/api/files/pdf");
            const files = await res.json();
            if (files.length) showPdfs(files.map(f => f.filename));
        } catch { }  // silently fail
    })();

})();
