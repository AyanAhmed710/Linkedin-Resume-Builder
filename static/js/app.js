/* ═══════════════════════════════════════════════════════════════════════
   ResumeForge AI — Frontend Logic
   ═══════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    if (typeof pdfjsLib !== "undefined") {
        pdfjsLib.GlobalWorkerOptions.workerSrc =
            "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
    }

    // ── DOM refs ────────────────────────────────────────────────────────
    const $ = (s, p = document) => p.querySelector(s);
    const $$ = (s, p = document) => [...p.querySelectorAll(s)];

    const tabBtns   = $$(".tab-btn");
    const tabSlider = $("#tab-slider");
    const panels    = $$(".tab-panel");

    // scraper
    const inpEmail    = $("#inp-email");
    const inpPassword = $("#inp-password");
    const inpKeyword  = $("#inp-keyword");
    const inpCountries = $("#inp-countries");
    const inpCount    = $("#inp-count");
    const inpDate     = $("#inp-date");
    const btnScrape   = $("#btn-scrape");
    const scraperTerm = $("#scraper-term");
    const scraperResult = $("#scraper-result");
    const scraperBody = $("#scraper-result-body");

    // generator — job file
    const dropZone      = $("#drop-zone");
    const fileInput     = $("#file-input");
    const uploadInfo    = $("#upload-info");
    const fileNameEl    = $("#file-name");
    const fileRemove    = $("#file-remove");
    const csvPreview    = $("#csv-preview-card");
    const csvRowCount   = $("#csv-row-count");
    const csvThead      = $("#csv-thead");
    const csvTbody      = $("#csv-tbody");
    const genBar        = $("#generate-bar");
    const btnGenerate   = $("#btn-generate");
    const genTermCard   = $("#gen-terminal-card");
    const genTerm       = $("#gen-term");
    const pdfResultCard = $("#pdf-result-card");
    const pdfList       = $("#pdf-list");

    // generator — profile txt
    const profileDropZone   = $("#profile-drop-zone");
    const profileFileInput  = $("#profile-file-input");
    const profileUploadInfo = $("#profile-upload-info");
    const profileFileName   = $("#profile-file-name");
    const profileFileRemove = $("#profile-file-remove");

    // generator — user resume pdf
    const resumeDropZone   = $("#resume-drop-zone");
    const resumeFileInput  = $("#resume-file-input");
    const resumeUploadInfo = $("#resume-upload-info");
    const resumeFileName   = $("#resume-file-name");
    const resumeFileRemove = $("#resume-file-remove");

    let uploadedFilename = null;
    let profileFilename  = null;
    let resumeFilename   = null;


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
        panels.forEach(p => p.classList.toggle("active", p.id === `panel-${name}`));
        const activeBtn = tabBtns.find(b => b.dataset.tab === name);
        if (activeBtn) positionSlider(activeBtn);
    }

    tabBtns.forEach(btn => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));
    requestAnimationFrame(() => {
        const active = tabBtns.find(b => b.classList.contains("active"));
        if (active) positionSlider(active);
    });
    window.addEventListener("resize", () => {
        const active = tabBtns.find(b => b.classList.contains("active"));
        if (active) positionSlider(active);
    });

    // ── Terminal helpers ────────────────────────────────────────────────
    function termClear(term) { term.innerHTML = ""; }

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

    // ── Verification modal ──────────────────────────────────────────────
    const verificationModal = $("#verification-modal");
    const verificationInput = $("#verification-code-input");
    const btnSubmitVerification = $("#btn-submit-verification");
    let _verificationTaskId = null;

    function showVerificationModal(taskId) {
        _verificationTaskId = taskId;
        verificationInput.value = "";
        verificationModal.classList.remove("hidden");
        verificationInput.focus();
    }

    btnSubmitVerification.addEventListener("click", async () => {
        const code = verificationInput.value.trim();
        if (!code) { toast("Please enter the verification code.", "error"); return; }
        btnLoading(btnSubmitVerification, true);
        try {
            await fetch(`/api/task/${_verificationTaskId}/verification`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code }),
            });
            verificationModal.classList.add("hidden");
            toast("Code submitted — scraper is continuing…", "success");
        } catch (err) {
            toast("Failed to submit code: " + err.message, "error");
        }
        btnLoading(btnSubmitVerification, false);
    });

    verificationInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") btnSubmitVerification.click();
    });

    // ── SSE log streamer ────────────────────────────────────────────────
    function streamLogs(taskId, term, onDone) {
        const es = new EventSource(`/api/logs/${taskId}`);
        es.onmessage = (ev) => {
            const data = JSON.parse(ev.data);
            if (data.type === "log") {
                if (data.message.includes("VERIFICATION_REQUIRED")) {
                    showVerificationModal(taskId);
                }
                termAppend(term, data.message);
            } else if (data.type === "status") {
                es.close();
                verificationModal.classList.add("hidden");
                if (onDone) onDone(data.status, data.result);
            }
        };
        es.onerror = () => {
            es.close();
            verificationModal.classList.add("hidden");
            termAppend(term, "⚠️ Connection to server lost.");
            if (onDone) onDone("failed", null);
        };
    }

    // ── Button state helpers ────────────────────────────────────────────
    function btnLoading(btn, loading) {
        const content = $(".btn-content", btn);
        const loader  = $(".btn-loader", btn);
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

    // ── Drop zone helper ────────────────────────────────────────────────
    function setupDrop(zone, onDrop) {
        ["dragenter", "dragover"].forEach(ev =>
            zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("drag-over"); })
        );
        ["dragleave", "drop"].forEach(ev =>
            zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("drag-over"); })
        );
        zone.addEventListener("drop", (e) => {
            const file = e.dataTransfer.files[0];
            if (file) onDrop(file);
        });
    }

    // ═════════════════════════════════════════════════════════════════════
    // SCRAPER
    // ═════════════════════════════════════════════════════════════════════
    btnScrape.addEventListener("click", async () => {
        const email     = inpEmail.value.trim();
        const password  = inpPassword.value;
        const keyword   = inpKeyword.value.trim();
        const countries = inpCountries.value.split(",").map(c => c.trim()).filter(Boolean);
        const count     = parseInt(inpCount.value, 10) || 5;
        const datep     = inpDate.value;

        if (!email)           { toast("Please enter your LinkedIn email.", "error"); return; }
        if (!password)        { toast("Please enter your LinkedIn password.", "error"); return; }
        if (!keyword)         { toast("Please enter a search keyword.", "error"); return; }
        if (!countries.length){ toast("Please enter at least one country.", "error"); return; }

        btnLoading(btnScrape, true);
        scraperResult.classList.add("hidden");
        termClear(scraperTerm);
        termAppend(scraperTerm, `Starting scrape: "${keyword}" in ${countries.join(", ")} (${count}/country, ${datep})…`);

        try {
            const res = await fetch("/api/scrape", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ search_keyword: keyword, countries, jobs_per_country: count, date_posted: datep, email, password }),
            });
            const { task_id } = await res.json();

            streamLogs(task_id, scraperTerm, (status, result) => {
                btnLoading(btnScrape, false);
                if (status === "completed" && result) {
                    toast("Scraping completed! File ready.", "success");
                    scraperResult.classList.remove("hidden");
                    scraperBody.innerHTML = `
                        <div class="dl-chip">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                          ${escapeHtml(result)}
                        </div>
                        <button class="dl-btn" onclick="window.open('/api/download/${encodeURIComponent(result)}')">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                          Download
                        </button>`;
                } else {
                    toast("Scraping failed. Check terminal for details.", "error");
                }
            });
        } catch (err) {
            btnLoading(btnScrape, false);
            toast("Failed to start scraper: " + err.message, "error");
        }
    });

    // ── Upload status checklist ─────────────────────────────────────────
    function updateUploadStatus() {
        // Count from JS variables — never depends on DOM elements existing
        const count = (profileFilename ? 1 : 0) + (uploadedFilename ? 1 : 0) + (resumeFilename ? 1 : 0);

        // Generate bar
        if (count === 3) {
            genBar.classList.remove("hidden");
        } else {
            genBar.classList.add("hidden");
        }

        // Card glow
        document.getElementById("profile-card")?.classList.toggle("card-loaded", !!profileFilename);
        document.getElementById("upload-card")?.classList.toggle("card-loaded", !!uploadedFilename);
        document.getElementById("resume-upload-card")?.classList.toggle("card-loaded", !!resumeFilename);

        // Checklist items (best-effort — elements may not exist in cached HTML)
        function setCheck(itemId, circleId, detailId, filename, emptyMsg) {
            const item = document.getElementById(itemId);
            if (!item) return;
            item.classList.toggle("ready", !!filename);
            const circle = document.getElementById(circleId);
            const detail = document.getElementById(detailId);
            if (circle) circle.textContent = filename ? "✓" : "";
            if (detail) detail.textContent = filename || emptyMsg;
        }

        setCheck("check-profile", "check-circle-profile", "check-detail-profile",
            profileFilename,  'Not uploaded — drop a .txt file in "Your Profile" above');
        setCheck("check-csv",     "check-circle-csv",     "check-detail-csv",
            uploadedFilename, 'Not uploaded — drop a .csv file in "Job File" above');
        setCheck("check-resume",  "check-circle-resume",  "check-detail-resume",
            resumeFilename,   'Not uploaded — drop a .pdf file in "Your Resume" above');

        const badge = document.getElementById("files-ready-badge");
        if (badge) {
            badge.textContent = `${count} / 3`;
            badge.className = count === 3 ? "badge badge-green" : "badge badge-cyan";
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // PROFILE TXT UPLOAD
    // ═════════════════════════════════════════════════════════════════════
    profileFileInput.addEventListener("change", () => {
        if (profileFileInput.files[0]) handleProfileFile(profileFileInput.files[0]);
    });
    setupDrop(profileDropZone, (file) => {
        if (file.name.endsWith(".txt")) handleProfileFile(file);
        else toast("Please drop a .txt file.", "error");
    });
    profileFileRemove.addEventListener("click", () => {
        profileFilename = null;
        profileUploadInfo.classList.add("hidden");
        profileDropZone.style.display = "";
        profileFileInput.value = "";
        updateUploadStatus();
    });

    async function handleProfileFile(file) {
        const fd = new FormData();
        fd.append("file", file);
        try {
            const res  = await fetch("/api/upload-profile", { method: "POST", body: fd });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Server error ${res.status}`);
            }
            const data = await res.json();
            profileFilename = data.filename;
            profileFileName.textContent = file.name;
            profileUploadInfo.classList.remove("hidden");
            profileDropZone.style.display = "none";
            toast(`Profile loaded: ${file.name}`, "success");
            updateUploadStatus();
        } catch (err) {
            toast("Profile upload failed: " + err.message, "error");
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // JOB FILE UPLOAD (CSV / XLSX)
    // ═════════════════════════════════════════════════════════════════════
    fileInput.addEventListener("change", () => {
        if (fileInput.files[0]) handleFile(fileInput.files[0]);
    });
    setupDrop(dropZone, (file) => {
        const ok = [".csv", ".xlsx", ".xls"].some(ext => file.name.toLowerCase().endsWith(ext));
        if (ok) handleFile(file);
        else toast("Please drop a .csv or .xlsx file.", "error");
    });
    fileRemove.addEventListener("click", () => {
        uploadedFilename = null;
        uploadInfo.classList.add("hidden");
        dropZone.style.display = "";
        csvPreview.classList.add("hidden");
        fileInput.value = "";
        updateUploadStatus();
    });

    async function handleFile(file) {
        const fd = new FormData();
        fd.append("file", file);
        try {
            const res  = await fetch("/api/upload-csv", { method: "POST", body: fd });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Server error ${res.status}`);
            }
            const data = await res.json();
            uploadedFilename = data.filename;
            fileNameEl.textContent = file.name;
            uploadInfo.classList.remove("hidden");
            dropZone.style.display = "none";
            toast(`Uploaded: ${file.name}`, "success");
            updateUploadStatus();
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
            const displayCols = columns.filter(c => c !== "job_description");
            csvThead.innerHTML = "<tr>" + displayCols.map(c => `<th>${escapeHtml(c)}</th>`).join("") + "</tr>";
            csvTbody.innerHTML = rows.map(r =>
                "<tr>" + displayCols.map(c => {
                    let val = String(r[c] || "—");
                    if (c === "job_url" && val.startsWith("http")) {
                        return `<td><a href="${val}" target="_blank" style="color:var(--cyan);text-decoration:none">🔗 Link</a></td>`;
                    }
                    if (val.length > 60) val = val.substring(0, 57) + "…";
                    return `<td title="${escapeHtml(String(r[c] || ""))}">${escapeHtml(val)}</td>`;
                }).join("") + "</tr>"
            ).join("");
            csvPreview.classList.remove("hidden");
        } catch (err) {
            toast("Could not preview file: " + err.message, "error");
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // USER RESUME PDF UPLOAD
    // ═════════════════════════════════════════════════════════════════════
    resumeFileInput.addEventListener("change", () => {
        if (resumeFileInput.files[0]) handleResumeFile(resumeFileInput.files[0]);
    });
    setupDrop(resumeDropZone, (file) => {
        if (file.name.toLowerCase().endsWith(".pdf")) handleResumeFile(file);
        else toast("Please drop a .pdf file.", "error");
    });
    resumeFileRemove.addEventListener("click", () => {
        resumeFilename = null;
        resumeUploadInfo.classList.add("hidden");
        resumeDropZone.style.display = "";
        resumeFileInput.value = "";
        updateUploadStatus();
    });

    async function handleResumeFile(file) {
        const fd = new FormData();
        fd.append("file", file);
        try {
            const res  = await fetch("/api/upload-resume", { method: "POST", body: fd });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Server error ${res.status}`);
            }
            const data = await res.json();
            resumeFilename = data.filename;
            resumeFileName.textContent = file.name;
            resumeUploadInfo.classList.remove("hidden");
            resumeDropZone.style.display = "none";
            toast(`Resume loaded: ${file.name}`, "success");
            updateUploadStatus();
        } catch (err) {
            toast("Resume upload failed: " + err.message, "error");
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    // GENERATE
    // ═════════════════════════════════════════════════════════════════════
    btnGenerate.addEventListener("click", async () => {
        if (!uploadedFilename) {
            toast("Please upload a jobs CSV file.", "error");
            return;
        }
        if (!profileFilename) {
            toast("Please upload a profile .txt file (Your Profile).", "error");
            return;
        }
        if (!resumeFilename) {
            toast("Please upload your resume PDF.", "error");
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
                body: JSON.stringify({
                    csv_filename:     uploadedFilename,
                    profile_filename: profileFilename  || null,
                    resume_filename:  resumeFilename   || null,
                }),
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

    // ═════════════════════════════════════════════════════════════════════
    // PDF PREVIEW GRID
    // ═════════════════════════════════════════════════════════════════════
    function showPdfs(filenames) {
        pdfResultCard.classList.remove("hidden");
        pdfList.innerHTML = `<div class="pdf-preview-grid">${filenames.map((f, i) => `
          <div class="pdf-preview-card" id="pdf-card-${i}">
            <div class="pdf-canvas-wrap" id="pdf-wrap-${i}">
              <div class="pdf-canvas-placeholder"><div class="pdf-loading-spin"></div></div>
              <div class="pdf-overlay">
                <div class="pdf-overlay-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                </div>
                <span class="pdf-overlay-text">Download</span>
              </div>
            </div>
            <div class="pdf-preview-footer">
              <div class="pdf-preview-name">${escapeHtml(f)}</div>
              <div class="pdf-preview-sub">Tailored Resume · PDF</div>
            </div>
          </div>`).join("")}</div>`;

        filenames.forEach((f, i) => {
            const card = document.getElementById(`pdf-card-${i}`);
            if (card) {
                card.addEventListener("click", () => {
                    const a = document.createElement("a");
                    a.href = "/api/download/" + encodeURIComponent(f);
                    a.download = f;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                });
            }
            const wrap = document.getElementById(`pdf-wrap-${i}`);
            if (wrap) renderPdfThumbnail("/api/download/" + encodeURIComponent(f), wrap);
        });
    }

    async function renderPdfThumbnail(url, wrap) {
        try {
            const pdf  = await pdfjsLib.getDocument(url).promise;
            const page = await pdf.getPage(1);
            const viewport = page.getViewport({ scale: 1 });
            const containerW = wrap.clientWidth || 220;
            const scale = containerW / viewport.width;
            const scaledViewport = page.getViewport({ scale });
            const canvas = document.createElement("canvas");
            canvas.width  = scaledViewport.width;
            canvas.height = scaledViewport.height;
            canvas.style.cssText = "position:absolute;top:0;left:0;width:100%;height:100%";
            await page.render({ canvasContext: canvas.getContext("2d"), viewport: scaledViewport }).promise;
            const placeholder = wrap.querySelector(".pdf-canvas-placeholder");
            if (placeholder) placeholder.replaceWith(canvas);
        } catch {
            const placeholder = wrap.querySelector(".pdf-canvas-placeholder");
            if (placeholder) {
                placeholder.style.cssText = "display:grid;place-items:center;position:absolute;inset:0;background:var(--bg-depth-2)";
                placeholder.innerHTML = `<span style="color:var(--t3);font-size:.7rem">Preview unavailable</span>`;
            }
        }
    }

    // load existing PDFs on page load
    (async () => {
        try {
            const res   = await fetch("/api/files/pdf");
            const files = await res.json();
            if (files.length) showPdfs(files.map(f => f.filename));
        } catch { }
    })();

})();
