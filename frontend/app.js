/* ==============================================================================
   DRAMA NHẬT STUDIO — FRONTEND APPLICATION LOGIC (V2.0 - BATCH & CUSTOM OUTPUT)
   ============================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  // State
  let currentMode = "single"; // "single" hoặc "batch"
  let selectedResolution = "1920x1080";
  let selectedFps = 24;
  let batchQueue = []; // [{ id, name, script_text, count, duration }]
  let currentResults = [];
  let socket = null;

  // DOM Elements
  const tabSingle = document.getElementById("tab-single");
  const tabBatch = document.getElementById("tab-batch");
  const tabAdas = document.getElementById("tab-adas");
  const singleScriptSection = document.getElementById("single-script-section");
  const batchScriptSection = document.getElementById("batch-script-section");
  const adasScriptSection = document.getElementById("adas-script-section");
  const projectNameGroup = document.getElementById("project-name-group");
  const projectNameInput = document.getElementById("script-title") || document.getElementById("project-name");
  const legacyProjectNameInput = document.getElementById("project-name");
  const channelNameInput = document.getElementById("channel-name");
  const scriptTextInput = document.getElementById("script-input") || document.getElementById("script-text");
  const legacyScriptTextInput = document.getElementById("script-text");
  const scriptStats = document.getElementById("script-stats");
  const charCountEl = document.getElementById("char-count");
  const estDurationEl = document.getElementById("est-duration");
  const estScenesEl = document.getElementById("est-scenes");
  const btnLoadSample = document.getElementById("btn-load-sample");
  const btnClearScript = document.getElementById("btn-clear-script");
  const outputDirInput = document.getElementById("output-dir");

  // Single file browse
  const singleFileInput = document.getElementById("single-file-input");
  const btnBrowseSingle = document.getElementById("btn-browse-single");

  // Batch elements
  const batchFilesInput = document.getElementById("batch-files-input");
  const btnBrowseBatch = document.getElementById("btn-browse-batch");
  const batchQueueContainer = document.getElementById("batch-queue-container");
  const queueCount = document.getElementById("queue-count");
  const queueList = document.getElementById("queue-list");
  const btnClearQueue = document.getElementById("btn-clear-queue");

  // Stock & Settings
  const stockSelect = document.getElementById("stock-select");
  const availableStockCount = document.getElementById("available-stock-count");
  const autoDeleteStock = document.getElementById("auto-delete-stock");
  const targetStockHoursInput = document.getElementById("target-stock-hours");
  const btnAutoReplenishMain = document.getElementById("btn-auto-replenish-main");
  const btnAutoReplenishModal = document.getElementById("btn-auto-replenish-modal");
  const mainReplenishMsg = document.getElementById("main-replenish-msg");
  const autoEnsureStock = document.getElementById("auto-ensure-stock");
  const cloudNoteLinkMain = document.getElementById("cloud-note-link-main");
  const cloudNoteLinkModal = document.getElementById("cloud-note-link-modal");
  const cloudNoteUrlText = document.getElementById("cloud-note-url-text");
  const cloudNoteCountMain = document.getElementById("cloud-note-count-main");
  const cloudNoteCountModal = document.getElementById("cloud-note-count-modal");
  const btnSyncCloudMain = document.getElementById("btn-sync-cloud-main");
  const btnSyncCloudModal = document.getElementById("btn-sync-cloud-modal");
  const cloudSyncMsg = document.getElementById("cloud-sync-msg");
  const bgmVolSlider = document.getElementById("bgm-vol");
  const bgmVolVal = document.getElementById("bgm-vol-val");

  // Preview Elements
  const previewContainer = document.getElementById("preview-container");
  const previewResTag = document.getElementById("preview-res-tag");
  const previewSubText = document.getElementById("preview-sub-text");
  const previewWatermarkText = document.getElementById("preview-watermark-text");

  // Control & Progress Elements
  const btnProduce = document.getElementById("btn-produce");
  const btnProduceLabel = document.getElementById("btn-produce-label");
  const progressSection = document.getElementById("progress-section");
  const progressMsg = document.getElementById("progress-msg");
  const progressPct = document.getElementById("progress-pct");
  const progressBar = document.getElementById("progress-bar");
  const progressStageName = document.getElementById("progress-stage-name");
  const progressTime = document.getElementById("progress-time");
  const deliverablesBox = document.getElementById("deliverables-box");
  const deliverablesTitle = document.getElementById("deliverables-title");

  // Deliverables Buttons
  const btnWatchVideo = document.getElementById("btn-watch-video");
  const btnOpenDir = document.getElementById("btn-open-dir");
  const btnCopySrt = document.getElementById("btn-copy-srt");
  const btnCopyChapters = document.getElementById("btn-copy-chapters");

  // Stock Modal Elements
  const btnOpenStockModal = document.getElementById("btn-open-stock-modal");
  const stockModal = document.getElementById("stock-modal");
  const btnCloseStockModal = document.getElementById("btn-close-stock-modal") || document.getElementById("btn-close-modal");
  const stockTableBody = document.getElementById("stock-table-body");
  const modalTotalStocks = document.getElementById("modal-total-stocks");
  const btnCleanupUsedStocks = document.getElementById("btn-cleanup-used-stocks");
  const btnRescanStocks = document.getElementById("btn-rescan-stocks");
  const ytUrlInput = document.getElementById("yt-url");
  const btnYtDownload = document.getElementById("btn-yt-download");
  const ytDownloadMsg = document.getElementById("yt-download-msg");

  // Folder Pickers & Stock Dir
  const btnBrowseOutputDir = document.getElementById("btn-browse-output-dir");
  const btnBrowseStockDir = document.getElementById("btn-browse-stock-dir");
  const btnModalBrowseStockDir = document.getElementById("btn-modal-browse-stock-dir");
  const btnApplyModalStockDir = document.getElementById("btn-apply-modal-stock-dir");
  const currentStookPath = document.getElementById("current-stook-path");
  const modalStookDirInput = document.getElementById("modal-stook-dir-input");

  // License Elements
  const btnOpenLicenseModal = document.getElementById("btn-open-license-modal");
  const licenseBadgeText = document.getElementById("license-badge-text");
  const licenseModal = document.getElementById("license-modal");
  const btnCloseLicenseModal = document.getElementById("btn-close-license-modal");
  const licenseHwidText = document.getElementById("license-hwid-text");
  const btnCopyHwid = document.getElementById("btn-copy-hwid");
  const licModalStatus = document.getElementById("lic-modal-status");
  const licModalPlan = document.getElementById("lic-modal-plan");
  const licModalExpiry = document.getElementById("lic-modal-expiry");
  const licenseKeyInput = document.getElementById("license-key-input");
  const btnActivateLicense = document.getElementById("btn-activate-license");
  const licenseModalMsg = document.getElementById("license-modal-msg");
  let isLicenseValid = false;
  window.__initErrors = [];

  function safeSetup(fn, label) {
    try {
      fn();
    } catch (err) {
      window.__initErrors.push({ label, error: String((err && err.stack) || err) });
      console.error(`[InitApp] Lỗi khởi tạo module ${label}:`, err);
    }
  }

  async function initApp() {
    safeSetup(setupLicenseSystem, "LicenseSystem");
    safeSetup(setupModeTabs, "ModeTabs");
    safeSetup(setupSingleFileLoader, "SingleFileLoader");
    safeSetup(setupBatchUploader, "BatchUploader");
    safeSetup(setupFolderPickers, "FolderPickers");
    safeSetup(setupResolutionSelectors, "ResolutionSelectors");
    safeSetup(setupFpsSelectors, "FpsSelectors");
    safeSetup(setupLivePreviewListeners, "LivePreviewListeners");
    safeSetup(setupStockModal, "StockModal");
    safeSetup(setupProductionTrigger, "ProductionTrigger");
    safeSetup(setupChatGPTAndADASSystem, "ChatGPTAndADASSystem");
    safeSetup(setupTelemetryPolling, "TelemetryPolling");
    await checkLicenseStatus();
    await loadConfig();
    await loadStocks();
    connectWebSocket();
  }

  // 1. Setup 4-Tab Studio Navigation & Mode Tabs
  function switchStudioTab(targetTabId) {
    if (!targetTabId) return;
    const actualPaneId = targetTabId === "tab-voice-stock" ? "tab-render" : targetTabId;
    if (targetTabId !== "tab-voice-stock") {
      window.scrollTo({ top: 0, behavior: "instant" });
    }
    document.querySelectorAll(".tab-pane").forEach((pane) => {
      if (pane.id === actualPaneId) {
        pane.style.display = "flex";
        pane.classList.remove("hidden");
        pane.classList.add("active");
      } else {
        pane.style.display = "none";
        pane.classList.add("hidden");
        pane.classList.remove("active");
      }
    });

    if (targetTabId === "tab-voice-stock") {
      const stockSec = document.getElementById("card-stock-section");
      if (stockSec) {
        setTimeout(() => stockSec.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
      }
    }

    document.querySelectorAll(".main-tab-btn").forEach((btn) => {
      const btnTarget = btn.dataset.tabTarget || btn.dataset.target;
      if (btnTarget === targetTabId) {
        btn.classList.add("active", "bg-surface-container", "text-primary-container", "border-b-2", "border-primary-container", "font-bold", "shadow-sm");
        btn.classList.remove("text-on-surface-variant", "border-transparent", "font-medium", "font-semibold");
      } else {
        btn.classList.remove("active", "bg-surface-container", "text-primary-container", "border-b-2", "border-primary-container", "font-bold", "shadow-sm");
        btn.classList.add("text-on-surface-variant", "border-transparent", "font-semibold");
      }
    });

    document.querySelectorAll(".quick-tab-jump").forEach((pill) => {
      const pillTarget = pill.dataset.tabTarget || pill.dataset.target || pill.dataset.jump;
      const dot = pill.querySelector(".sub-dot");
      if (pillTarget === targetTabId) {
        pill.className = "quick-tab-jump px-3 py-1.5 rounded-lg bg-primary-container/10 border border-primary-container/40 text-primary-container font-headline font-bold text-xs flex items-center gap-2 shadow-[0_0_12px_rgba(0,230,118,0.12)] transition-all";
        if (dot) dot.classList.remove("hidden");
      } else {
        pill.className = "quick-tab-jump px-3 py-1.5 rounded-lg bg-surface-container-low/60 hover:bg-surface-container border border-outline-variant/20 text-on-surface-variant hover:text-on-surface font-headline font-medium text-xs flex items-center gap-2 transition-all";
        if (dot) dot.classList.add("hidden");
      }
    });

    if (actualPaneId === "tab-render") {
      if (batchQueue.length > 0 && (!scriptTextInput || !scriptTextInput.value.trim())) {
        currentMode = "batch";
        updateBatchButtonLabel();
      } else {
        currentMode = "single";
        if (btnProduceLabel) {
          btnProduceLabel.innerText = "BẮT ĐẦU SẢN XUẤT 1-CLICK";
        }
      }
    }
  }

  function setupModeTabs() {
    document.querySelectorAll(".main-tab-btn, .quick-tab-jump").forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.dataset.tabTarget || btn.dataset.target || btn.dataset.jump;
        if (target) switchStudioTab(target);
      });
    });

    const btnHeaderTerminal = document.getElementById("btn-header-terminal");
    if (btnHeaderTerminal) {
      btnHeaderTerminal.addEventListener("click", () => {
        switchStudioTab("tab-diagnostics");
        const cmdInput = document.getElementById("terminal-quick-input");
        if (cmdInput) setTimeout(() => cmdInput.focus(), 100);
      });
    }

    if (tabSingle) {
      tabSingle.addEventListener("click", () => {
        currentMode = "single";
        tabSingle.className = "mode-tab active px-3 py-1.5 rounded-md bg-primary-container/15 text-primary-container border border-primary-container/40 text-[11px] font-headline font-bold flex items-center gap-1.5 transition-all shadow-[0_0_12px_rgba(0,230,118,0.15)]";
        if (tabBatch) {
          tabBatch.className = "mode-tab px-3 py-1.5 rounded-md text-on-surface-variant text-[11px] font-headline font-semibold hover:text-on-surface hover:bg-surface-container-low/50 flex items-center gap-1.5 transition-all border border-transparent";
        }
        if (tabAdas) tabAdas.classList.remove("active");
        if (singleScriptSection) {
          singleScriptSection.style.display = "flex";
          singleScriptSection.classList.remove("hidden");
        }
        if (batchScriptSection) {
          batchScriptSection.style.display = "none";
          batchScriptSection.classList.add("hidden");
        }
        if (projectNameGroup) projectNameGroup.style.display = "block";
        if (btnProduceLabel) btnProduceLabel.innerText = "XUẤT VIDEO HOÀN CHỈNH (FFMPEG NVENC GPU)";
      });
    }

    if (tabBatch) {
      tabBatch.addEventListener("click", () => {
        currentMode = "batch";
        tabBatch.className = "mode-tab active px-3 py-1.5 rounded-md bg-primary-container/15 text-primary-container border border-primary-container/40 text-[11px] font-headline font-bold flex items-center gap-1.5 transition-all shadow-[0_0_12px_rgba(0,230,118,0.15)]";
        if (tabSingle) {
          tabSingle.className = "mode-tab px-3 py-1.5 rounded-md text-on-surface-variant text-[11px] font-headline font-semibold hover:text-on-surface hover:bg-surface-container-low/50 flex items-center gap-1.5 transition-all border border-transparent";
        }
        if (tabAdas) tabAdas.classList.remove("active");
        if (singleScriptSection) {
          singleScriptSection.style.display = "none";
          singleScriptSection.classList.add("hidden");
        }
        if (batchScriptSection) {
          batchScriptSection.style.display = "block";
          batchScriptSection.classList.remove("hidden");
        }
        if (projectNameGroup) projectNameGroup.style.display = "none";
        updateBatchButtonLabel();
      });
    }

    const btnToggleAdas = document.getElementById("btn-toggle-adas-body");
    if (btnToggleAdas && adasScriptSection) {
      btnToggleAdas.addEventListener("click", () => {
        const isHidden = adasScriptSection.style.display === "none";
        adasScriptSection.style.display = isHidden ? "block" : "none";
        btnToggleAdas.innerText = isHidden ? "🔽 Thu gọn / Mở rộng" : "▶️ Mở rộng Trạm AI";
      });
    }
  }

  function updateBatchButtonLabel() {
    if (!btnProduceLabel) return;
    if (currentMode === "batch") {
      btnProduceLabel.innerText = batchQueue.length > 0
        ? `CHẠY HÀNG LOẠT (${batchQueue.length} KỊCH BẢN - FFMPEG NVENC GPU)`
        : "XUẤT VIDEO HOÀN CHỈNH (FFMPEG NVENC GPU)";
    } else {
      btnProduceLabel.innerText = "XUẤT VIDEO HOÀN CHỈNH (FFMPEG NVENC GPU)";
    }
  }

  // 2. Single File Loader & Sample/Clear Buttons
  function setupSingleFileLoader() {
    if (btnBrowseSingle && singleFileInput) {
      btnBrowseSingle.addEventListener("click", () => singleFileInput.click());
      singleFileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
          currentMode = "single";
          if (scriptTextInput) {
            scriptTextInput.value = event.target.result;
            scriptTextInput.dispatchEvent(new Event("input"));
          }
          if (legacyScriptTextInput && legacyScriptTextInput !== scriptTextInput) {
            legacyScriptTextInput.value = event.target.result;
          }
          const baseName = file.name.replace(/\.[^/.]+$/, "");
          if (projectNameInput) projectNameInput.value = baseName;
          if (legacyProjectNameInput && legacyProjectNameInput !== projectNameInput) {
            legacyProjectNameInput.value = baseName;
          }
          updateBatchButtonLabel();
        };
        reader.readAsText(file, "utf-8");
      });
    }

    if (btnLoadSample && scriptTextInput) {
      btnLoadSample.addEventListener("click", () => {
        currentMode = "single";
        const sampleScript = [
          "定年退職の日、夫は「お前とは別に暮らす」と冷たく言い放った。",
          "三十年間、家族のために尽くしてきた私に突きつけられたのは、一枚の離婚届だった。",
          "だが、私が静かに差し出した三十年前の家計ノートを開いた瞬間、夫の顔から血の気が引いていった。",
          "そこには、夫が忘れていたある重大な秘密と、毎月振り込まれ続けていた謎の口座記録が残されていたのだ。"
        ].join("\n");
        scriptTextInput.value = sampleScript;
        if (projectNameInput && !projectNameInput.value.trim()) {
          projectNameInput.value = "K1_DRAMA_SAMPLE";
        }
        scriptTextInput.dispatchEvent(new Event("input"));
        updateBatchButtonLabel();
      });
    }

    if (btnClearScript && scriptTextInput) {
      btnClearScript.addEventListener("click", () => {
        scriptTextInput.value = "";
        scriptTextInput.dispatchEvent(new Event("input"));
      });
    }
  }

  // 3. Batch Uploader & Queue Management
  function setupBatchUploader() {
    if (btnBrowseBatch && batchFilesInput) {
      btnBrowseBatch.addEventListener("click", () => batchFilesInput.click());
      batchFilesInput.addEventListener("change", async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        for (const file of files) {
          const text = await readFileAsText(file);
          const name = file.name.replace(/\.[^/.]+$/, "");
          const sentences = text.split("\n").filter(l => l.trim().length > 0);

          batchQueue.push({
            id: `job_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
            name: name,
            script_text: text,
            sentences_count: sentences.length
          });
        }

        currentMode = "batch";
        renderBatchQueue();
        updateBatchButtonLabel();
        batchFilesInput.value = "";
      });
    }

    if (btnClearQueue) {
      btnClearQueue.addEventListener("click", () => {
        batchQueue = [];
        currentMode = "single";
        renderBatchQueue();
        updateBatchButtonLabel();
      });
    }
  }

  function readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = reject;
      reader.readAsText(file, "utf-8");
    });
  }

  function renderBatchQueue() {
    if (!batchQueueContainer || !queueCount || !queueList) return;
    if (batchQueue.length === 0) {
      batchQueueContainer.style.display = "none";
      return;
    }

    batchQueueContainer.style.display = "block";
    queueCount.innerText = batchQueue.length;
    queueList.innerHTML = "";

    batchQueue.forEach((job, idx) => {
      const item = document.createElement("div");
      item.className = "queue-item";
      item.innerHTML = `
        <div>
          <span style="color: var(--accent-green); font-weight: 700; margin-right: 6px;">#${idx+1}</span>
          <span class="queue-item-name">${job.name}</span>
          <span class="queue-item-meta">(${job.sentences_count} câu)</span>
        </div>
        <button type="button" class="queue-item-del" data-idx="${idx}">&times;</button>
      `;
      queueList.appendChild(item);
    });

    // Sự kiện xóa từng item
    document.querySelectorAll(".queue-item-del").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.idx);
        batchQueue.splice(idx, 1);
        if (batchQueue.length === 0) currentMode = "single";
        renderBatchQueue();
        updateBatchButtonLabel();
      });
    });
  }

  // 3b. Setup Folder Pickers (Thư mục lưu thành phẩm & Kho Stock)
  function syncStoragePathsToUI(sp) {
    if (!sp || typeof sp !== "object") return;
    const pDir = sp.projects_dir || "";
    const fDir = sp.final_video_dir || pDir || "";
    const ssdDir = sp.ssd_staging_dir || "";
    const useSsd = sp.use_ssd_staging !== undefined ? Boolean(sp.use_ssd_staging) : true;

    const adasProjInput = document.getElementById("adas-projects-dir-input");
    const renderProjInput = document.getElementById("render-projects-dir");
    const adasFinalInput = document.getElementById("adas-final-video-dir-input");
    const adasSsdChk = document.getElementById("adas-use-ssd-staging");
    const renderSsdChk = document.getElementById("render-use-ssd-staging");
    const ssdBadge = document.getElementById("adas-ssd-staging-badge");

    if (pDir) {
      if (adasProjInput) adasProjInput.value = pDir;
      if (renderProjInput) renderProjInput.value = pDir;
    }
    if (fDir) {
      if (adasFinalInput) adasFinalInput.value = fDir;
      if (outputDirInput) outputDirInput.value = fDir;
    }
    if (adasSsdChk) adasSsdChk.checked = useSsd;
    if (renderSsdChk) renderSsdChk.checked = useSsd;
    if (ssdBadge && ssdDir) {
      ssdBadge.innerText = `SSD Cache: ${ssdDir}`;
    }
  }

  async function updateStoragePathsBackend(payload, showAlert = false) {
    try {
      const res = await fetch("/api/storage-paths", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {})
      });
      const data = await res.json();
      if (res.ok && data.success) {
        syncStoragePathsToUI(data);
        if (data.restore_summary && Array.isArray(data.restore_summary.ideas)) {
          if (typeof window.__renderSavedIdeasGlobal === "function") {
            window.__renderSavedIdeasGlobal(data.restore_summary.ideas);
          }
        }
        const rs = data.restore_summary || {};
        appendInstantLogToUI(
          `📂 Đã cập nhật đường dẫn: Folder Project=[${data.projects_dir}] | Nơi Chứa Video Cuối=[${data.final_video_dir}] | Đã load ${rs.total_count ?? 0} dự án (${rs.script_done_count ?? 0} KB xong, ${rs.video_done_count ?? 0} MP4).`,
          "SYSTEM",
          "INFO"
        );
        if (showAlert) {
          alert(
            `✅ Đã cập nhật đường dẫn & nạp dự án thành công!\n\n` +
            `📂 1. Folder Project: ${data.projects_dir}\n` +
            `🎬 2. Nơi Chứa Video Cuối: ${data.final_video_dir}\n` +
            `⚡ Render SSD Staging: ${data.use_ssd_staging ? "ĐANG BẬT (Tự chuyển MP4 sang Nơi Chứa Video Cuối)" : "ĐANG TẮT"}\n\n` +
            `📊 Đã load: ${rs.total_count ?? 0} dự án (${rs.script_done_count ?? 0} kịch bản xong, ${rs.video_done_count ?? 0} video MP4)`
          );
        }
        return data;
      } else {
        alert("❌ Không thể cập nhật đường dẫn: " + (data.detail || "Lỗi không xác định"));
      }
    } catch (e) {
      console.error("Lỗi cập nhật đường dẫn:", e);
      alert("❌ Lỗi kết nối khi cập nhật đường dẫn: " + e.message);
    }
    return null;
  }

  function setupFolderPickers() {
    async function browseAndPickFolder(btnEl, dialogTitle, onPicked) {
      if (!btnEl) return;
      btnEl.disabled = true;
      const origHtml = btnEl.innerHTML;
      btnEl.innerText = "⏳ Đang mở...";
      try {
        const res = await fetch("/api/browse-directory", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: dialogTitle })
        });
        const data = await res.json();
        if (data && data.path) {
          await onPicked(data.path);
        }
      } catch (e) {
        console.error("Lỗi khi mở hộp thoại chọn thư mục:", e);
        alert("Không thể mở hộp thoại chọn thư mục: " + e.message);
      } finally {
        btnEl.disabled = false;
        btnEl.innerHTML = origHtml;
      }
    }

    // 1A. Nút Chọn Folder Project (Tab 1 & Tab 2)
    const btnAdasPickProj = document.getElementById("btn-adas-pick-projects-dir");
    const btnRenderPickProj = document.getElementById("btn-browse-projects-dir");
    [btnAdasPickProj, btnRenderPickProj].forEach(btn => {
      if (btn) {
        btn.addEventListener("click", () => {
          browseAndPickFolder(btn, "Chọn Folder Project (Chứa Dự Án / Kịch Bản)", async (pickedPath) => {
            await updateStoragePathsBackend({ projects_dir: pickedPath }, true);
          });
        });
      }
    });

    // 1B. Nút Chọn Nơi Chứa Video Cuối (Tab 1 & Tab 2)
    const btnAdasPickFinal = document.getElementById("btn-adas-pick-final-video-dir");
    [btnAdasPickFinal, btnBrowseOutputDir].forEach(btn => {
      if (btn) {
        btn.addEventListener("click", () => {
          browseAndPickFolder(btn, "Chọn Nơi Chứa Video Cuối (Ổ Lưu MP4 Sau Khi Render SSD)", async (pickedPath) => {
            await updateStoragePathsBackend({ final_video_dir: pickedPath }, true);
          });
        });
      }
    });

    // 1C. Nhấn Enter trên các ô nhập đường dẫn Folder Project / Nơi Chứa Video Cuối
    const adasProjInput = document.getElementById("adas-projects-dir-input");
    const renderProjInput = document.getElementById("render-projects-dir");
    [adasProjInput, renderProjInput].forEach(inp => {
      if (inp) {
        inp.addEventListener("keydown", async (e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            const val = inp.value.trim();
            if (val) await updateStoragePathsBackend({ projects_dir: val }, true);
          }
        });
        inp.addEventListener("change", async () => {
          const val = inp.value.trim();
          if (val) await updateStoragePathsBackend({ projects_dir: val }, false);
        });
      }
    });

    const adasFinalInput = document.getElementById("adas-final-video-dir-input");
    [adasFinalInput, outputDirInput].forEach(inp => {
      if (inp) {
        inp.addEventListener("keydown", async (e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            const val = inp.value.trim();
            if (val) await updateStoragePathsBackend({ final_video_dir: val }, true);
          }
        });
        inp.addEventListener("change", async () => {
          const val = inp.value.trim();
          if (val) await updateStoragePathsBackend({ final_video_dir: val }, false);
        });
      }
    });

    // 1D. Checkbox Bật/Tắt Render SSD Staging
    const adasSsdChk = document.getElementById("adas-use-ssd-staging");
    const renderSsdChk = document.getElementById("render-use-ssd-staging");
    [adasSsdChk, renderSsdChk].forEach(chk => {
      if (chk) {
        chk.addEventListener("change", async () => {
          await updateStoragePathsBackend({ use_ssd_staging: chk.checked }, false);
        });
      }
    });

    // 1E. Nút Mở Nơi Chứa Video Cuối
    const btnOpenFinalDir = document.getElementById("btn-adas-open-final-video-dir");
    if (btnOpenFinalDir) {
      btnOpenFinalDir.addEventListener("click", async () => {
        const fPath = (adasFinalInput && adasFinalInput.value.trim()) || (outputDirInput && outputDirInput.value.trim()) || "projects";
        await openSystemFolder(fPath);
      });
    }

    // 2. Nút chọn kho stock ngoài màn hình chính
    if (btnBrowseStockDir) {
      btnBrowseStockDir.addEventListener("click", async () => {
        await pickAndChangeStockDir(btnBrowseStockDir, "📂 Chọn Kho Stock");
      });
    }

    // 3. Nút chọn kho stock trong Modal
    if (btnModalBrowseStockDir) {
      btnModalBrowseStockDir.addEventListener("click", async () => {
        await pickAndChangeStockDir(btnModalBrowseStockDir, "📂 Duyệt Thư Mục...");
      });
    }

    // 4. Nút Áp Dụng đường dẫn kho stock gõ tay/dán trong Modal
    if (btnApplyModalStockDir && modalStookDirInput) {
      btnApplyModalStockDir.addEventListener("click", async () => {
        const customPath = modalStookDirInput.value.trim();
        if (!customPath) {
          alert("Vui lòng nhập hoặc dán đường dẫn thư mục Kho Stock!");
          return;
        }
        await applyNewStockDirectory(customPath);
      });

      modalStookDirInput.addEventListener("keydown", async (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          const customPath = modalStookDirInput.value.trim();
          if (customPath) {
            await applyNewStockDirectory(customPath);
          }
        }
      });
    }
  }

  async function pickAndChangeStockDir(btnElement, originalText) {
    if (btnElement) {
      btnElement.disabled = true;
      btnElement.innerText = "⏳ Đang mở...";
    }
    try {
      const res = await fetch("/api/browse-directory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Chọn Thư Mục Chứa Video Stock Nền" })
      });
      const data = await res.json();
      if (data && data.path) {
        await applyNewStockDirectory(data.path);
      }
    } catch (e) {
      console.error("Lỗi chọn kho stock:", e);
      alert("Lỗi khi mở chọn kho stock: " + e.message);
    } finally {
      if (btnElement) {
        btnElement.disabled = false;
        btnElement.innerText = originalText;
      }
    }
  }

  async function applyNewStockDirectory(newPath) {
    try {
      const res = await fetch("/api/stocks/set-directory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ directory: newPath })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        await loadStocks();
        alert(`✅ Đã chuyển sang kho Stock mới thành công!\n📁 Đường dẫn: ${newPath}\n📊 Tổng cộng: ${data.data.total} video (${data.data.available_count} khả dụng)`);
      } else {
        alert("❌ Lỗi chuyển kho stock: " + (data.detail || "Thư mục không tồn tại hoặc không hợp lệ"));
      }
    } catch (e) {
      alert("❌ Lỗi kết nối khi cập nhật kho stock: " + e.message);
    }
  }

  // 4. Load Config từ Backend
  async function loadConfig() {
    try {
      const res = await fetch("/api/config");
      const data = await res.json();
      if (data.gpu_name) {
        const gpuEl = document.getElementById("gpu-name");
        if (gpuEl) gpuEl.innerText = data.gpu_name;
      }
      if (data.storage_paths) {
        syncStoragePathsToUI(data.storage_paths);
      } else {
        syncStoragePathsToUI(data);
        try {
          const spRes = await fetch("/api/storage-paths");
          if (spRes.ok) {
            const spData = await spRes.json();
            syncStoragePathsToUI(spData);
          }
        } catch (_) {}
      }
    } catch (e) {
      console.warn("Không thể tải config:", e);
    }
  }

  // 5. Resolution & FPS
  function setupResolutionSelectors() {
    const btns = document.querySelectorAll("#resolution-grid .select-btn, #resolution-grid .res-card");
    btns.forEach(btn => {
      btn.addEventListener("click", () => {
        btns.forEach(b => {
          b.classList.remove("active", "border-2", "border-primary-container", "bg-primary-container/10", "shadow-[0_0_15px_rgba(0,230,118,0.12)]");
          b.classList.add("border", "border-outline-variant/25", "bg-surface-container");
          const dot = b.querySelector(".res-dot");
          if (dot) dot.className = "res-dot w-2 h-2 rounded-full bg-outline-variant/40";
        });
        btn.classList.add("active", "border-2", "border-primary-container", "bg-primary-container/10", "shadow-[0_0_15px_rgba(0,230,118,0.12)]");
        btn.classList.remove("border", "border-outline-variant/25", "bg-surface-container");
        const activeDot = btn.querySelector(".res-dot");
        if (activeDot) activeDot.className = "res-dot w-2 h-2 rounded-full bg-primary-container shadow-[0_0_6px_#00e676]";
        selectedResolution = btn.dataset.res;
        updatePreviewDimensions();
      });
    });
  }

  function setupFpsSelectors() {
    const pills = document.querySelectorAll("#fps-pills .pill-btn, #fps-pills .pill");
    pills.forEach(pill => {
      pill.addEventListener("click", () => {
        pills.forEach(p => {
          p.classList.remove("active", "border-2", "border-secondary-container", "bg-secondary-container/10", "shadow-[0_0_15px_rgba(0,210,255,0.12)]");
          p.classList.add("border", "border-outline-variant/25", "bg-surface-container");
        });
        pill.classList.add("active", "border-2", "border-secondary-container", "bg-secondary-container/10", "shadow-[0_0_15px_rgba(0,210,255,0.12)]");
        pill.classList.remove("border", "border-outline-variant/25", "bg-surface-container");
        selectedFps = parseInt(pill.dataset.fps);
        updatePreviewDimensions();
      });
    });
  }

  function updatePreviewDimensions() {
    if (previewResTag) {
      previewResTag.innerText = `${selectedResolution} @ ${selectedFps}FPS`;
    }
    const specRes = document.getElementById("spec-res");
    if (specRes) specRes.innerText = selectedResolution;
    const specFps = document.getElementById("spec-fps");
    if (specFps) specFps.innerText = `${selectedFps} FPS`;

    const resPill = document.getElementById("preview-spec-res-pill");
    if (resPill) {
      const labelMap = {
        "1920x1080": "1920x1080 (Full HD)",
        "1280x720": "1280x720 (HD)",
        "2560x1440": "2560x1440 (2K QHD)",
        "3840x2160": "3840x2160 (4K UHD)",
        "1080x1920": "1080x1920 (Shorts 9:16)"
      };
      resPill.innerText = labelMap[selectedResolution] || selectedResolution;
    }
    const fpsPill = document.getElementById("preview-spec-fps-pill");
    if (fpsPill) {
      fpsPill.innerText = `${selectedFps} FPS`;
    }
    const masterTag = document.getElementById("preview-master-tag");
    if (masterTag) {
      masterTag.innerText = selectedResolution === "1080x1920" ? "SHORTS 9:16 • MASTER" : "16:9 • MASTER";
    }

    if (previewContainer) {
      if (selectedResolution === "1080x1920") {
        previewContainer.style.aspectRatio = "9 / 16";
        previewContainer.style.maxHeight = "480px";
        previewContainer.style.margin = "0 auto";
      } else {
        previewContainer.style.aspectRatio = "16 / 9";
        previewContainer.style.maxHeight = "none";
      }
    }
  }

  // 6. Live Preview & 5-Layer Timeline Playback Controller
  let previewSentencesList = [
    "定年退職の日、夫は「お前とは別に暮らす」と冷たく言い放った。",
    "三十年間、家族のために尽くしてきた私に突きつけられたのは、一枚の離婚届だった。",
    "だが、私が静かに差し出した三十年前の家計ノートを開いた瞬間、夫の顔から血の気が引いていった。",
    "そこには、夫が忘れていたある重大な秘密と、毎月振り込まれ続けていた謎の口座記録が残されていたのだ。"
  ];
  let previewCurrentIdx = 0;
  let previewTotalEstSec = 1390;
  let previewPlayInterval = null;

  function formatSecToTimecode(sec, includeFrames = false) {
    const s = Math.max(0, Math.floor(sec || 0));
    const hh = String(Math.floor(s / 3600)).padStart(2, "0");
    const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    if (includeFrames) {
      const ff = String((s * 7) % (selectedFps || 24)).padStart(2, "0");
      return `${hh}:${mm}:${ss}:${ff}`;
    }
    return `${hh}:${mm}:${ss}`;
  }

  function renderPreviewTimelinePosition(idx) {
    const total = Math.max(1, previewSentencesList.length);
    previewCurrentIdx = Math.max(0, Math.min(total - 1, idx));
    const curSentence = previewSentencesList[previewCurrentIdx] || "";
    if (previewSubText && curSentence) {
      previewSubText.innerText = curSentence;
    }
    const pct = total > 1 ? Math.round(((previewCurrentIdx + 1) / total) * 100) : 18;
    const curSec = Math.round((pct / 100) * previewTotalEstSec);

    const scrubFill = document.getElementById("preview-scrub-fill");
    const scrubThumb = document.getElementById("preview-scrub-thumb");
    const recTimer = document.getElementById("preview-rec-timer");
    const timeCur = document.getElementById("preview-time-cur");
    const timeTotal = document.getElementById("preview-time-total");
    const sceneBadge = document.getElementById("preview-scene-badge");
    const segCounter = document.getElementById("preview-segment-counter");

    if (scrubFill) scrubFill.style.width = `${pct}%`;
    if (scrubThumb) scrubThumb.style.left = `${pct}%`;
    if (recTimer) recTimer.innerText = formatSecToTimecode(curSec, true);
    if (timeCur) timeCur.innerText = formatSecToTimecode(curSec, false);
    if (timeTotal) timeTotal.innerText = formatSecToTimecode(previewTotalEstSec, false);
    if (sceneBadge) {
      sceneBadge.innerText = `SCENE #${String(previewCurrentIdx + 1).padStart(3, "0")} / ${String(total).padStart(3, "0")}`;
    }
    if (segCounter) {
      segCounter.innerText = `Câu #${previewCurrentIdx + 1} / ${total}`;
    }
  }

  function setupLivePreviewListeners() {
    if (channelNameInput && previewWatermarkText) {
      previewWatermarkText.innerText = channelNameInput.value.trim() || ".";
      channelNameInput.addEventListener("input", () => {
        previewWatermarkText.innerText = channelNameInput.value.trim() || ".";
      });
    }

    // 5-Layer Visibility Toggles
    document.querySelectorAll(".preview-layer-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const rawLayer = btn.dataset.layer || "1";
        const layerId = rawLayer.startsWith("preview-layer-") ? rawLayer : `preview-layer-${rawLayer}`;
        const layerEl = document.getElementById(layerId);
        if (!layerEl) return;
        const isHidden = layerEl.style.opacity === "0";
        layerEl.style.opacity = isHidden ? "" : "0";
        btn.style.opacity = isHidden ? "1" : "0.4";
      });
    });

    // Timeline Prev / Next / Play / Scrub / Fullscreen
    const btnPrevScene = document.getElementById("btn-preview-prev-scene");
    const btnNextScene = document.getElementById("btn-preview-next-scene");
    const btnPlayToggle = document.getElementById("btn-preview-play-toggle");
    const playIcon = document.getElementById("preview-play-icon");
    const scrubBar = document.getElementById("preview-scrub-bar");
    const btnFullscreen = document.getElementById("btn-preview-fullscreen");

    if (btnPrevScene) {
      btnPrevScene.addEventListener("click", () => {
        renderPreviewTimelinePosition(previewCurrentIdx - 1);
      });
    }
    if (btnNextScene) {
      btnNextScene.addEventListener("click", () => {
        renderPreviewTimelinePosition(previewCurrentIdx + 1);
      });
    }
    if (btnPlayToggle) {
      btnPlayToggle.addEventListener("click", () => {
        if (previewPlayInterval) {
          clearInterval(previewPlayInterval);
          previewPlayInterval = null;
          if (playIcon) playIcon.innerText = "play_arrow";
        } else {
          if (playIcon) playIcon.innerText = "pause";
          previewPlayInterval = setInterval(() => {
            const nextIdx = (previewCurrentIdx + 1) % Math.max(1, previewSentencesList.length);
            renderPreviewTimelinePosition(nextIdx);
          }, 2200);
        }
      });
    }
    if (scrubBar) {
      scrubBar.addEventListener("click", (e) => {
        const rect = scrubBar.getBoundingClientRect();
        if (!rect.width) return;
        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const targetIdx = Math.floor(ratio * Math.max(1, previewSentencesList.length - 1));
        renderPreviewTimelinePosition(targetIdx);
      });
    }
    if (btnFullscreen && previewContainer) {
      btnFullscreen.addEventListener("click", () => {
        if (!document.fullscreenElement) {
          previewContainer.requestFullscreen().catch(() => {});
        } else {
          document.exitFullscreen().catch(() => {});
        }
      });
    }

    if (scriptTextInput) {
      let debounceTimer = null;
      scriptTextInput.addEventListener("input", () => {
        const rawText = scriptTextInput.value;
        const text = rawText.trim();
        if (text) currentMode = "single";
        if (legacyScriptTextInput && legacyScriptTextInput !== scriptTextInput) {
          legacyScriptTextInput.value = rawText;
        }
        if (charCountEl) {
          charCountEl.innerText = `${text.length.toLocaleString()}`;
        }

        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
          if (!text) {
            if (scriptStats) scriptStats.innerText = "0 câu | ~00:00";
            if (estDurationEl) estDurationEl.innerText = "~00:00";
            if (estScenesEl) estScenesEl.innerText = "0";
            return;
          }

          try {
            const res = await fetch("/api/preview-script", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ script_text: text })
            });
            const data = await res.json();
            if (scriptStats) {
              scriptStats.innerText = `${data.sentence_count} câu | ~${data.estimated_formatted}`;
            }
            if (estDurationEl) {
              estDurationEl.innerText = `~${data.estimated_formatted}`;
            }
            if (estScenesEl) {
              estScenesEl.innerText = `${data.sentence_count}`;
            }
            if (data.estimated_seconds) {
              previewTotalEstSec = data.estimated_seconds;
            }
            if (data.sample_sentences && data.sample_sentences.length > 0 && previewSubText) {
              previewSubText.innerHTML = data.sample_sentences.slice(0, 2).join("<br>");
            }
          } catch (e) {
            console.error(e);
          }
        }, 300);
      });
    }

    // Bidirectional BGM Volume Sliders (Tab 2 #bgm-vol-render <-> Tab 3 #bgm-vol)
    const bgmVolRender = document.getElementById("bgm-vol-render");
    const bgmVolLabelRender = document.getElementById("bgm-vol-label-render");
    const bgmVolLabelTab3 = document.getElementById("bgm-vol-label");

    function syncBgmVolumeUI(rawVal) {
      const num = parseFloat(rawVal);
      const pct = num <= 1.0 ? Math.round(num * 100) : Math.round(num);
      const floatVal = (pct / 100).toFixed(2);
      if (bgmVolSlider) {
        const max1 = parseFloat(bgmVolSlider.max || "1");
        bgmVolSlider.value = max1 <= 1.0 ? floatVal : String(pct);
      }
      if (bgmVolRender) {
        const max2 = parseFloat(bgmVolRender.max || "1");
        bgmVolRender.value = max2 <= 1.0 ? floatVal : String(pct);
      }
      if (bgmVolVal) bgmVolVal.innerText = `${pct}%`;
      if (bgmVolLabelTab3) bgmVolLabelTab3.innerText = `${pct}%`;
      if (bgmVolLabelRender) bgmVolLabelRender.innerText = `${pct}%`;
    }

    if (bgmVolSlider) {
      bgmVolSlider.addEventListener("input", () => syncBgmVolumeUI(bgmVolSlider.value));
    }
    if (bgmVolRender) {
      bgmVolRender.addEventListener("input", () => syncBgmVolumeUI(bgmVolRender.value));
    }
  }

  // 7. Quản lý kho Stock (2 Chế Độ: 1. Dùng Stock Tải Về Tự Động & 2. Dùng Stock Sẵn Có)
  let currentStockSourceMode = "auto_download";

  function syncStockModeUI(modeVal) {
    currentStockSourceMode = (modeVal === "local_available") ? "local_available" : "auto_download";
    const mainModeSel = document.getElementById("stock-source-mode-select");
    const modalModeSel = document.getElementById("modal-stock-source-mode-select");
    const autoDlBox = document.getElementById("stock-auto-download-box");
    if (mainModeSel && mainModeSel.value !== currentStockSourceMode) {
      mainModeSel.value = currentStockSourceMode;
    }
    if (modalModeSel && modalModeSel.value !== currentStockSourceMode) {
      modalModeSel.value = currentStockSourceMode;
    }
    if (autoDlBox) {
      // Hiển thị hộp điều khiển Tải Stock & Link Chống Trùng ở Chế độ 1; làm mờ nhẹ ở Chế độ 2
      autoDlBox.style.display = currentStockSourceMode === "auto_download" ? "flex" : "none";
    }
    if (autoDeleteStock) {
      if (currentStockSourceMode === "local_available") {
        autoDeleteStock.checked = false;
      } else {
        autoDeleteStock.checked = true;
      }
    }
    if (autoEnsureStock) {
      if (currentStockSourceMode === "local_available") {
        autoEnsureStock.checked = false;
      } else {
        autoEnsureStock.checked = true;
      }
    }
  }

  async function switchStockSourceModeBackend(newMode) {
    syncStockModeUI(newMode);
    try {
      const res = await fetch("/api/stocks/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: currentStockSourceMode })
      });
      if (res.ok) {
        await loadStocks();
      }
    } catch (e) {
      console.warn("Lỗi chuyển chế độ Stock:", e);
    }
  }

  async function loadStocks() {
    try {
      const res = await fetch("/api/stocks");
      const data = await res.json();

      if (data.stock_source_mode) {
        syncStockModeUI(data.stock_source_mode);
      }

      const isLocalMode = currentStockSourceMode === "local_available";
      const availFiles = data.available_count || 0;
      const availUses = data.available_uses_count !== undefined ? data.available_uses_count : availFiles;
      const rawHours = data.available_raw_hours !== undefined ? data.available_raw_hours : 0;
      const targetHrs = data.target_stock_hours || (targetStockHoursInput ? parseFloat(targetStockHoursInput.value) || 30 : 30);
      if (targetStockHoursInput && data.target_stock_hours) {
        targetStockHoursInput.value = data.target_stock_hours;
        updateReplenishButtonLabels(data.target_stock_hours);
      }
      if (availableStockCount) {
        availableStockCount.innerText = isLocalMode
          ? `${availFiles} file sẵn có (${rawHours}h • Xoay vòng giữ nguyên file)`
          : `${availFiles} file khả dụng (${rawHours}h gốc • ${availUses} lượt xuất)`;
      }
      if (modalTotalStocks) {
        modalTotalStocks.innerText = isLocalMode
          ? `📂 Chế độ 2 (Stock Sẵn Có): ${data.total || 0} file (${rawHours}h gốc • Xoay vòng không xóa)`
          : `🌐 Chế độ 1 (Stock Tải Về): ${data.total || 0} file — ${rawHours}h khả dụng (${availUses} cuộn chưa dùng)`;
      }

      // Cập nhật hiển thị đường dẫn kho stock hiện tại
      if (data.current_stook_dir) {
        if (currentStookPath) currentStookPath.innerText = data.current_stook_dir;
        if (modalStookDirInput) modalStookDirInput.value = data.current_stook_dir;
      }

      // Cập nhật thông tin Note Online chống trùng riêng của Mexico Ông Già
      if (data.used_links_count !== undefined) {
        if (cloudNoteCountMain) cloudNoteCountMain.innerText = `${data.used_links_count} links`;
        if (cloudNoteCountModal) cloudNoteCountModal.innerText = data.used_links_count;
      }
      if (data.cloud_note_url) {
        if (cloudNoteLinkMain) {
          cloudNoteLinkMain.href = data.cloud_note_url;
          cloudNoteLinkMain.innerText = data.cloud_note_url.replace(/^https?:\/\//, "");
        }
        if (cloudNoteLinkModal) cloudNoteLinkModal.href = data.cloud_note_url;
        if (cloudNoteUrlText) cloudNoteUrlText.innerText = data.cloud_note_url;
      }

      const defaultOptText = isLocalMode
        ? `📂 Tự động xoay vòng Stock sẵn có trong kho STOOK (Không tải mạng • Giữ nguyên file)`
        : `🛡️ Tự động chọn Stock 720p tải về chưa dùng (Dùng xong tự xóa • Chống trùng 100%)`;

      stockSelect.innerHTML = `<option value="auto_unique">${defaultOptText}</option>`;
      if (data.items && data.items.length > 0) {
        data.items.forEach(item => {
          const maxUses = item.max_uses || 1;
          const usedCount = item.usage_count || 0;
          const isFullyUsed = !isLocalMode && (usedCount >= maxUses || item.status === "used");
          const opt = document.createElement("option");
          opt.value = item.id;
          if (isFullyUsed) {
            opt.disabled = true;
            opt.innerText = `⛔ [ĐÃ DÙNG] ${item.name} (${item.duration_formatted}) — Đã khóa`;
            opt.style.color = "#ff6666";
            opt.style.background = "#2a1515";
          } else if (isLocalMode) {
            opt.innerText = `📂 [Sẵn có • Đã xoay vòng ${usedCount} lần] ${item.name} (${item.duration_formatted})`;
          } else {
            opt.innerText = `🟢 [Mới 100% • Dùng xong tự xóa] ${item.name} (${item.duration_formatted})`;
          }
          stockSelect.appendChild(opt);
        });

        renderStockTable(data.items);
        renderInlineStockRolls(data.items);
      } else {
        stockSelect.innerHTML = `<option value="auto_unique">⚠️ Kho này chưa có video (.mp4) nào — Bấm Tải Sẵn Đủ 30 Tiếng Stock hoặc chọn thư mục STOOK!</option>`;
        renderStockTable([]);
        renderInlineStockRolls([]);
      }
    } catch (e) {
      console.warn("Lỗi tải kho stock:", e);
    }
  }

  function renderInlineStockRolls(items) {
    const inlineList = document.getElementById("inline-stock-rolls-list");
    if (!inlineList) return;
    if (!items || items.length === 0) {
      inlineList.innerHTML = `<div class="p-3 rounded-lg bg-surface-container-lowest/80 border border-outline-variant/20 text-center text-xs text-on-surface-variant">Kho STOOK hiện đang trống. Bấm <strong>Tải Sẵn Đủ 30 Tiếng Stock</strong> bên trên để tự động nạp video 720p mới!</div>`;
      return;
    }
    const isLocalMode = currentStockSourceMode === "local_available";
    inlineList.innerHTML = items.slice(0, 25).map((item) => {
      const maxUses = item.max_uses || 1;
      const usedCount = item.usage_count || 0;
      const isFullyUsed = !isLocalMode && (usedCount >= maxUses || item.status === "used");
      if (!isFullyUsed) {
        return `
          <div class="inline-stock-item flex items-center justify-between p-2 rounded-lg bg-surface-container-lowest/80 border border-outline-variant/20 hover:border-secondary-container/40 transition-colors cursor-pointer" data-stock-id="${item.id}">
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-8 h-6 rounded bg-secondary-container/20 border border-secondary-container/40 flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-secondary-container text-[14px]">movie</span>
              </div>
              <span class="font-mono text-xs text-on-surface truncate">${item.name}</span>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <span class="text-[10px] font-mono text-on-surface-variant">720p • ${item.duration_formatted || "30:00"}</span>
              <span class="px-1.5 py-0.5 rounded bg-primary-container/15 text-primary-container font-mono text-[9px] font-bold">Khả dụng</span>
            </div>
          </div>
        `;
      } else {
        return `
          <div class="flex items-center justify-between p-2 rounded-lg bg-surface-container-lowest/40 border border-outline-variant/10 opacity-60">
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-8 h-6 rounded bg-surface-container-high border border-outline-variant/30 flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-on-surface-variant text-[14px]">lock</span>
              </div>
              <span class="font-mono text-xs text-on-surface-variant line-through truncate">${item.name}</span>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <span class="text-[10px] font-mono text-on-surface-variant">Đã dùng (${item.size_mb || 0}MB)</span>
              <span class="px-1.5 py-0.5 rounded bg-error-container/30 text-error font-mono text-[9px] font-bold">Chờ xóa</span>
            </div>
          </div>
        `;
      }
    }).join("");

    inlineList.querySelectorAll(".inline-stock-item").forEach((el) => {
      el.addEventListener("click", () => {
        const sid = el.dataset.stockId;
        if (stockSelect && sid) {
          stockSelect.value = sid;
        }
      });
    });
  }

  function renderStockTable(items) {
    if (!stockTableBody) return;
    if (!items || items.length === 0) {
      stockTableBody.innerHTML = `<tr><td colspan="6" class="px-4 py-6 text-center text-on-surface-variant">Kho STOOK chưa có video nào. Dán link YouTube bên trên hoặc bấm Tự Động Bù Stock để tải!</td></tr>`;
      return;
    }

    const isLocalMode = currentStockSourceMode === "local_available";
    stockTableBody.innerHTML = "";
    items.forEach(item => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-surface-container/60 transition-colors";
      const maxUses = item.max_uses || 1;
      const usedCount = item.usage_count || 0;
      const isFullyUsed = !isLocalMode && (usedCount >= maxUses || item.status === "used");

      let statusBadge = "";
      let actionBtn = "";
      if (isLocalMode) {
        statusBadge = `<span class="px-2 py-0.5 rounded bg-primary-container/15 text-primary-container border border-primary-container/30 text-[10px] font-bold">📂 Sẵn có (Đã dùng ${usedCount} lần)</span>`;
        actionBtn = `<span class="text-secondary text-[11px] font-bold">♻️ Xoay vòng • Giữ file</span>`;
      } else if (!isFullyUsed) {
        statusBadge = `<span class="px-2 py-0.5 rounded bg-primary-container/15 text-primary-container border border-primary-container/30 text-[10px] font-bold">🟢 Mới 100% (Khả dụng)</span>`;
        actionBtn = `<span class="text-primary-container text-[11px] font-bold">🗑️ Dùng xong tự xóa</span>`;
      } else {
        statusBadge = `<span class="px-2 py-0.5 rounded bg-error/15 text-error border border-error/30 text-[10px] font-bold">🔒 Đã dùng - ĐÃ KHÓA</span>`;
        actionBtn = `<span class="text-error text-[11px] font-bold">🔒 Cấm dùng lại</span>`;
      }

      const projects = item.used_in_projects && item.used_in_projects.length > 0
        ? item.used_in_projects.join(", ")
        : "—";

      tr.innerHTML = `
        <td class="px-4 py-2.5 font-mono text-on-surface font-semibold">${item.name}</td>
        <td class="px-3 py-2.5 font-mono text-secondary-container">${item.duration_formatted}</td>
        <td class="px-3 py-2.5 font-mono text-on-surface-variant">${item.size_mb} MB</td>
        <td class="px-3 py-2.5">${statusBadge}</td>
        <td class="px-3 py-2.5 font-mono text-on-surface-variant text-[11px]">${projects}</td>
        <td class="px-4 py-2.5 text-right">${actionBtn}</td>
      `;
      stockTableBody.appendChild(tr);
    });
  }

  function updateReplenishButtonLabels(hrs) {
    const h = hrs || (targetStockHoursInput ? parseFloat(targetStockHoursInput.value) || 30 : 30);
    if (btnAutoReplenishMain && !btnAutoReplenishMain.disabled) {
      btnAutoReplenishMain.innerText = `⚡ Tải Sẵn Đủ ${h} Tiếng Stock (720p) Ngay`;
    }
    if (btnAutoReplenishModal && !btnAutoReplenishModal.disabled) {
      btnAutoReplenishModal.innerText = `⚡ Tự Động Tìm & Bù Đủ ${h} Tiếng Stock 720p (Không Cần Dán Link)`;
    }
  }

  function setupStockModal() {
    const mainModeSel = document.getElementById("stock-source-mode-select");
    const modalModeSel = document.getElementById("modal-stock-source-mode-select");
    if (mainModeSel) {
      mainModeSel.addEventListener("change", () => {
        switchStockSourceModeBackend(mainModeSel.value);
      });
    }
    if (modalModeSel) {
      modalModeSel.addEventListener("change", () => {
        switchStockSourceModeBackend(modalModeSel.value);
      });
    }

    if (targetStockHoursInput) {
      targetStockHoursInput.addEventListener("input", () => {
        updateReplenishButtonLabels(parseFloat(targetStockHoursInput.value) || 30);
      });
    }

    async function runAutoReplenishStock() {
      if (currentStockSourceMode === "local_available") {
        await switchStockSourceModeBackend("auto_download");
      }
      const targetHrs = targetStockHoursInput ? (parseFloat(targetStockHoursInput.value) || 30) : 30;
      if (btnAutoReplenishMain) {
        btnAutoReplenishMain.disabled = true;
        btnAutoReplenishMain.innerText = `⏳ Đang kiểm tra & tải bù đủ ${targetHrs}h (720p)...`;
      }
      if (btnAutoReplenishModal) {
        btnAutoReplenishModal.disabled = true;
        btnAutoReplenishModal.innerText = `⏳ Đang tìm & tải bù đủ ${targetHrs}h (720p)...`;
      }
      if (mainReplenishMsg) {
        mainReplenishMsg.classList.remove("hidden");
        mainReplenishMsg.style.display = "block";
        mainReplenishMsg.style.color = "var(--accent-cyan)";
        mainReplenishMsg.innerText = `⏳ Đang kiểm tra kho Stock (Mục tiêu: ${targetHrs} tiếng). Nếu thiếu hệ thống sẽ tự động tải từ Pexels / Pixabay / YouTube và cắt thành các part 30 phút...`;
      }
      if (ytDownloadMsg) {
        ytDownloadMsg.style.color = "var(--accent-cyan)";
        ytDownloadMsg.innerText = `⏳ Đang tự động tìm video 720p mới (Pexels / Pixabay / YouTube) và tải bù cho đủ ${targetHrs} tiếng...`;
      }

      try {
        const res = await fetch("/api/stocks/auto-replenish", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ target_hours: targetHrs, slice_minutes: 30 })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          const msg = data.message || `✅ Đã đảm bảo kho có đủ ${data.current_hours}h / ${targetHrs}h!`;
          if (mainReplenishMsg) {
            mainReplenishMsg.style.color = "var(--accent-green)";
            mainReplenishMsg.innerText = msg;
          }
          if (ytDownloadMsg) {
            ytDownloadMsg.style.color = "var(--accent-green)";
            ytDownloadMsg.innerText = msg;
          }
          await loadStocks();
        } else {
          const errMsg = `❌ Lỗi tải bù tự động: ${data.error || "Không thể tải thêm video"}`;
          if (mainReplenishMsg) {
            mainReplenishMsg.style.color = "var(--accent-red)";
            mainReplenishMsg.innerText = errMsg;
          }
          if (ytDownloadMsg) {
            ytDownloadMsg.style.color = "var(--accent-red)";
            ytDownloadMsg.innerText = errMsg;
          }
        }
      } catch (e) {
        const errMsg = `❌ Lỗi kết nối: ${e.message}`;
        if (mainReplenishMsg) {
          mainReplenishMsg.style.color = "var(--accent-red)";
          mainReplenishMsg.innerText = errMsg;
        }
        if (ytDownloadMsg) {
          ytDownloadMsg.style.color = "var(--accent-red)";
          ytDownloadMsg.innerText = errMsg;
        }
      } finally {
        if (btnAutoReplenishMain) btnAutoReplenishMain.disabled = false;
        if (btnAutoReplenishModal) btnAutoReplenishModal.disabled = false;
        updateReplenishButtonLabels(targetHrs);
      }
    }

    if (btnAutoReplenishMain) {
      btnAutoReplenishMain.addEventListener("click", runAutoReplenishStock);
    }
    if (btnAutoReplenishModal) {
      btnAutoReplenishModal.addEventListener("click", runAutoReplenishStock);
    }

    async function runSyncCloudNote() {
      if (btnSyncCloudMain) {
        btnSyncCloudMain.disabled = true;
        btnSyncCloudMain.innerText = "⏳ Đang đồng bộ Note...";
      }
      if (btnSyncCloudModal) {
        btnSyncCloudModal.disabled = true;
        btnSyncCloudModal.innerText = "⏳ Đang đồng bộ Note...";
      }
      if (cloudSyncMsg) {
        cloudSyncMsg.style.color = "var(--accent-cyan)";
        cloudSyncMsg.innerText = "⏳ Đang đồng bộ danh sách link Stock đã tải lên File Note Online riêng của Mexico Ông Già...";
      }
      if (mainReplenishMsg) {
        mainReplenishMsg.classList.remove("hidden");
        mainReplenishMsg.style.display = "block";
        mainReplenishMsg.style.color = "var(--accent-cyan)";
        mainReplenishMsg.innerText = "⏳ Đang đồng bộ danh sách link Stock với File Note Online riêng của Mexico Ông Già...";
      }

      try {
        const res = await fetch("/api/stocks/sync-cloud-note", { method: "POST" });
        const data = await res.json();
        if (res.ok && data.success) {
          const noteUrl = data.cloud_note_url || "https://rentry.co/mexico-ong-gia-stock-8a9b2c";
          const totalIds = data.total_synced_ids !== undefined ? data.total_synced_ids : 0;
          const pulledNew = data.new_from_cloud !== undefined ? data.new_from_cloud : 0;
          const msg = `✅ Đã đồng bộ File Note Online Mexico (${noteUrl})! Tổng số link đã khóa: ${totalIds} link (Nhận mới từ máy khác: +${pulledNew} | Đẩy lên Note: ${data.pushed_to_cloud ? "Thành công" : "Đã khớp"}).`;
          if (cloudSyncMsg) {
            cloudSyncMsg.style.color = "var(--accent-green)";
            cloudSyncMsg.innerText = msg;
          }
          if (mainReplenishMsg) {
            mainReplenishMsg.style.color = "var(--accent-green)";
            mainReplenishMsg.innerText = msg;
          }
          await loadStocks();
        } else {
          const errMsg = `⚠️ Không thể đồng bộ Note Online lúc này: ${data.error || "Mất kết nối mạng (Đang dùng bộ nhớ chống trùng cục bộ)"}`;
          if (cloudSyncMsg) {
            cloudSyncMsg.style.color = "var(--accent-gold)";
            cloudSyncMsg.innerText = errMsg;
          }
          if (mainReplenishMsg) {
            mainReplenishMsg.style.color = "var(--accent-gold)";
            mainReplenishMsg.innerText = errMsg;
          }
        }
      } catch (e) {
        const errMsg = `❌ Lỗi kết nối khi đồng bộ Note Online: ${e.message}`;
        if (cloudSyncMsg) {
          cloudSyncMsg.style.color = "var(--accent-red)";
          cloudSyncMsg.innerText = errMsg;
        }
      } finally {
        if (btnSyncCloudMain) {
          btnSyncCloudMain.disabled = false;
          btnSyncCloudMain.innerText = "☁️ Đồng Bộ Note Ngay";
        }
        if (btnSyncCloudModal) {
          btnSyncCloudModal.disabled = false;
          btnSyncCloudModal.innerText = "☁️ Đồng Bộ Note Ngay";
        }
      }
    }

    if (btnSyncCloudMain) {
      btnSyncCloudMain.addEventListener("click", runSyncCloudNote);
    }
    if (btnSyncCloudModal) {
      btnSyncCloudModal.addEventListener("click", runSyncCloudNote);
    }

    if (btnOpenStockModal && stockModal) {
      btnOpenStockModal.addEventListener("click", () => {
        stockModal.style.display = "flex";
        stockModal.classList.remove("hidden");
        loadStocks();
      });
    }

    if (btnCloseStockModal && stockModal) {
      btnCloseStockModal.addEventListener("click", () => {
        stockModal.style.display = "none";
        stockModal.classList.add("hidden");
      });
    }

    window.addEventListener("click", (e) => {
      if (e.target === stockModal && stockModal) {
        stockModal.style.display = "none";
        stockModal.classList.add("hidden");
      }
    });

    if (btnRescanStocks) {
      btnRescanStocks.addEventListener("click", async () => {
        btnRescanStocks.innerText = "Đang quét...";
        await fetch("/api/stocks/scan", { method: "POST" });
        await loadStocks();
        btnRescanStocks.innerText = "🔄 Quét Lại Kho";
      });
    }

    const btnResetAllStocks = document.getElementById("btn-reset-all-stocks");
    if (btnResetAllStocks) {
      btnResetAllStocks.addEventListener("click", async () => {
        btnResetAllStocks.disabled = true;
        btnResetAllStocks.innerText = "⏳ Đang đặt lại...";
        try {
          await fetch("/api/stocks/reset-all", { method: "POST" });
          await loadStocks();
        } catch (e) {
          alert("Lỗi đặt lại lượt dùng: " + e.message);
        } finally {
          btnResetAllStocks.disabled = false;
          btnResetAllStocks.innerText = "♻️ Đặt Lại Lượt Dùng";
        }
      });
    }

    if (btnCleanupUsedStocks) {
      btnCleanupUsedStocks.addEventListener("click", async () => {
        if (!confirm("Bạn có chắc chắn muốn xóa tất cả các file video stock ĐÃ DÙNG khỏi ổ cứng để giải phóng dung lượng đĩa?\n\n(Lưu ý: Hệ thống vẫn lưu vĩnh viễn lịch sử trên Link Note Online để bảo đảm TUYỆT ĐỐI KHÔNG BAO GIỜ bị tải trùng lại).")) {
          return;
        }
        btnCleanupUsedStocks.disabled = true;
        btnCleanupUsedStocks.innerText = "Đang dọn dẹp...";
        try {
          const res = await fetch("/api/stocks/cleanup-used", { method: "POST" });
          const data = await res.json();
          alert(data.message || `Đã dọn dẹp ${data.deleted_count} file stock đã dùng!`);
          await loadStocks();
        } catch (e) {
          alert("Lỗi dọn dẹp: " + e.message);
        } finally {
          btnCleanupUsedStocks.disabled = false;
          btnCleanupUsedStocks.innerText = "🗑️ Xóa File Đã Dùng";
        }
      });
    }

    if (btnYtDownload) {
      btnYtDownload.addEventListener("click", async () => {
        const url = ytUrlInput ? ytUrlInput.value.trim() : "";
        if (!url) {
          alert("Vui lòng dán link YouTube!");
          return;
        }
        await triggerYtDownload(url, false);
      });
    }

    async function triggerYtDownload(url, forceDownload) {
      btnYtDownload.disabled = true;
      btnYtDownload.innerText = "Đang tải & cắt part...";
      ytDownloadMsg.style.color = "var(--accent-cyan)";
      ytDownloadMsg.innerText = "⏳ Đang kiểm tra và tải video, sau đó tự động cắt thành các part 30 phút... Vui lòng chờ.";

      try {
        const res = await fetch("/api/stocks/download-youtube", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: url, slice_minutes: 30, force: forceDownload })
        });
        const data = await res.json();
        if (data.success) {
          ytDownloadMsg.style.color = "var(--accent-green)";
          ytDownloadMsg.innerText = `✅ Tải & Cắt thành công ${data.parts_count} part 30 phút vào kho STOOK!`;
          ytUrlInput.value = "";
          await loadStocks();
        } else if (data.already_exists) {
          ytDownloadMsg.style.color = "var(--accent-cyan)";
          ytDownloadMsg.innerHTML = `🛡️ <strong>ĐÃ TỒN TẠI TRONG KHO:</strong><br>${data.error}<br><button type="button" id="btn-force-yt-download" class="btn-tool-link" style="margin-top:6px;">⚠️ Vẫn tải lại (Ghi đè)</button>`;
          const btnForce = document.getElementById("btn-force-yt-download");
          if (btnForce) {
            btnForce.addEventListener("click", () => triggerYtDownload(url, true));
          }
        } else {
          ytDownloadMsg.style.color = "var(--accent-red)";
          ytDownloadMsg.innerText = `❌ Lỗi: ${data.error || "Không thể tải video"}`;
        }
      } catch (e) {
        ytDownloadMsg.style.color = "var(--accent-red)";
        ytDownloadMsg.innerText = `❌ Lỗi kết nối: ${e.message}`;
      } finally {
        btnYtDownload.disabled = false;
        btnYtDownload.innerText = "Tải & Cắt Part 30p";
      }
    }
  }

  // 8. Bắt đầu sản xuất
  function setupProductionTrigger() {
    if (btnProduce) btnProduce.addEventListener("click", async () => {
      await checkLicenseStatus();
      if (!isLicenseValid) {
        if (licenseModal) licenseModal.style.display = "flex";
        return;
      }

      const outputDir = outputDirInput.value.trim() || null;
      const channel = channelNameInput.value.trim() || ".";
      const rawBgm = bgmVolSlider ? parseFloat(bgmVolSlider.value) : 8;
      const bgmVol = isNaN(rawBgm) ? 0.08 : (rawBgm <= 1.0 ? rawBgm : rawBgm / 100.0);

      // KIỂM TRA QUY ĐỊNH NGHIÊM NGẶT: TUYỆT ĐỐI KHÔNG DÙNG LẠI STOCK ĐÃ DÙNG
      if (stockSelect && stockSelect.value && stockSelect.value !== "auto_unique") {
        const selOpt = stockSelect.options[stockSelect.selectedIndex];
        if (selOpt && selOpt.disabled) {
          alert("❌ Video stock này đã qua sử dụng! Theo quy định nghiêm ngặt, tuyệt đối không được dùng lại stock đã dùng.\nVui lòng chọn video khả dụng khác hoặc chọn 'Tự động chọn Stock chưa dùng (Chống trùng 100%)'.");
          return;
        }
      }

      let endpoint = "/api/start";
      let payload = {};
      const isLocalStockMode = currentStockSourceMode === "local_available";
      const shouldDeleteUsedStocks = !isLocalStockMode && (autoDeleteStock ? autoDeleteStock.checked : true);
      const shouldAutoEnsureStock = !isLocalStockMode && (autoEnsureStock ? autoEnsureStock.checked : true);
      const targetStockHours = targetStockHoursInput ? (parseFloat(targetStockHoursInput.value) || 30.0) : 30.0;
      const effectiveStockSelection = (stockSelect && stockSelect.value && stockSelect.value !== "auto_unique")
        ? stockSelect.value
        : currentStockSourceMode;

      if (currentMode === "adas") {
        const runAllBtn = document.getElementById("btn-adas-run-all");
        if (runAllBtn) runAllBtn.click();
        return;
      }

      if (currentMode === "single") {
        const script = scriptTextInput ? scriptTextInput.value.trim() : "";
        if (!script) {
          // Chế độ mặc định (Đã ẩn Kịch Bản Đơn thủ công): Lấy trực tiếp dự án từ Kho ADAS để xuất Video MP4
          const targetSel = document.getElementById("render-adas-target-select");
          const chosenTarget = targetSel ? targetSel.value : "ALL_READY";
          if (chosenTarget && chosenTarget !== "ALL_READY") {
            await triggerRenderOnly([chosenTarget], false);
            return;
          }
          const res = await fetch("/api/adas/ideas");
          if (res.ok) {
            const data = await res.json();
            const readyIds = (data.ideas || [])
              .filter((it) => (!!it.has_script && (it.pure_char_count || 0) >= 35000) && (!it.has_video_mp4 || it.status !== "COMPLETED_VIDEO"))
              .map((it) => it.ma_id);
            if (readyIds.length > 0) {
              await triggerRenderOnly(readyIds, true);
              return;
            }
            alert("Hiện chưa có dự án nào trong Kho ADAS đang chờ xuất MP4 (Hoặc toàn bộ đã xuất xong MP4).\n\nBạn có thể chọn 1 mã cụ thể ở mục 'Nguồn Kịch Bản Xuất Video (Từ Kho ADAS)' bên trái để xuất lại!");
            return;
          }
          return;
        }

        endpoint = "/api/start";
        payload = {
          script_text: script,
          project_name: projectNameInput ? (projectNameInput.value.trim() || null) : null,
          output_dir: outputDir,
          channel_name: channel,
          resolution: selectedResolution,
          fps: selectedFps,
          stock_selection: effectiveStockSelection,
          bgm_volume: bgmVol,
          delete_used_stocks: shouldDeleteUsedStocks,
          auto_ensure_stock_hours: shouldAutoEnsureStock,
          target_stock_hours: targetStockHours,
          voice_config: getCurrentVoiceConfigFromUI()
        };
      } else {
        // BATCH MODE
        if (batchQueue.length === 0) {
          alert("Hàng đợi kịch bản đang trống! Vui lòng bấm 'Chọn Nhiều File Kịch Bản (.txt)' trước.");
          return;
        }

        endpoint = "/api/start-batch";
        payload = {
          jobs: batchQueue.map(j => ({ name: j.name, script_text: j.script_text })),
          output_dir: outputDir,
          channel_name: channel,
          resolution: selectedResolution,
          fps: selectedFps,
          stock_selection: effectiveStockSelection,
          bgm_volume: bgmVol,
          delete_used_stocks: shouldDeleteUsedStocks,
          auto_ensure_stock_hours: shouldAutoEnsureStock,
          target_stock_hours: targetStockHours,
          voice_config: getCurrentVoiceConfigFromUI()
        };
      }

      btnProduce.disabled = true;
      btnProduce.style.opacity = "0.6";
      progressSection.style.display = "block";
      deliverablesBox.style.display = "none";
      progressBar.style.width = "2%";
      progressPct.innerText = "2%";
      progressMsg.innerText = "Đang bắt đầu tiến trình...";

      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Không thể khởi động");
        }
      } catch (e) {
        alert("Lỗi: " + e.message);
        btnProduce.disabled = false;
        btnProduce.style.opacity = "1";
        progressSection.style.display = "none";
      }
    });

    // Deliverables Buttons
    if (btnWatchVideo) {
      btnWatchVideo.addEventListener("click", async () => {
        const target = currentResults.length > 0 ? currentResults[0] : null;
        if (target && target.final_video) {
          await openSystemVideo(target.final_video);
        }
      });
    }

    if (btnOpenDir) {
      btnOpenDir.addEventListener("click", async () => {
        const target = currentResults.length > 0 ? currentResults[0] : null;
        const targetPath = (target && target.project_dir) ? target.project_dir : (outputDirInput ? outputDirInput.value.trim() : "");
        if (targetPath) {
          await openSystemFolder(targetPath);
        }
      });
    }

    if (btnCopySrt) {
      btnCopySrt.addEventListener("click", () => {
        const target = currentResults.length > 0 ? currentResults[0] : null;
        if (target && target.subtitles_srt) {
          navigator.clipboard.writeText(target.subtitles_srt);
          alert("Đã sao chép đường dẫn file SRT: " + target.subtitles_srt);
        }
      });
    }

    if (btnCopyChapters) {
      btnCopyChapters.addEventListener("click", () => {
        const target = currentResults.length > 0 ? currentResults[0] : null;
        if (target && target.timestamps_txt) {
          navigator.clipboard.writeText(target.timestamps_txt);
          alert("Đã sao chép đường dẫn file Chapters: " + target.timestamps_txt);
        }
      });
    }
  }

  // 9. WebSocket Tiến Trình Thời Gian Thực
  function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${location.host}/ws`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("[WebSocket] Kết nối thời gian thực thành công!");
    };

    socket.onmessage = (event) => {
      try {
        const state = JSON.parse(event.data);
        handleStateUpdate(state);
      } catch (e) {
        console.error("Lỗi parse WebSocket message:", e);
      }
    };

    socket.onclose = () => {
      setTimeout(connectWebSocket, 3000);
    };

    // Đồng bộ ngay khi kết nối và lặp lại mỗi 2.5 giây
    const syncStatusNow = async () => {
      try {
        const res = await fetch("/api/status");
        if (res.ok) {
          const state = await res.json();
          handleStateUpdate(state);
        }
      } catch (e) {
        // Bỏ qua lỗi tạm thời
      }
    };
    syncStatusNow();
    setInterval(syncStatusNow, 2500);
  }

  let latestVideoPipelineState = null;
  let lastSavedIdeasCache = [];
  let lastAdasIdeasLoadTs = 0;
  let lastAdasStepKey = "";

  function handleStateUpdate(state) {
    if (!state) return;

    if (state.type === "sys_log" && state.entry) {
      pushLogEntryToConsole(state.entry);
      return;
    }

    if (state.type === "adas_update" && state.adas_state) {
      updateADASLiveUI(state.adas_state);
      const now = Date.now();
      const stepKey = `${state.adas_state.status || ""}|${state.adas_state.current_ma_id || ""}|${state.adas_state.current_step || ""}`;
      if (stepKey !== lastAdasStepKey || (now - lastAdasIdeasLoadTs >= 4000)) {
        lastAdasStepKey = stepKey;
        lastAdasIdeasLoadTs = now;
        const listEl = document.getElementById("adas-ideas-list");
        // Không ghi đè DOM khi người dùng đang rê chuột vào danh sách dự án để bấm nút Mở Folder / Xem / Render
        if (!listEl || !listEl.matches(":hover")) {
          loadSavedIdeas();
        }
      }
      return;
    }

    const prevStatus = latestVideoPipelineState ? latestVideoPipelineState.status : null;
    const prevPct = latestVideoPipelineState ? Math.round(latestVideoPipelineState.progress || 0) : -1;
    latestVideoPipelineState = state;
    if (state.hardware_load) {
      const g = Math.round(state.hardware_load.gpu_percent || 0);
      const c = Math.round(state.hardware_load.cpu_percent || 0);
      const balEl = document.getElementById("gpu-balancer-badge");
      if (balEl) {
        balEl.innerText = `⚡ Tự cân đối 90%: GPU ${g}% • CPU ${c}%`;
      }
      const gpuPctEl = document.getElementById("gauge-gpu-pct");
      const gpuBarEl = document.getElementById("gauge-gpu-bar");
      const cpuPctEl = document.getElementById("gauge-cpu-pct");
      const cpuBarEl = document.getElementById("gauge-cpu-bar");
      if (gpuPctEl) gpuPctEl.innerText = `${g}%`;
      if (gpuBarEl) gpuBarEl.style.width = `${Math.max(4, Math.min(100, g))}%`;
      if (cpuPctEl) cpuPctEl.innerText = `${c}%`;
      if (cpuBarEl) cpuBarEl.style.width = `${Math.max(4, Math.min(100, c))}%`;
    }
    const curPct = Math.round(state.progress || 0);
    if (lastSavedIdeasCache.length > 0 && (prevStatus !== state.status || prevPct !== curPct)) {
      renderSavedIdeasList(lastSavedIdeasCache);
    }

    if (state.status === "running") {
      progressSection.style.display = "block";
      deliverablesBox.style.display = "none";
      btnProduce.disabled = true;
      btnProduce.style.opacity = "0.6";

      const pct = Math.max(2, Math.min(100, state.progress || 0));
      progressBar.style.width = `${pct}%`;
      progressPct.innerText = `${pct.toFixed(0)}%`;
      progressMsg.innerText = state.message || "Đang xử lý...";

      const totalJobs = state.batch_total || 1;
      const activeJobs = Array.isArray(state.active_jobs) ? state.active_jobs : [];
      const doneJobsCount = typeof state.completed_count === "number" ? state.completed_count : ((state.results || []).length);
      const pendingJobsCount = typeof state.pending_count === "number" ? state.pending_count : Math.max(0, totalJobs - doneJobsCount - activeJobs.length);

      progressStageName.innerText = `📊 Tiến độ lô: Đang chạy ${activeJobs.length} video song song • Đã xong: ${doneJobsCount}/${totalJobs} video • Chờ: ${pendingJobsCount} video`;

      const sec = state.elapsed_seconds || 0;
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      progressTime.innerText = `Thời gian tổng: ${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;

      renderActiveVideoJobBoxes(activeJobs);
    } else if (state.status === "completed") {
      progressBar.style.width = "100%";
      progressPct.innerText = "100%";
      progressMsg.innerText = state.message || "Sản xuất hoàn tất!";
      btnProduce.disabled = false;
      btnProduce.style.opacity = "1";
      renderActiveVideoJobBoxes([]);

      currentResults = state.results || [];
      deliverablesBox.style.display = "block";
      deliverablesTitle.innerText = currentResults.length > 1
        ? `🎉 HOÀN TẤT THÀNH CÔNG HÀNG ĐỢI ${currentResults.length} VIDEO!`
        : `🎉 SẢN XUẤT HOÀN TẤT THÀNH CÔNG!`;

      loadStocks();
    } else if (state.status === "error") {
      progressMsg.innerText = state.message || "Có lỗi xảy ra";
      progressMsg.style.color = "var(--accent-red)";
      btnProduce.disabled = false;
      btnProduce.style.opacity = "1";
      renderActiveVideoJobBoxes([]);
    }
  }

  function renderActiveVideoJobBoxes(activeJobs) {
    const listContainer = document.getElementById("multi-video-jobs-list");
    if (!listContainer) return;

    if (!Array.isArray(activeJobs) || activeJobs.length === 0) {
      listContainer.classList.add("hidden");
      listContainer.classList.remove("flex");
      listContainer.innerHTML = "";
      return;
    }

    listContainer.classList.remove("hidden");
    listContainer.classList.add("flex");

    const activeIdsSet = new Set(activeJobs.map((j) => String(j.project_name || "")));
    listContainer.querySelectorAll("[data-video-job-id]").forEach((rowEl) => {
      if (!activeIdsSet.has(rowEl.getAttribute("data-video-job-id") || "")) {
        rowEl.remove();
      }
    });

    activeJobs.forEach((job) => {
      const projId = String(job.project_name || "VIDEO");
      const stageLbl = String(job.stage_label || "Đang xử lý");
      const detailTxt = String(job.detail || "Đang xử lý...");
      const jobPct = Math.max(1, Math.min(100, Number(job.progress || 0)));
      const elap = Math.max(0, Number(job.elapsed_seconds || 0));
      const mm = String(Math.floor(elap / 60)).padStart(2, "0");
      const ss = String(elap % 60).padStart(2, "0");

      let rowEl = listContainer.querySelector(`[data-video-job-id="${projId}"]`);
      if (!rowEl) {
        rowEl = document.createElement("div");
        rowEl.setAttribute("data-video-job-id", projId);
        rowEl.className = "video-job-row p-2.5 rounded-md bg-surface-container border border-surface-container-highest flex flex-col gap-1.5 shadow-sm";
        rowEl.innerHTML = `
          <div class="flex items-center justify-between gap-2 text-xs font-mono">
            <div class="flex items-center gap-1.5 min-w-0 flex-1">
              <span class="px-1.5 py-0.5 rounded bg-primary-container/20 text-primary-container font-bold border border-primary-container/40 shrink-0">#${projId}</span>
              <span class="vjob-stage-badge px-1.5 py-0.5 rounded bg-secondary-container/20 text-secondary border border-secondary/30 text-[10.5px] font-semibold shrink-0"></span>
              <span class="vjob-detail-text text-on-surface text-[11px] truncate flex-1"></span>
            </div>
            <div class="flex items-center gap-2.5 shrink-0">
              <span class="vjob-time-text text-[10.5px] text-on-surface-variant"></span>
              <span class="vjob-pct-text font-bold text-primary-container min-w-[40px] text-right"></span>
            </div>
          </div>
          <div class="w-full h-1.5 bg-surface-container-lowest rounded overflow-hidden">
            <div class="vjob-bar-fill h-full bg-gradient-to-r from-secondary to-primary-container rounded transition-all duration-300" style="width: 1%;"></div>
          </div>
        `;
        listContainer.appendChild(rowEl);
      }

      const stageBadgeEl = rowEl.querySelector(".vjob-stage-badge");
      const detailEl = rowEl.querySelector(".vjob-detail-text");
      const timeEl = rowEl.querySelector(".vjob-time-text");
      const pctEl = rowEl.querySelector(".vjob-pct-text");
      const barEl = rowEl.querySelector(".vjob-bar-fill");

      if (stageBadgeEl && stageBadgeEl.innerText !== stageLbl) stageBadgeEl.innerText = stageLbl;
      if (detailEl && detailEl.innerText !== detailTxt) {
        detailEl.innerText = detailTxt;
        detailEl.title = `[#${projId}] ${stageLbl} — ${detailTxt}`;
      }
      if (timeEl) timeEl.innerText = `⏱ ${mm}:${ss}`;
      if (pctEl) pctEl.innerText = `${jobPct.toFixed(1)}%`;
      if (barEl) barEl.style.width = `${jobPct}%`;
    });
  }

  // 10. Hệ thống Khóa & Kích hoạt Bản Quyền (License Gate)
  function setupLicenseSystem() {
    if (btnOpenLicenseModal) {
      btnOpenLicenseModal.addEventListener("click", async () => {
        await checkLicenseStatus();
        if (licenseModal) licenseModal.style.display = "flex";
      });
    }

    if (btnCloseLicenseModal) {
      btnCloseLicenseModal.addEventListener("click", () => {
        if (isLicenseValid && licenseModal) {
          licenseModal.style.display = "none";
        }
      });
    }

    if (btnCopyHwid) {
      btnCopyHwid.addEventListener("click", () => {
        const hwid = licenseHwidText ? licenseHwidText.innerText.trim() : "";
        if (hwid) {
          navigator.clipboard.writeText(hwid);
          const orig = btnCopyHwid.innerText;
          btnCopyHwid.innerText = "✅ Đã Copy!";
          setTimeout(() => { btnCopyHwid.innerText = orig; }, 2000);
        }
      });
    }

    if (btnActivateLicense) {
      btnActivateLicense.addEventListener("click", async () => {
        const keyStr = licenseKeyInput ? licenseKeyInput.value.trim() : "";
        if (!keyStr) {
          if (licenseModalMsg) {
            licenseModalMsg.style.color = "var(--accent-red)";
            licenseModalMsg.innerText = "⚠️ Vui lòng dán mã Key bản quyền vào ô bên trên!";
          }
          return;
        }

        btnActivateLicense.disabled = true;
        btnActivateLicense.innerText = "⏳ ĐANG KIỂM TRA & KÍCH HOẠT...";
        if (licenseModalMsg) {
          licenseModalMsg.style.color = "var(--accent-cyan)";
          licenseModalMsg.innerText = "Đang xác thực chữ ký số và thời hạn Key...";
        }

        try {
          const res = await fetch("/api/license/activate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ license_key: keyStr })
          });
          const data = await res.json();
          if (res.ok && data.valid) {
            if (licenseModalMsg) {
              licenseModalMsg.style.color = "var(--accent-green)";
              licenseModalMsg.innerText = data.message || "✅ Kích hoạt bản quyền thành công!";
            }
            await checkLicenseStatus();
            setTimeout(() => {
              if (licenseModal) licenseModal.style.display = "none";
            }, 1000);
          } else {
            if (licenseModalMsg) {
              licenseModalMsg.style.color = "var(--accent-red)";
              licenseModalMsg.innerText = data.detail || data.message || "❌ Mã Key không hợp lệ hoặc đã hết hạn!";
            }
          }
        } catch (e) {
          if (licenseModalMsg) {
            licenseModalMsg.style.color = "var(--accent-red)";
            licenseModalMsg.innerText = "❌ Lỗi kết nối khi kích hoạt: " + e.message;
          }
        } finally {
          btnActivateLicense.disabled = false;
          btnActivateLicense.innerText = "🔓 KÍCH HOẠT / GIA HẠN BẢN QUYỀN NGAY";
        }
      });
    }
  }

  async function checkLicenseStatus() {
    try {
      const res = await fetch("/api/license/status");
      const data = await res.json();
      isLicenseValid = !!data.valid;

      if (licenseHwidText && data.hwid) {
        licenseHwidText.innerText = data.hwid;
      }

      if (data.valid) {
        if (licenseBadgeText) {
          licenseBadgeText.innerText = `Bản Quyền: Còn ${data.days_remaining} ngày (${data.expiry_formatted})`;
        }
        if (btnOpenLicenseModal) {
          btnOpenLicenseModal.style.borderColor = "rgba(0, 230, 118, 0.5)";
          btnOpenLicenseModal.style.background = "rgba(0, 230, 118, 0.12)";
          btnOpenLicenseModal.style.color = "var(--accent-green)";
        }
        if (licModalStatus) {
          licModalStatus.style.color = "var(--accent-green)";
          licModalStatus.innerText = `✅ Đang hoạt động (Còn ${data.days_remaining} ngày)`;
        }
        if (licModalPlan) licModalPlan.innerText = `${data.plan_label || ""} — ${data.mode_label || ""}`;
        if (licModalExpiry) licModalExpiry.innerText = data.expiry_formatted || "--/--/----";
        if (licenseKeyInput && data.license_key && !licenseKeyInput.value) {
          licenseKeyInput.value = data.license_key;
        }
        if (btnCloseLicenseModal) btnCloseLicenseModal.style.display = "block";
      } else {
        if (licenseBadgeText) {
          licenseBadgeText.innerText = data.status === "expired" ? "⛔ KEY ĐÃ HẾT HẠN" : "🔒 CHƯA KÍCH HOẠT KEY";
        }
        if (btnOpenLicenseModal) {
          btnOpenLicenseModal.style.borderColor = "rgba(255, 75, 75, 0.6)";
          btnOpenLicenseModal.style.background = "rgba(255, 75, 75, 0.15)";
          btnOpenLicenseModal.style.color = "#ff6b6b";
        }
        if (licModalStatus) {
          licModalStatus.style.color = "var(--accent-red)";
          licModalStatus.innerText = data.message || "Chưa kích hoạt hoặc đã hết hạn";
        }
        if (licModalPlan) licModalPlan.innerText = data.plan_label || "Chưa kích hoạt";
        if (licModalExpiry) licModalExpiry.innerText = data.expiry_formatted || "--/--/----";
        if (btnCloseLicenseModal) btnCloseLicenseModal.style.display = "none";
        if (licenseModal) licenseModal.style.display = "flex";
      }
    } catch (e) {
      console.warn("Không thể kiểm tra trạng thái bản quyền:", e);
    }
  }

  // ============================================================================
  // 11. HỆ THỐNG 3 TÀI KHOẢN CHATGPT WEB & DÂY CHUYỀN ADAS (STEP 2 -> STEP 6)
  // ============================================================================
  let currentProjectDetailData = null;

  async function openSystemFolder(targetPath) {
    if (!targetPath) return;
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.open_folder) {
        const res = await window.pywebview.api.open_folder(targetPath);
        if (res && res.success) return;
      }
    } catch (e) {
      console.warn("pywebview open_folder fallback:", e);
    }
    await fetch("/api/open-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: targetPath })
    });
  }

  async function openSystemVideo(targetPath) {
    if (!targetPath) return;
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.open_video) {
        const res = await window.pywebview.api.open_video(targetPath);
        if (res && res.success) return;
      }
    } catch (e) {
      console.warn("pywebview open_video fallback:", e);
    }
    await fetch("/api/open-video", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: targetPath })
    });
  }

  let activeGpuServerMode = "voicevox_gpu";

  function getCurrentVoiceConfigFromUI() {
    const mainSel = document.getElementById("voice-preset-select");
    const adasSel = document.getElementById("adas-voice-select");
    const speedRange = document.getElementById("voice-speed-range");
    const pitchRange = document.getElementById("voice-pitch-range");
    const intoRange = document.getElementById("voice-intonation-range");
    const pauseRange = document.getElementById("voice-pause-range");

    const selectedId = (mainSel && mainSel.value) || (adasSel && adasSel.value) || "Drama";
    const presetObj = (voicePresetsCache || []).find((p) => p.id === selectedId) || null;
    const isOmni = activeGpuServerMode === "omnivoice_gpu" || (presetObj && presetObj.engine === "omnivoice");

    const activePerfMode = localStorage.getItem("studio_perf_mode") || "full_100";
    return {
      active_gpu_server: isOmni ? "omnivoice_gpu" : "voicevox_gpu",
      engine_mode: isOmni ? "omnivoice" : "voicevox",
      selected_preset_id: selectedId,
      speaker_id: presetObj ? presetObj.speaker_id : 13,
      speedScale: speedRange ? parseFloat(speedRange.value) : 0.97,
      pitchScale: pitchRange ? parseFloat(pitchRange.value) : -0.02,
      intonationScale: intoRange ? parseFloat(intoRange.value) : 0.95,
      pauseLengthScale: pauseRange ? parseFloat(pauseRange.value) : 1.12,
      volumeScale: presetObj ? (presetObj.volumeScale || 1.05) : 1.05,
      ref_wav: presetObj ? (presetObj.ref_wav || "Drama.wav") : "Drama.wav",
      performance_mode: activePerfMode
    };
  }

  function getCurrentVideoSettings() {
    const rawBgm = bgmVolSlider ? parseFloat(bgmVolSlider.value) : 8;
    const bgmVol = isNaN(rawBgm) ? 0.08 : (rawBgm <= 1.0 ? rawBgm : rawBgm / 100.0);
    const activePerfMode = localStorage.getItem("studio_perf_mode") || "full_100";
    const isLocalStockMode = currentStockSourceMode === "local_available";
    const effectiveSel = (stockSelect && stockSelect.value && stockSelect.value !== "auto_unique")
      ? stockSelect.value
      : currentStockSourceMode;
    return {
      output_dir: outputDirInput ? outputDirInput.value.trim() : "",
      channel_name: (channelNameInput ? channelNameInput.value.trim() : "") || ".",
      resolution: selectedResolution,
      fps: selectedFps,
      stock_selection: effectiveSel,
      bgm_volume: bgmVol,
      delete_used_stocks: !isLocalStockMode && (autoDeleteStock ? autoDeleteStock.checked : true),
      auto_ensure_stock_hours: !isLocalStockMode && (autoEnsureStock ? autoEnsureStock.checked : true),
      target_stock_hours: targetStockHoursInput ? parseFloat(targetStockHoursInput.value) || 30.0 : 30.0,
      performance_mode: activePerfMode,
      voice_config: getCurrentVoiceConfigFromUI()
    };
  }

  function updateADASLiveUI(st) {
    if (!st) return;
    const stepEl = document.getElementById("adas-current-step-text");
    const pctEl = document.getElementById("adas-progress-pct");
    const barEl = document.getElementById("adas-progress-bar");
    const msgEl = document.getElementById("adas-status-msg");
    const stopBtn = document.getElementById("btn-adas-stop");
    const threadEl = document.getElementById("adas-thread-status");

    const pct = Math.max(0, Math.min(100, Math.round(st.progress || 0)));
    if (stepEl) {
      stepEl.innerText = `🤖 Trạng thái Agent: ${st.current_step || "Sẵn sàng"}${st.current_ma_id ? " [" + st.current_ma_id + "]" : ""}`;
    }
    if (pctEl) {
      pctEl.innerText = `${pct}%`;
    }
    if (barEl) {
      barEl.style.width = `${pct}%`;
    }
    if (msgEl) {
      msgEl.innerText = st.message || "";
      msgEl.style.color = st.status === "error" ? "var(--accent-red)" : st.status === "completed" ? "var(--accent-green)" : "var(--text-primary)";
    }
    if (stopBtn) {
      if (st.status === "running") {
        stopBtn.style.display = "inline-flex";
        stopBtn.classList.remove("hidden");
      } else {
        stopBtn.style.display = "none";
        stopBtn.classList.add("hidden");
      }
    }
    if (threadEl) {
      threadEl.innerText = st.status === "running"
        ? `● LUỒNG ĐANG CHẠY (${st.current_ma_id || "ADAS"})`
        : "● LUỒNG ĐANG SẴN SÀNG";
    }
  }

  async function refreshChatGPTAccountsBar(force = false) {
    try {
      const res = await fetch(`/api/chatgpt/status?force=${force ? "true" : "false"}`);
      if (!res.ok) return;
      const data = await res.json();
      const accs = data.accounts || {};
      let savedCount = 0;
      let openCount = 0;

      ["acc_1", "acc_2", "acc_3", "acc_4", "acc_5"].forEach((aid, idx) => {
        const btn = document.getElementById(`btn-chatgpt-acc-${idx + 1}`);
        if (!btn) return;
        const info = accs[aid] || {};
        const isBrowserOpen = !!info.browser_open;
        const isSavedOrLogged = !!(info.logged_in || info.saved_logged_in);
        if (isBrowserOpen) openCount += 1;
        if (isSavedOrLogged) savedCount += 1;

        const port = info.port || (9232 + idx);
        const activeJobs = (info.active_projects || []).length;
        const rawEmail = (info.user_email || info.email || "").trim();
        const shortEmail = (rawEmail && rawEmail.includes("@"))
          ? (rawEmail.split("@")[0].slice(0, 12) + (rawEmail.split("@")[0].length > 12 ? "…" : ""))
          : "";

        if (isBrowserOpen && isSavedOrLogged) {
          const busyTag = activeJobs > 0 ? ` • 🔥 Chạy ${activeJobs}` : " • Đang bật";
          const mailTag = shortEmail ? ` (${shortEmail})` : ` (${port})`;
          btn.className = "chatgpt-acc-btn flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-high border border-primary-container text-primary-container font-label-sm text-[11px] font-bold shadow-[0_0_8px_rgba(0,255,135,0.25)]";
          btn.innerHTML = `<span class="w-2 h-2 rounded-full bg-primary-container animate-pulse"></span>Acc #${idx + 1}${mailTag}${busyTag}`;
          btn.title = `Acc #${idx + 1} (Cổng ${port}) — Đang bật Chrome (${rawEmail || "Đã đăng nhập"}). Hệ thống sẽ tự động tắt khi viết xong!`;
        } else if (!isBrowserOpen && isSavedOrLogged) {
          const mailTag = shortEmail ? ` (${shortEmail})` : ` (${port})`;
          btn.className = "chatgpt-acc-btn flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container hover:bg-surface-container-high border border-primary-container/40 text-primary-container font-label-sm text-[11px] font-semibold";
          btn.innerHTML = `<span class="w-2 h-2 rounded-full bg-primary-container"></span>Acc #${idx + 1}${mailTag} • Đã lưu`;
          btn.title = `Acc #${idx + 1} (Cổng ${port}) — ĐÃ LƯU ĐĂNG NHẬP (${rawEmail}). Đang tắt Chrome tiết kiệm RAM, tự bật khi dùng hoặc bấm để mở!`;
        } else if (isBrowserOpen && !isSavedOrLogged) {
          btn.className = "chatgpt-acc-btn flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-high border border-tertiary text-tertiary font-label-sm text-[11px] font-bold";
          btn.innerHTML = `<span class="w-2 h-2 rounded-full bg-tertiary animate-ping"></span>Acc #${idx + 1} (${port}) • Chờ Login`;
          btn.title = `Acc #${idx + 1} (Cổng ${port}) — Đang mở Chrome để bạn đăng nhập ChatGPT. Đăng nhập xong hệ thống sẽ tự lưu lại!`;
        } else {
          btn.className = "chatgpt-acc-btn flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container/60 hover:bg-surface-container-high border border-outline-variant/25 text-on-surface-variant/75 font-label-sm text-[11px]";
          btn.innerHTML = `<span class="w-2 h-2 rounded-full bg-outline-variant/50"></span>Acc #${idx + 1} (${port}) • Chưa Login`;
          btn.title = `Acc #${idx + 1} (Cổng ${port}) — Chưa đăng nhập (Sẽ KHÔNG tự động mở). Bấm vào đây nếu muốn đăng nhập thêm tài khoản thứ #${idx + 1}!`;
        }
      });

      const summaryLbl = document.getElementById("chatgpt-bar-summary-label");
      if (summaryLbl) {
        summaryLbl.innerText = `ChatGPT (${savedCount}/5 Đã Lưu${openCount > 0 ? ` • ${openCount} Đang Bật` : " • Đang Tắt Chrome"}):`;
      }

      const cdpBadge = document.getElementById("adas-cdp-linked-badge");
      if (cdpBadge) {
        cdpBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-primary-container animate-ping"></span>CDP LINKED (${savedCount}/5 ACC ĐÃ LƯU)`;
      }

      const addBtn = document.getElementById("btn-chatgpt-add-acc");
      if (addBtn) {
        if (savedCount >= 5) {
          addBtn.innerHTML = `<span>✅ Đủ 5/5 Acc</span>`;
        } else {
          addBtn.innerHTML = `<span>➕ Thêm Acc (#${savedCount + 1}/5)</span>`;
        }
      }

      const closeAllBtn = document.getElementById("btn-chatgpt-close-all");
      if (closeAllBtn) {
        closeAllBtn.style.opacity = openCount > 0 ? "1" : "0.6";
        closeAllBtn.innerHTML = openCount > 0
          ? `<span class="material-symbols-outlined text-[15px]">power_settings_new</span><span>Tắt Chrome (${openCount})</span>`
          : `<span class="material-symbols-outlined text-[15px]">check_circle</span><span>Chrome Đã Tắt</span>`;
      }

      const visBtn = document.getElementById("btn-chatgpt-toggle-vis");
      if (visBtn) {
        const isHidden = !!data.chrome_hidden;
        visBtn.dataset.visible = isHidden ? "false" : "true";
        visBtn.innerHTML = isHidden
          ? `<span class="material-symbols-outlined text-[15px]">visibility</span>Hiện Lại Cửa Sổ Chrome`
          : `<span class="material-symbols-outlined text-[15px]">visibility_off</span>Ẩn Ngầm Chrome (-3200)`;
      }
    } catch (e) {
      // Bỏ qua lỗi tạm thời
    }
  }

  async function loadSavedIdeas() {
    try {
      const res = await fetch("/api/adas/ideas");
      if (!res.ok) return;
      const data = await res.json();
      if (data.state) updateADASLiveUI(data.state);
      renderSavedIdeasList(data.ideas || []);
    } catch (e) {
      console.warn("Lỗi tải danh sách ý tưởng ADAS:", e);
    }
  }

  let currentAdasFilter = "all";
  let currentAdasTitleMode = (window.currentAdasTitleMode || localStorage.getItem("adas_title_mode")) === "original" ? "original" : "rewrite";
  window.currentAdasTitleMode = currentAdasTitleMode;

  function applyAdasTitleModeUI(mode, syncBackend = false) {
    currentAdasTitleMode = mode === "original" ? "original" : "rewrite";
    window.currentAdasTitleMode = currentAdasTitleMode;
    try {
      localStorage.setItem("adas_title_mode", currentAdasTitleMode);
    } catch (e) {}
    if (typeof window.selectAdasTitleMode === "function") {
      window.selectAdasTitleMode(currentAdasTitleMode, syncBackend);
    }
  }
  let adasVisibleLimit = 25;

  function renderSavedIdeasList(ideas) {
    lastSavedIdeasCache = ideas || [];
    const countEl = document.getElementById("adas-ideas-count");
    const listEl = document.getElementById("adas-ideas-list");
    if (countEl) countEl.innerText = ideas.length;
    if (!listEl) return;

    const classifyDone = (it) => {
      const pureCount = it.pure_char_count || 0;
      const doneParts = typeof it.completed_parts_count === "number"
        ? it.completed_parts_count
        : (pureCount >= 35000 ? 3 : pureCount >= 24000 ? 2 : pureCount >= 9500 ? 1 : 0);
      return !!it.has_script && pureCount >= 35000 && doneParts >= 3;
    };

    const isVideoTrulyCompleted = (it) => !!it.has_video_mp4 && it.status === "COMPLETED_VIDEO";

    const doneIdeas = ideas.filter((it) => classifyDone(it));
    const pendingIdeas = ideas.filter((it) => !classifyDone(it));
    const renderedIdeas = ideas.filter((it) => isVideoTrulyCompleted(it));
    const readyUnrendered = doneIdeas.filter((it) => !isVideoTrulyCompleted(it));
    const videoErrorCount = readyUnrendered.filter((it) => it.status === "ERROR_VIDEO").length;
    const mp4DoneCount = renderedIdeas.length;

    const renderSummaryEl = document.getElementById("render-adas-ready-summary");
    if (renderSummaryEl) {
      const errNote = videoErrorCount > 0 ? ` (Gồm ${videoErrorCount} video lỗi/ngắt cần chạy lại)` : "";
      renderSummaryEl.innerText = `✅ Chờ xuất MP4: ${readyUnrendered.length} mã${errNote} • Đã có MP4: ${mp4DoneCount} mã`;
    }
    const renderTargetSel = document.getElementById("render-adas-target-select");
    if (renderTargetSel) {
      const prevVal = renderTargetSel.value || "ALL_READY";
      const opts = [
        `<option value="ALL_READY">🎬 Xuất Tất Cả Kịch Bản Chưa Có MP4 & Video Lỗi/Ngắt (${readyUnrendered.length} mã sẵn sàng)</option>`,
        ...doneIdeas.map((it) => {
          const mid = it.ma_id || "IDEA";
          const t = String(it.locked_title || it.draft_title_ja || it.summary_vi || "").slice(0, 42);
          const mp4Tag = isVideoTrulyCompleted(it)
            ? " [Đã có MP4]"
            : (it.status === "ERROR_VIDEO" ? " [⚠️ Lỗi/Ngắt - Chờ Render lại]" : " [Chờ Render]");
          return `<option value="${mid}">#${mid}${mp4Tag} — ${t}...</option>`;
        })
      ];
      renderTargetSel.innerHTML = opts.join("");
      if ([...renderTargetSel.options].some((o) => o.value === prevVal)) {
        renderTargetSel.value = prevVal;
      }
    }

    const btnAll = document.getElementById("btn-adas-filter-all");
    const btnPending = document.getElementById("btn-adas-filter-pending");
    const btnDone = document.getElementById("btn-adas-filter-done");
    const btnUnrendered = document.getElementById("btn-adas-filter-unrendered");
    const btnRendered = document.getElementById("btn-adas-filter-rendered");
    if (btnAll) btnAll.innerText = `Tất cả (${ideas.length})`;
    if (btnPending) btnPending.innerText = `⏳ Chưa xong (${pendingIdeas.length})`;
    if (btnDone) btnDone.innerText = `✅ Đã xong KB (${doneIdeas.length})`;
    if (btnUnrendered) btnUnrendered.innerText = `📦 Chưa Render (${readyUnrendered.length})`;
    if (btnRendered) btnRendered.innerText = `🎬 Đã Render (${renderedIdeas.length})`;

    document.querySelectorAll(".adas-filter-btn").forEach((b) => {
      const f = b.dataset.adasFilter || "all";
      if (f === currentAdasFilter) {
        b.className = "adas-filter-btn px-2 py-0.5 rounded text-[10.5px] font-mono font-bold bg-primary-container text-on-primary-container transition-all";
      } else {
        b.className = "adas-filter-btn px-2 py-0.5 rounded text-[10.5px] font-mono font-semibold text-on-surface-variant hover:bg-surface-container-high transition-all";
      }
      if (!b.dataset.boundClick) {
        b.dataset.boundClick = "1";
        b.addEventListener("click", () => {
          currentAdasFilter = b.dataset.adasFilter || "all";
          adasVisibleLimit = 25;
          renderSavedIdeasList(lastSavedIdeasCache);
        });
      }
    });

    const filteredIdeas = currentAdasFilter === "rendered"
      ? renderedIdeas
      : (currentAdasFilter === "unrendered"
        ? readyUnrendered
        : (currentAdasFilter === "done"
          ? doneIdeas
          : (currentAdasFilter === "pending" ? pendingIdeas : ideas)));

    if (filteredIdeas.length === 0) {
      const emptyMsg = currentAdasFilter === "pending"
        ? "✅ Tuyệt vời! Không còn tiêu đề nào chưa xong kịch bản."
        : (currentAdasFilter === "done"
          ? "⏳ Chưa có tiêu đề nào hoàn thành kịch bản."
          : (currentAdasFilter === "unrendered"
            ? "✅ Tất cả các kịch bản đã viết xong đều đã được Render Video MP4 (hoặc chưa có kịch bản nào hoàn tất)."
            : (currentAdasFilter === "rendered"
              ? "🎬 Chưa có kịch bản nào đã Render xong Video MP4."
              : "Chưa có tiêu đề nào được lưu. Hãy dán Tiêu đề Nhật nháp ở cột bên trái rồi bấm Lưu Kho Dự Án!")));
      listEl.innerHTML = `<div class="p-4 rounded-lg bg-surface-container-lowest/60 border border-dashed border-outline-variant/30 text-center text-xs text-on-surface-variant">${emptyMsg}</div>`;
      return;
    }

    const visibleItems = filteredIdeas.slice(0, adasVisibleLimit);
    const remainingCount = Math.max(0, filteredIdeas.length - visibleItems.length);

    const rowsHtml = visibleItems.map((it) => {
      const maId = it.ma_id || "IDEA";
      const lockedTitle = it.locked_title || "";
      const draftTitle = it.draft_title_ja || it.summary_vi || "(Chưa có tiêu đề Nhật)";
      const fullTitle = lockedTitle || draftTitle;
      const pureCount = it.pure_char_count || 0;
      const doneParts = typeof it.completed_parts_count === "number"
        ? it.completed_parts_count
        : (pureCount >= 35000 ? 3 : pureCount >= 24000 ? 2 : pureCount >= 9500 ? 1 : 0);
      const hasScript = !!it.has_script && pureCount >= 35000 && doneParts >= 3;
      const isPartialScript = !hasScript && (it.status === "PARTIAL_SCRIPT" || (pureCount >= 2500 && pureCount < 35000) || (doneParts > 0 && doneParts < 3));
      const hasMp4 = isVideoTrulyCompleted(it);
      const activeProjectsList = (latestVideoPipelineState && latestVideoPipelineState.current_project)
        ? String(latestVideoPipelineState.current_project).split(",").map((s) => s.trim()).filter(Boolean)
        : [];
      const isVideoRenderingNow =
        latestVideoPipelineState &&
        latestVideoPipelineState.status === "running" &&
        activeProjectsList.includes(maId);
      const isVideoError = it.status === "ERROR_VIDEO" && !hasMp4;
      const isError = (it.status === "ERROR" || it.status === "ERROR_VIDEO") && !hasScript && !isPartialScript;
      const isRunning = (it.status === "RUNNING" || (it.status === "VIDEO_RENDERING" && isVideoRenderingNow) || isVideoRenderingNow) && !hasMp4;
      const hasThumb = !!it.has_thumbnail;
      const hasSeo = !!it.has_seo;

      let statusPill = `<span class="px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant text-[10px] font-mono shrink-0">⏳ Chưa xong</span>`;
      if (hasMp4) {
        statusPill = `<span class="px-1.5 py-0.5 rounded bg-primary-container/20 text-primary-container border border-primary-container/40 text-[10px] font-mono font-bold shrink-0">🎬 Đã có MP4</span>`;
      } else if (isRunning) {
        statusPill = `<span class="px-1.5 py-0.5 rounded bg-secondary-container/20 text-secondary-container border border-secondary-container/40 text-[10px] font-mono font-bold animate-pulse shrink-0">🔄 Đang chạy</span>`;
      } else if (isVideoError && hasScript) {
        const kChars = (pureCount / 1000).toFixed(1) + "k";
        statusPill = `<span class="px-1.5 py-0.5 rounded bg-error/20 text-error border border-error/40 text-[10px] font-mono font-bold shrink-0" title="Video trước đó bị lỗi hoặc ngắt giữa chừng — Đã lọc vào Chưa Render để chạy lại">⚠️ Lỗi Render (${kChars})</span>`;
      } else if (hasScript) {
        const kChars = (pureCount / 1000).toFixed(1) + "k";
        statusPill = `<span class="px-1.5 py-0.5 rounded bg-primary-container/15 text-primary-container border border-primary-container/30 text-[10px] font-mono font-semibold shrink-0">✓ Xong (${kChars})</span>`;
      } else if (isPartialScript) {
        statusPill = `<span class="px-1.5 py-0.5 rounded bg-tertiary/15 text-tertiary border border-tertiary/30 text-[10px] font-mono font-semibold shrink-0">⚠ ${doneParts}/3 Part</span>`;
      } else if (isError) {
        statusPill = `<span class="px-1.5 py-0.5 rounded bg-error/20 text-error border border-error/40 text-[10px] font-mono font-bold shrink-0">❌ Lỗi</span>`;
      }

      const safeTooltip = String(`${maId}: ${fullTitle} (${it.current_step || ""})`).replace(/"/g, "&quot;");

      return `
        <div class="adas-idea-card px-2.5 py-1.5 rounded bg-surface-container-high border border-outline-variant/25 hover:border-secondary-container/40 transition-all flex items-center justify-between gap-2" style="display:flex;" title="${safeTooltip}">
          <div class="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
            <span class="px-1.5 py-0.5 rounded bg-secondary-container/15 text-secondary-container font-mono font-bold text-[10.5px] border border-secondary-container/30 shrink-0">#${maId}</span>
            ${it.use_original_title
              ? `<button type="button" class="btn-idea-toggle-title-mode px-1.5 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/35 text-amber-300 font-mono font-bold text-[9.5px] border border-amber-400/50 shrink-0 cursor-pointer transition-all" data-id="${maId}" data-orig="1" title="Đang dùng Tiêu Đề Gốc (Bỏ Skill 01, tạo thẳng Giàn ý Skill 02) • Bấm để đổi sang Chạy Như Cũ (Skill 01)">📌 Gốc</button>`
              : `<button type="button" class="btn-idea-toggle-title-mode px-1.5 py-0.5 rounded bg-primary-container/10 hover:bg-primary-container/25 text-primary-container/90 font-mono text-[9.5px] border border-primary-container/30 shrink-0 cursor-pointer transition-all" data-id="${maId}" data-orig="0" title="Đang chọn Chạy Như Cũ (Qua Skill 01 viết lại 5 tiêu đề) • Bấm để đổi sang Dùng Tiêu Đề Gốc (Bỏ Skill 01)">🔄 Skill 1</button>`}
            <span class="text-[11.5px] text-on-surface font-medium truncate flex-1">${fullTitle}</span>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            ${statusPill}
            ${!hasScript ? `
              <button type="button" class="btn-idea-script-only px-2 py-0.5 rounded bg-primary-container text-on-primary-fixed hover:brightness-110 text-[10.5px] font-bold flex items-center gap-0.5 transition-all" data-id="${maId}" title="Viết kịch bản cho mã này">
                <span class="material-symbols-outlined text-[12px]">play_arrow</span>${isPartialScript ? "Tiếp" : "Viết"}
              </button>
            ` : `
              <button type="button" class="btn-idea-render-mp4 px-1.5 py-0.5 rounded bg-secondary-container/20 hover:bg-secondary-container/30 text-secondary-container border border-secondary-container/40 text-[10px] font-bold flex items-center gap-0.5 transition-all" data-id="${maId}" title="Dựng Video MP4">
                <span class="material-symbols-outlined text-[12px]">movie</span>Dựng
              </button>
              <button type="button" class="btn-idea-rewrite px-1.5 py-0.5 rounded bg-surface-container hover:bg-surface-bright text-tertiary border border-tertiary/30 text-[10px] font-semibold transition-all" data-id="${maId}" data-has-script="1" title="Viết lại kịch bản">↻</button>
            `}
            ${(hasScript && !hasThumb) ? `
              <button type="button" class="btn-idea-thumb px-1.5 py-0.5 rounded bg-surface-container hover:bg-surface-bright text-secondary border border-outline-variant/30 text-[10px] transition-all" data-id="${maId}" title="Tạo Thumbnail">🖼</button>
            ` : (hasThumb ? `
              <button type="button" class="btn-idea-view-thumbs px-1.5 py-0.5 rounded bg-primary-container/15 hover:bg-primary-container/30 text-primary-container border border-primary-container/40 text-[10px] font-bold transition-all" data-id="${maId}" title="Xem 2 Ảnh Thumbnail & Ảnh Nền Xanh (Có Phóng To)">🖼 Ảnh</button>
            ` : "")}
            <button type="button" class="btn-idea-view p-1 rounded bg-surface-container hover:bg-surface-bright text-on-surface-variant hover:text-on-surface border border-outline-variant/30 transition-all" data-id="${maId}" title="Xem Hồ Sơ Toàn Diện Dự Án Mexico (Kịch Bản, SEO, 2 Ảnh Thumbnail, Giàn Ý, QA)">
              <span class="material-symbols-outlined text-[13px]">visibility</span>
            </button>
            <button type="button" class="btn-idea-folder p-1 rounded bg-surface-container hover:bg-surface-bright text-on-surface-variant hover:text-tertiary border border-outline-variant/30 transition-all" data-id="${maId}" title="Mở Thư Mục Dự Án">
              <span class="material-symbols-outlined text-[13px]">folder</span>
            </button>
            <button type="button" class="btn-idea-del p-1 rounded bg-surface-container hover:bg-error-container/40 text-on-surface-variant hover:text-error border border-outline-variant/30 transition-all" data-id="${maId}" title="Xóa Mã Này">
              <span class="material-symbols-outlined text-[13px]">delete</span>
            </button>
          </div>
        </div>
      `;
    }).join("");

    const moreBtnHtml = remainingCount > 0
      ? `<button type="button" id="btn-adas-load-more" class="w-full py-1.5 mt-1 rounded bg-surface-container hover:bg-surface-container-high text-secondary font-mono text-[11px] font-semibold border border-surface-container-high transition-all">Xem thêm ${remainingCount} tiêu đề nữa...</button>`
      : "";

    listEl.innerHTML = rowsHtml + moreBtnHtml;

    const loadMoreBtn = document.getElementById("btn-adas-load-more");
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener("click", () => {
        adasVisibleLimit += 50;
        renderSavedIdeasList(lastSavedIdeasCache);
      });
    }

    // Gắn sự kiện cho nút chuyển đổi nhanh Chế Độ Tiêu Đề trên từng mã (📌 Gốc <-> 🔄 Skill 1)
    listEl.querySelectorAll(".btn-idea-toggle-title-mode").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const mid = btn.dataset.id;
        if (!mid) return;
        const nextOrig = btn.dataset.orig !== "1";
        try {
          const res = await fetch("/api/adas/ideas/set-title-mode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ use_original_title: nextOrig, ma_ids: [mid] })
          });
          if (res.ok) {
            const data = await res.json();
            renderSavedIdeasList(data.ideas || []);
            appendInstantLogToUI(
              nextOrig
                ? `📌 [#${mid}] Đã chuyển sang chế độ: DÙNG TIÊU ĐỀ GỐC (Bỏ qua Skill 01, tạo thẳng Giàn ý Skill 02).`
                : `🔄 [#${mid}] Đã chuyển sang chế độ: CHẠY NHƯ CŨ (Qua Skill 01 viết lại tiêu đề).`,
              "SCRIPT",
              "INFO",
              mid
            );
          }
        } catch (e) {}
      });
    });

    // Gắn sự kiện cho nút Render MP4 trực tiếp (dành cho các mã đã viết xong kịch bản)
    listEl.querySelectorAll(".btn-idea-render-mp4").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const mid = btn.dataset.id;
        await triggerRenderOnly([mid], false);
      });
    });

    // Gắn sự kiện cho nút Chỉ Viết KB + SEO + Thumbnail (Không Render Video)
    listEl.querySelectorAll(".btn-idea-script-only").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const mid = btn.dataset.id;
        await triggerRunADAS([mid], false, false);
      });
    });

    // Gắn sự kiện cho các nút trên từng thẻ ý tưởng
    listEl.querySelectorAll(".btn-idea-run").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const mid = btn.dataset.id;
        await triggerRunADAS([mid], null, false);
      });
    });

    // Gắn sự kiện cho nút Viết Lại Thủ Công (🔁 Viết Lại)
    listEl.querySelectorAll(".btn-idea-rewrite").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const mid = btn.dataset.id;
        if (!mid) return;
        const alreadyHasScript = btn.dataset.hasScript === "1";
        if (alreadyHasScript) {
          const ok = confirm(
            `🔁 Bạn có muốn VIẾT LẠI THỦ CÔNG kịch bản cho mã [${mid}] từ đầu không?\n\n` +
            `• Chọn OK: Xóa kịch bản cũ của ${mid} và mở AI viết lại mới hoàn toàn từ Step 2 (kèm tự động Retry tối đa 3 lần nếu lỗi).`
          );
          if (!ok) return;
        }
        appendInstantLogToUI(`🔁 Kích hoạt VIẾT LẠI THỦ CÔNG cho mã [${mid}] (Tự động Retry tối đa 3 lần nếu lỗi)...`, "SCRIPT", "INFO", mid);
        await triggerRunADAS([mid], null, true);
      });
    });

    listEl.querySelectorAll(".btn-idea-thumb").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const mid = btn.dataset.id;
        const origText = btn.innerText;
        btn.disabled = true;
        btn.innerText = "⏳ Đang vẽ...";
        try {
          const res = await fetch(`/api/adas/project/${encodeURIComponent(mid)}/generate-thumbnails?force=true`, {
            method: "POST"
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            alert(data.detail || "Không thể khởi chạy tạo Thumbnail!");
          } else {
            await loadSavedIdeas();
          }
        } catch (e) {
          alert("Lỗi khởi chạy tạo Thumbnail: " + e.message);
        } finally {
          setTimeout(() => {
            btn.disabled = false;
            btn.innerText = origText;
          }, 1500);
        }
      });
    });

    listEl.querySelectorAll(".btn-idea-sync").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const mid = btn.dataset.id;
        const origText = btn.innerText;
        btn.disabled = true;
        btn.innerText = "⏳ Đang check...";
        try {
          const res = await fetch(`/api/adas/project/${encodeURIComponent(mid)}/check-sync`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ auto_redo: false })
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(`❌ Không thể kiểm định ${mid}: ${err.detail || "Chưa có dữ liệu kịch bản/video"}`);
            return;
          }
          const data = await res.json();
          const rep = data.report || {};
          const sa = rep.sentence_audit || {};
          if (rep.passed) {
            alert(
              `✅ [${mid}] KIỂM ĐỊNH ĐẠT 100%!\n\n` +
              `• Trạng thái: ${rep.status_label}\n` +
              `• Số câu thoại khớp chuẩn: ${sa.passed_sentences}/${sa.total_sentences} câu\n` +
              `• Thời lượng Video MP4: ${rep.video_duration}s\n` +
              `• Thời lượng Voice WAV: ${rep.voice_duration}s\n` +
              `• Độ lệch MP4 vs Voice: ${rep.drift_video_vs_voice_sec}s`
            );
          } else {
            const issuesText = (rep.issues || []).map((x) => "  - " + x).join("\n");
            const confirmRedo = confirm(
              `⚠️ [${mid}] KIỂM ĐỊNH PHÁT HIỆN CHƯA KHỚP:\n\n` +
              `${issuesText}\n` +
              `• Câu đạt chuẩn: ${sa.passed_sentences || 0}/${sa.total_sentences || 0} (Cần làm lại: ${sa.failed_count || 0} câu)\n\n` +
              `👉 Bạn có muốn hệ thống TỰ ĐỘNG LÀM LẠI các câu bị lệch (chế độ 1 Câu = 1 File Voice độc lập) và Render lại Video MP4 ngay bây giờ không?`
            );
            if (confirmRedo) {
              const redoRes = await fetch(`/api/adas/project/${encodeURIComponent(mid)}/check-sync`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  auto_redo: true,
                  video_settings: getCurrentVideoSettings()
                })
              });
              if (redoRes.ok) {
                progressSection.style.display = "block";
                progressMsg.innerText = `[${mid}] 🔄 Đang tự động làm lại các câu lệch Sub-Voice và Render lại Video...`;
              }
            }
          }
        } catch (e) {
          alert("Lỗi kiểm định Sub-Voice: " + e.message);
        } finally {
          btn.disabled = false;
          btn.innerText = origText;
        }
      });
    });

    listEl.querySelectorAll(".btn-idea-view").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const mid = btn.dataset.id;
        await openProjectDetailModal(mid, "full_script");
      });
    });

    listEl.querySelectorAll(".btn-idea-view-thumbs").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const mid = btn.dataset.id;
        await openProjectDetailModal(mid, "thumbnails");
      });
    });

    listEl.querySelectorAll(".btn-idea-folder").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const mid = btn.dataset.id;
        if (!mid) return;
        try {
          const outRes = await fetch(`/api/adas/project/${encodeURIComponent(mid)}/outputs`);
          if (outRes.ok) {
            const outData = await outRes.json();
            if (outData && outData.project_dir) {
              await openSystemFolder(outData.project_dir);
              return;
            }
          }
        } catch (_) {}
        const adasProjInput = document.getElementById("adas-projects-dir-input");
        const baseProj = (adasProjInput && adasProjInput.value.trim())
          ? adasProjInput.value.trim().replace(/[\\/]+$/, "")
          : ((outputDirInput && outputDirInput.value.trim()) ? outputDirInput.value.trim().replace(/[\\/]+$/, "") : "projects");
        const directProjPath = `${baseProj}\\${mid}`;
        await openSystemFolder(directProjPath);
      });
    });

    listEl.querySelectorAll(".btn-idea-del").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const mid = btn.dataset.id;
        if (!mid) return;
        btn.disabled = true;
        btn.innerText = "⏳";
        appendInstantLogToUI(`🗑️ Đang xóa mã dự án [${mid}] khỏi Kho Dự Án...`, "SCRIPT", "INFO", mid);
        try {
          const res = await fetch("/api/adas/ideas/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ma_id: mid })
          });
          if (res.ok) {
            const data = await res.json();
            renderSavedIdeasList(data.ideas || []);
          } else {
            await loadSavedIdeas();
          }
        } catch (e) {
          console.error("Lỗi xóa mã:", e);
          await loadSavedIdeas();
        }
      });
    });
  }
  window.__renderSavedIdeasGlobal = renderSavedIdeasList;

  async function triggerRenderOnly(maIds = null, onlyUnrendered = false) {
    try {
      const res = await fetch("/api/adas/render-only", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ma_ids: maIds,
          only_unrendered: onlyUnrendered,
          video_settings: getCurrentVideoSettings()
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        alert(data.detail || "Không có kịch bản nào sẵn sàng Render MP4!");
        return;
      }
      switchStudioTab("tab-render");
      if (progressSection) {
        progressSection.style.display = "block";
        progressMsg.innerText = data.message || "🎬 Đang khởi tạo hàng đợi tạo Voice & Render MP4...";
      }
      await loadSavedIdeas();
      await fetchSystemLogs();
    } catch (e) {
      alert("Lỗi khởi chạy Render MP4: " + e.message);
    }
  }

  async function triggerRunADAS(maIds, forceAutoVideo = null, forceRewriteScript = false) {
    if (!maIds || maIds.length === 0) return;
    const accSel = document.getElementById("adas-acc-select");
    const autoVid = document.getElementById("adas-auto-video");
    const outputModeSel = document.getElementById("adas-output-mode-select");
    const lenMode = document.getElementById("adas-length-mode");
    const aiProvSel = document.getElementById("adas-ai-provider-select");
    const chosenProvider = (aiProvSel && aiProvSel.value) ? aiProvSel.value : "chatgpt_web";

    // Nếu người dùng đang chọn chế độ 3 ("render_ready_only" — Chỉ Render các kịch bản đã xong) và không ép chế độ khác
    if (forceAutoVideo === null && !forceRewriteScript && outputModeSel && outputModeSel.value === "render_ready_only") {
      await triggerRenderOnly(maIds, true);
      return;
    }

    let shouldProduceVideo = true;
    if (typeof forceAutoVideo === "boolean") {
      shouldProduceVideo = forceAutoVideo;
    } else if (outputModeSel && outputModeSel.value === "script_seo_thumb_only") {
      shouldProduceVideo = false;
    } else if (autoVid) {
      shouldProduceVideo = autoVid.checked;
    }

    if (!shouldProduceVideo) {
      appendInstantLogToUI(
        `📝 Khởi chạy chế độ CHỈ VIẾT KỊCH BẢN + SEO + THUMBNAIL (Không Render Video) cho ${maIds.length} mã: ${maIds.join(", ")} (Tự động Retry 3 lần nếu lỗi)`,
        "SCRIPT",
        "INFO"
      );
    }

    try {
      const res = await fetch("/api/adas/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ma_ids: maIds,
          preferred_acc_id: accSel && accSel.value ? accSel.value : null,
          auto_produce_video: shouldProduceVideo,
          target_part_min: lenMode ? parseInt(lenMode.value, 10) || 13334 : 13334,
          video_settings: getCurrentVideoSettings(),
          ai_provider: chosenProvider,
          force_rewrite_script: !!forceRewriteScript,
          max_retries: 3,
          use_original_title: (window.currentAdasTitleMode || currentAdasTitleMode) === "original"
        })
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Không thể khởi chạy Agent!");
        return;
      }
      await loadSavedIdeas();
      await fetchSystemLogs();
    } catch (e) {
      alert("Lỗi khởi chạy dây chuyền Agent: " + e.message);
    }
  }

  let currentZoomScale = 1.0;
  let currentZoomKind = "main";

  function openMexicoImageZoomLightbox(kind = "main") {
    if (!currentProjectDetailData) return;
    const cards = Array.isArray(currentProjectDetailData.thumbnail_cards)
      ? currentProjectDetailData.thumbnail_cards
      : [];
    const targetCard = cards.find((c) => c.kind === kind && c.exists && c.data_url)
      || cards.find((c) => c.exists && c.data_url);
    if (!targetCard || !targetCard.data_url) {
      alert("Chưa có file ảnh để phóng to!");
      return;
    }
    currentZoomKind = targetCard.kind || kind;
    currentZoomScale = 1.0;

    const zoomModal = document.getElementById("mexico-image-zoom-modal");
    const zoomImg = document.getElementById("mexico-zoom-img");
    const zoomTitle = document.getElementById("mexico-zoom-title");
    const zoomMeta = document.getElementById("mexico-zoom-meta");
    if (!zoomModal || !zoomImg) return;

    zoomImg.src = targetCard.data_url;
    zoomImg.style.transform = `scale(${currentZoomScale})`;
    if (zoomTitle) {
      zoomTitle.innerText = `🇲🇽 Dự Án Mexico #${currentProjectDetailData.ma_id || ""} — ${targetCard.title || targetCard.filename}`;
    }
    if (zoomMeta) {
      zoomMeta.innerText = `${Math.round(currentZoomScale * 100)}% • ${targetCard.meta || "1920×1080"}`;
    }
    zoomModal.classList.remove("hidden");
    zoomModal.style.display = "flex";
  }

  function updateMexicoZoomScale(newScale) {
    currentZoomScale = Math.max(0.5, Math.min(3.5, Number(newScale.toFixed(2))));
    const zoomImg = document.getElementById("mexico-zoom-img");
    const zoomMeta = document.getElementById("mexico-zoom-meta");
    if (zoomImg) {
      zoomImg.style.transform = `scale(${currentZoomScale})`;
    }
    if (zoomMeta && currentProjectDetailData) {
      const cards = Array.isArray(currentProjectDetailData.thumbnail_cards) ? currentProjectDetailData.thumbnail_cards : [];
      const card = cards.find((c) => c.kind === currentZoomKind) || {};
      zoomMeta.innerText = `${Math.round(currentZoomScale * 100)}% • ${card.meta || "1920×1080"}`;
    }
  }

  function renderModalThumbnailsGrid(data) {
    const gridEl = document.getElementById("adas-thumbnails-grid");
    if (!gridEl) return;
    const cards = Array.isArray(data && data.thumbnail_cards) ? data.thumbnail_cards : [];
    if (cards.length === 0) {
      gridEl.innerHTML = `<div class="col-span-2 p-6 text-center text-on-surface-variant font-mono text-xs">Chưa có ảnh Thumbnail cho dự án này. Hãy bấm "🔄 Vẽ / Tách Lại Cặp Thumbnail".</div>`;
      return;
    }

    gridEl.innerHTML = cards.map((card) => {
      const borderCls = card.kind === "green"
        ? "border-[#00ff87]/50 bg-[#001a0d]/40"
        : "border-primary-container/40 bg-surface-container";
      const badgeCls = card.kind === "green"
        ? "bg-[#00ff87]/20 text-[#00ff87] border-[#00ff87]/40"
        : "bg-secondary-container/20 text-secondary-container border-secondary-container/40";
      if (!card.exists || !card.data_url) {
        return `
          <div class="rounded-lg p-3 border ${borderCls} flex flex-col justify-between gap-2">
            <div class="flex items-center justify-between gap-2">
              <span class="font-bold text-xs text-primary">${card.title}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono border ${badgeCls}">${card.meta || "Chưa có"}</span>
            </div>
            <div class="aspect-video w-full rounded bg-surface-container-lowest border border-surface-container-high flex items-center justify-center text-xs text-outline font-mono">
              Chưa tạo file ${card.filename}
            </div>
          </div>
        `;
      }
      return `
        <div class="rounded-lg p-2.5 border ${borderCls} flex flex-col gap-2 shadow-lg">
          <div class="flex items-center justify-between gap-2">
            <span class="font-bold text-xs text-primary truncate">${card.title}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono border shrink-0 ${badgeCls}">${card.meta || "1920×1080"}</span>
          </div>
          <div class="relative group aspect-video w-full rounded overflow-hidden bg-black border border-surface-container-highest cursor-zoom-in" data-zoom-kind="${card.kind}">
            <img src="${card.data_url}" alt="${card.filename}" class="w-full h-full object-contain transition-transform duration-200 group-hover:scale-[1.02]" />
            <div class="absolute inset-0 bg-black/0 group-hover:bg-black/35 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
              <span class="px-3 py-1.5 rounded-full bg-black/85 text-white font-bold text-xs flex items-center gap-1 border border-white/30 shadow-xl">
                <span class="material-symbols-outlined text-[16px]">zoom_in</span> Bấm để Phóng To Xem Rõ
              </span>
            </div>
          </div>
          <div class="flex items-center justify-between gap-2 pt-0.5">
            <span class="font-mono text-[10.5px] text-on-surface-variant truncate" title="${card.path}">${card.filename}</span>
            <div class="flex items-center gap-1.5 shrink-0">
              <button type="button" class="btn-thumb-card-zoom px-2.5 py-1 rounded bg-primary-container text-on-primary-container font-bold text-[11px] flex items-center gap-1 hover:brightness-110 transition-all" data-zoom-kind="${card.kind}">
                <span class="material-symbols-outlined text-[14px]">zoom_in</span> Phóng To
              </button>
              <button type="button" class="btn-thumb-card-folder px-2 py-1 rounded bg-surface-container-high hover:bg-surface-bright text-on-surface font-mono text-[11px] border border-outline-variant/40" data-folder-path="${card.path}">
                📂 Mở File
              </button>
            </div>
          </div>
        </div>
      `;
    }).join("");

    gridEl.querySelectorAll("[data-zoom-kind]").forEach((el) => {
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const k = el.getAttribute("data-zoom-kind") || "main";
        openMexicoImageZoomLightbox(k);
      });
    });

    gridEl.querySelectorAll(".btn-thumb-card-folder").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const p = btn.getAttribute("data-folder-path") || "";
        const dir = p ? p.replace(/[\\/][^\\/]+$/, "") : (currentProjectDetailData.raw_project_dir || currentProjectDetailData.project_dir);
        if (dir) await openSystemFolder(dir);
      });
    });
  }

  async function openProjectDetailModal(maId, initialTab = "full_script") {
    try {
      const res = await fetch(`/api/adas/project/${encodeURIComponent(maId)}`);
      if (!res.ok) return;
      currentProjectDetailData = await res.json();

      const modal = document.getElementById("adas-detail-modal");
      const titleEl = document.getElementById("adas-detail-title") || document.getElementById("adas-detail-modal-title");
      if (titleEl) {
        titleEl.innerText = `🇲🇽 Hồ Sơ Toàn Diện Dự Án Mexico — Mã #${maId}`;
      }

      const badgeId = document.getElementById("adas-detail-badge-id");
      const badgeTitle = document.getElementById("adas-detail-badge-title");
      const badgeChars = document.getElementById("adas-detail-badge-chars");
      const badgeThumbs = document.getElementById("adas-detail-badge-thumbs");
      const footerPath = document.getElementById("adas-detail-footer-path");

      if (badgeId) badgeId.innerText = `#${maId}`;
      if (badgeTitle) {
        const lockedT = currentProjectDetailData.locked_title
          || (currentProjectDetailData.idea && (currentProjectDetailData.idea.locked_title || currentProjectDetailData.idea.draft_title_ja))
          || `Dự Án Mexico #${maId}`;
        badgeTitle.innerText = lockedT;
        badgeTitle.title = lockedT;
      }
      if (badgeChars) {
        const cCount = Number(currentProjectDetailData.pure_char_count || 0);
        const wCount = Number(currentProjectDetailData.word_count || 0);
        badgeChars.innerText = `📝 ${cCount.toLocaleString()} chữ (${wCount.toLocaleString()} từ)`;
      }
      if (badgeThumbs) {
        const cards = Array.isArray(currentProjectDetailData.thumbnail_cards) ? currentProjectDetailData.thumbnail_cards : [];
        const readyCnt = cards.filter((c) => c.exists).length;
        badgeThumbs.innerText = `🖼️ ${readyCnt}/2 Ảnh Thumbnail & Nền Xanh`;
      }
      if (footerPath) {
        footerPath.innerText = `📁 Thư mục dự án: ${currentProjectDetailData.raw_project_dir || currentProjectDetailData.project_dir || ""}`;
      }

      renderModalThumbnailsGrid(currentProjectDetailData);
      switchDetailModalTab(initialTab);
      if (modal) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
      }
    } catch (e) {
      alert("Không thể đọc chi tiết dự án Mexico: " + e.message);
    }
  }

  function switchDetailModalTab(tabKey) {
    if (!currentProjectDetailData) return;
    const txtArea = document.getElementById("adas-detail-textarea");
    const thumbsView = document.getElementById("adas-detail-thumbnails-view");
    const stageBar = document.getElementById("adas-script-subfilter-bar");

    document.querySelectorAll(".adas-view-tab").forEach((b) => {
      if (b.dataset.tab === tabKey) {
        b.classList.add("active");
        b.style.borderColor = "#00ff87";
        b.style.color = "#00ff87";
        b.style.background = "rgba(0, 255, 135, 0.12)";
      } else {
        b.classList.remove("active");
        b.style.borderColor = "rgba(255,255,255,0.15)";
        b.style.color = "#e2e8f0";
        b.style.background = "transparent";
      }
    });

    if (thumbsView) {
      if (tabKey === "thumbnails") {
        thumbsView.classList.remove("hidden");
        thumbsView.style.display = "flex";
      } else {
        thumbsView.classList.add("hidden");
        thumbsView.style.display = "none";
      }
    }

    if (stageBar) {
      stageBar.style.display = (tabKey === "full_script") ? "flex" : "none";
    }

    let content = "";
    if (tabKey === "full_script") {
      content = currentProjectDetailData.full_script
        || currentProjectDetailData.script_clean
        || [currentProjectDetailData.part_a, currentProjectDetailData.part_b, currentProjectDetailData.part_c].filter(Boolean).join("\n\n")
        || "(Chưa có kịch bản hoàn chỉnh cho dự án Mexico này)";
      const stageInfoEl = document.getElementById("adas-script-stage-char-info");
      if (stageInfoEl) {
        const lenA = (currentProjectDetailData.part_a || "").replace(/\s+/g, "").length;
        const lenB = (currentProjectDetailData.part_b || "").replace(/\s+/g, "").length;
        const lenC = (currentProjectDetailData.part_c || "").replace(/\s+/g, "").length;
        stageInfoEl.innerText = `A: ${lenA.toLocaleString()} | B: ${lenB.toLocaleString()} | C: ${lenC.toLocaleString()} chữ`;
      }
      if (txtArea) txtArea.rows = 15;
    } else if (tabKey === "seo_pack") {
      content = currentProjectDetailData.seo_pack
        || currentProjectDetailData.step2_output
        || "(Chưa có gói SEO YouTube es-MX cho dự án này)";
      if (txtArea) txtArea.rows = 15;
    } else if (tabKey === "thumbnails") {
      const cards = Array.isArray(currentProjectDetailData.thumbnail_cards) ? currentProjectDetailData.thumbnail_cards : [];
      const lines = cards.map((c, idx) => `${idx + 1}. ${c.title}: ${c.path || "(Chưa tạo)"} (${c.meta || ""})`);
      content = "📌 ĐƯỜNG DẪN 2 FILE ẢNH THUMBNAIL & NHÂN VẬT NỀN XANH (#00FF00):\n" + lines.join("\n");
      if (txtArea) txtArea.rows = 3;
    } else if (tabKey === "outline") {
      content = currentProjectDetailData.outline
        || [currentProjectDetailData.step2_output, currentProjectDetailData.step3_output].filter(Boolean).join("\n\n")
        || "(Chưa có Giàn ý 7 Phần & Tiêu đề cho dự án này)";
      if (txtArea) txtArea.rows = 15;
    } else if (tabKey === "audit_report") {
      content = currentProjectDetailData.audit_report
        || currentProjectDetailData.step5_output
        || "(Chưa có Báo cáo kiểm định QA cho dự án này)";
      if (txtArea) txtArea.rows = 15;
    } else if (tabKey === "step2_prompt") {
      content = currentProjectDetailData.step2_prompt
        || "(Chưa có Lệnh khởi tạo cho dự án này)";
      if (txtArea) txtArea.rows = 15;
    } else {
      content = currentProjectDetailData[tabKey] || "";
    }

    if (txtArea) txtArea.value = content;
  }

  function setupChatGPTAndADASSystem() {
    // 0. Lưu & khôi phục lựa chọn Bộ Máy AI (ChatGPT Web / Gemini 4 Pro / Kết Hợp)
    const aiProvSel = document.getElementById("adas-ai-provider-select");
    if (aiProvSel) {
      const savedProv = localStorage.getItem("adas_ai_provider");
      if (savedProv && ["chatgpt_web", "gemini_4_pro", "hybrid_gemini_chatgpt"].includes(savedProv)) {
        aiProvSel.value = savedProv;
      }
      aiProvSel.addEventListener("change", () => {
        localStorage.setItem("adas_ai_provider", aiProvSel.value);
        appendInstantLogToUI(
          `🧠 Đã chọn cách viết kịch bản: ${aiProvSel.options[aiProvSel.selectedIndex].text}`,
          "SCRIPT",
          "INFO"
        );
      });
    }

    // 0b. Lưu & đồng bộ Chế Độ Chạy (3 Chế Độ: Chỉ Viết KB+Thumb+SEO / Viết + Render Song Song / Chỉ Render Kịch Bản Đã Xong)
    const outputModeSel = document.getElementById("adas-output-mode-select");
    const autoVidChk = document.getElementById("adas-auto-video");
    if (outputModeSel) {
      const savedOutMode = localStorage.getItem("adas_output_mode");
      if (savedOutMode && ["full_video", "script_seo_thumb_only", "render_ready_only"].includes(savedOutMode)) {
        outputModeSel.value = savedOutMode;
        if (autoVidChk) {
          autoVidChk.checked = (savedOutMode !== "script_seo_thumb_only");
        }
      }
      outputModeSel.addEventListener("change", () => {
        const modeVal = outputModeSel.value;
        localStorage.setItem("adas_output_mode", modeVal);
        if (autoVidChk) {
          autoVidChk.checked = (modeVal !== "script_seo_thumb_only");
        }
        const logMsg = modeVal === "script_seo_thumb_only"
          ? "📝 Đã chọn Chế độ 1: CHỈ VIẾT KỊCH BẢN + THUMBNAIL + SEO (Không Render Video)"
          : (modeVal === "render_ready_only"
            ? "🎬 Đã chọn Chế độ 3: CHỈ RENDER CÁC KỊCH BẢN ĐÃ XONG (Không mở AI viết lại)"
            : "🚀 Đã chọn Chế độ 2: VIẾT KỊCH BẢN + THUMBNAIL + SEO & RENDER VIDEO LUÔN (Cứ xong kịch bản nào Render ngay kịch bản đó)");
        appendInstantLogToUI(logMsg, "SCRIPT", "INFO");
      });
    }
    if (autoVidChk && outputModeSel) {
      autoVidChk.addEventListener("change", () => {
        outputModeSel.value = autoVidChk.checked ? "full_video" : "script_seo_thumb_only";
        localStorage.setItem("adas_output_mode", outputModeSel.value);
      });
    }

    // 1. Nút mở từng tài khoản Chrome ChatGPT (Acc #1 .. Acc #5)
    document.querySelectorAll(".chatgpt-acc-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const accId = btn.dataset.acc || "acc_1";
        const origHtml = btn.innerHTML;
        btn.innerText = `⏳ Đang mở ${accId.toUpperCase()}...`;
        try {
          await fetch("/api/chatgpt/open_browser", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ acc_id: accId })
          });
          setTimeout(() => refreshChatGPTAccountsBar(true), 1200);
        } catch (e) {
          btn.innerHTML = origHtml;
        }
      });
    });

    // 1a. Nút Thêm Acc (tự động mở slot tiếp theo chưa đăng nhập trong tối đa 5 Acc để user đăng nhập)
    const addAccBtn = document.getElementById("btn-chatgpt-add-acc");
    if (addAccBtn) {
      addAccBtn.addEventListener("click", async () => {
        const origHtml = addAccBtn.innerHTML;
        addAccBtn.innerText = "⏳ Đang kiểm tra...";
        try {
          const stRes = await fetch("/api/chatgpt/status?force=true");
          const stData = await stRes.json();
          const accs = (stData && stData.accounts) || {};
          const nextAcc = ["acc_1", "acc_2", "acc_3", "acc_4", "acc_5"].find(
            (aid) => !(accs[aid] && (accs[aid].saved_logged_in || accs[aid].logged_in))
          );
          if (!nextAcc) {
            alert("✅ Bạn đã đăng nhập và lưu đủ tối đa 5/5 tài khoản ChatGPT (Acc #1 -> Acc #5)!");
            await refreshChatGPTAccountsBar(true);
            return;
          }
          const idxNum = nextAcc.replace("acc_", "");
          addAccBtn.innerText = `⏳ Mở Acc #${idxNum}...`;
          appendInstantLogToUI(
            `➕ Đang mở trình duyệt Chrome cho Acc #${idxNum} (Cổng ${9231 + parseInt(idxNum, 10)}) để bạn đăng nhập ChatGPT — Đăng nhập xong hệ thống sẽ tự động lưu lại!`,
            "CHROME",
            "INFO"
          );
          await fetch("/api/chatgpt/open_browser", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ acc_id: nextAcc })
          });
          setTimeout(() => refreshChatGPTAccountsBar(true), 1200);
        } catch (e) {
          addAccBtn.innerHTML = origHtml;
        }
      });
    }

    // 1a-2. Nút Tắt Chrome (Đóng toàn bộ cửa sổ Chrome ChatGPT khi không dùng, giữ nguyên trạng thái đã lưu)
    const closeAllChromeBtn = document.getElementById("btn-chatgpt-close-all");
    if (closeAllChromeBtn) {
      closeAllChromeBtn.addEventListener("click", async () => {
        const origHtml = closeAllChromeBtn.innerHTML;
        closeAllChromeBtn.innerText = "🛑 Đang tắt Chrome...";
        try {
          const res = await fetch("/api/chatgpt/close_browsers", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ only_if_idle: false })
          });
          const data = await res.json().catch(() => ({}));
          appendInstantLogToUI(
            `🛑 Đã tắt ${data.closed_count || 0} cửa sổ trình duyệt Chrome ChatGPT (Các tài khoản đã đăng nhập vẫn được lưu giữ 100%)!`,
            "CHROME",
            "INFO"
          );
          await refreshChatGPTAccountsBar(true);
        } catch (e) {
          closeAllChromeBtn.innerHTML = origHtml;
        }
      });
    }

    // 1b. Nút mở Google Gemini 3.8 High trên cổng Chrome riêng (Gemini #1: 9225, #2: 9226, #3: 9227)
    document.querySelectorAll(".gemini-acc-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const accId = btn.dataset.acc || "acc_1";
        const idx = parseInt(accId.replace("acc_", ""), 10) || 1;
        const port = 9224 + idx;
        btn.innerText = `⏳ Mở Gemini #${idx} (${port})...`;
        try {
          const res = await fetch("/api/gemini/open_browser", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ acc_id: accId })
          });
          const data = await res.json().catch(() => ({}));
          if (res.ok && data.ok) {
            btn.innerText = `✨ Gemini #${idx} (${port}): Đã mở`;
            btn.style.borderColor = "rgba(0, 230, 118, 0.65)";
            btn.style.background = "rgba(0, 230, 118, 0.14)";
            appendInstantLogToUI(
              `✨ Đã mở Google Gemini 3.8 High (https://gemini.google.com/app) trên Cổng riêng ${port} (GEMINI_PROFILE_${idx})!`,
              "CHROME",
              "INFO"
            );
          } else {
            btn.innerText = `✨ GEM ${idx} (${port})`;
          }
          setTimeout(() => refreshChatGPTAccountsBar(true), 1200);
        } catch (e) {
          btn.innerText = `✨ GEM ${idx} (${port})`;
        }
      });
    });

    // 2. Nút Ẩn/Hiện cửa sổ Chrome (-3200, -3200)
    const visBtn = document.getElementById("btn-chatgpt-toggle-vis");
    if (visBtn) {
      visBtn.addEventListener("click", async () => {
        const currentlyVisible = visBtn.dataset.visible === "true";
        const targetVisible = !currentlyVisible;
        await fetch("/api/chatgpt/visibility", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ visible: targetVisible, acc_id: null })
        });
        await refreshChatGPTAccountsBar(true);
      });
    }

    // 3. Nút Dọn Tab Đã Xong
    const sweepBtn = document.getElementById("btn-chatgpt-sweep-tabs");
    if (sweepBtn) {
      sweepBtn.addEventListener("click", async () => {
        const orig = sweepBtn.innerText;
        sweepBtn.innerText = "🧹 Đang dọn...";
        try {
          const res = await fetch("/api/chatgpt/sweep_tabs", { method: "POST" });
          const data = await res.json();
          sweepBtn.innerText = `✅ Đã dọn ${data.closed_tabs || 0} tab`;
          setTimeout(() => { sweepBtn.innerText = orig; }, 2200);
          await refreshChatGPTAccountsBar(true);
        } catch (e) {
          sweepBtn.innerText = orig;
        }
      });
    }

    // 4. Nút Điền Mẫu Tiêu Đề (Mỗi tiêu đề 1 dòng — Tự động bỏ qua Mã và đánh STT 1, 2, 3...)
    const sampleText = [
      "Mi yerno me pidió ciento veinte mil euros sin saber que yo ya lo había visto todo",
      "Mi hijo y mi nuera me echaron de la casa que construí ladrillo por ladrillo; al día siguiente el notario leyó la cláusula de donación revocable",
      "Mis tres hijos cambiaron las cerraduras de mi rancho pensando que ya no valía nada, pero el juez abrió el fideicomiso"
    ].join("\n");

    const rawInputEl = document.getElementById("adas-raw-input");
    const detectedBadgeEl = document.getElementById("adas-detected-count-badge");

    const fieldLinePrefixRe = /^(?:(?:\d{1,2}[\.\)\-:]|\-|•|\*)\s*)?(?:vi|vn|dịch\s*ý|tóm\s*tắt|premise|nội\s*dung|keyword|keywords|từ\s*khóa|evidence|proof|vật\s*chứng|bằng\s*chứng|reveal|reveals|ba\s*lớp\s*tiết\s*lộ|3\s*lớp\s*tiết\s*lộ|lớp\s*tiết\s*lộ|tiết\s*lộ|capacity|longform|đánh\s*giá|quan\s*hệ|nhân\s*vật|relation|relationship|trụ\s*cột|nhóm\s*chủ\s*đề|chủ\s*đề|không\s*gian|bối\s*cảnh|setting|xung\s*đột|conflict|câu\s*hỏi|payoff|hệ\s*quả|mức\s*ưu\s*tiên|ưu\s*tiên|priority|trạng\s*thái|status|mã\s*cơ\s*chế|cơ\s*chế|căn\s*cứ|lưu\s*ý|quy\s*tắc|góc\s*thumbnail|nguồn\s*gốc|research_source)\s*[:：]/i;
    const titleLabelStartRe = /^(?:(?:\d+[\.\)\-:]|\-|•|\*|#+\s*)\s*)?(?:tiêu\s*đề\s*nhật\s*nháp|tiêu\s*đề\s*nháp|tiêu\s*đề|04\.\s*tiêu\s*đề|title|current_final_title|locked_title)\s*[:：]/i;

    function cleanSingleTitleLine(rawLine) {
      let ln = (rawLine || "").trim();
      if (!ln || /^[-=*#]{3,}$/.test(ln)) return "";
      if (fieldLinePrefixRe.test(ln)) return "";
      if (titleLabelStartRe.test(ln)) {
        ln = ln.replace(titleLabelStartRe, "").trim();
      }
      if (ln.includes("\t")) {
        const parts = ln.split("\t").map(p => p.trim()).filter(Boolean);
        ln = parts.length >= 2 ? parts.slice(1).join(" ").trim() : (parts[0] || "");
      }
      ln = ln.replace(/^(?:(?:#|\*|\-|\•)\s*)?(?:[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+|(?:P|ID|IDEA_?|PMX_?|M|T|STT)\s*\d{1,5}|\d{1,5})\s*(?:[\.\)\-—–:：\|]+|\s{2,})\s*/i, "").trim();
      ln = ln.replace(/^["'“”‘’«»]+|["'“”‘’«»]+$/g, "").trim();
      return ln;
    }

    function sanitizePastedTitlesText(text) {
      const lines = (text || "").split(/\r?\n/);
      const cleanedLines = [];
      for (const line of lines) {
        const cleaned = cleanSingleTitleLine(line);
        if (cleaned) {
          cleanedLines.push(cleaned);
        }
      }
      return cleanedLines.join("\n");
    }

    function handleTitlePasteClean(e) {
      const clip = (e.clipboardData || window.clipboardData)?.getData("text") || "";
      if (!clip) return;
      e.preventDefault();
      const cleanedText = sanitizePastedTitlesText(clip);
      if (!rawInputEl) return;
      const start = rawInputEl.selectionStart || 0;
      const end = rawInputEl.selectionEnd || 0;
      const before = rawInputEl.value.slice(0, start);
      const after = rawInputEl.value.slice(end);
      const prefixNewline = (before && !before.endsWith("\n")) ? "\n" : "";
      const suffixNewline = (after && !after.startsWith("\n")) ? "\n" : "";
      rawInputEl.value = `${before}${prefixNewline}${cleanedText}${suffixNewline}${after}`.replace(/^\n+/, "");
      refreshDetectedCountBadge();
    }

    function countDetectedIdeasInText(text) {
      const t = (text || "").trim();
      if (!t) return 0;
      const lines = t.split(/\r?\n/).map(l => cleanSingleTitleLine(l)).filter(Boolean);
      return lines.length;
    }

    function refreshDetectedCountBadge() {
      if (!rawInputEl || !detectedBadgeEl) return;
      const c = countDetectedIdeasInText(rawInputEl.value);
      detectedBadgeEl.innerText = c > 0
        ? `🔥 Đã nhận diện: ${c} tiêu đề (Mã STT #1 ➔ #${c})`
        : `Đã nhận diện: 0 tiêu đề`;
    }

    if (rawInputEl) {
      rawInputEl.addEventListener("input", () => {
        refreshDetectedCountBadge();
      });
      rawInputEl.addEventListener("paste", handleTitlePasteClean);
      refreshDetectedCountBadge();
    }

    const fillSampleBtn = document.getElementById("btn-adas-fill-sample");
    if (fillSampleBtn && rawInputEl) {
      fillSampleBtn.addEventListener("click", () => {
        rawInputEl.value = sampleText;
        refreshDetectedCountBadge();
        appendInstantLogToUI("📋 Đã điền 3 tiêu đề mẫu (mỗi dòng 1 tiêu đề, tự động đánh Mã theo STT #1, #2, #3).", "SCRIPT", "INFO");
      });
    }

    const deleteAllBtn = document.getElementById("btn-adas-delete-all");
    if (deleteAllBtn) {
      deleteAllBtn.addEventListener("click", async () => {
        if (!lastSavedIdeasCache || lastSavedIdeasCache.length === 0) {
          alert("Kho dự án hiện đang trống!");
          return;
        }
        if (!confirm(`Bạn có chắc chắn muốn XÓA TẤT CẢ (${lastSavedIdeasCache.length} mã) khỏi danh sách Kho Dự Án không?`)) {
          return;
        }
        deleteAllBtn.disabled = true;
        appendInstantLogToUI(`🗑️ Đang xóa toàn bộ ${lastSavedIdeasCache.length} mã khỏi Kho Dự Án...`, "SCRIPT", "WARN");
        try {
          const res = await fetch("/api/adas/ideas/delete-all", { method: "POST" });
          if (res.ok) {
            const data = await res.json();
            renderSavedIdeasList(data.ideas || []);
          }
        } catch (e) {
          alert("Lỗi khi xóa tất cả: " + e.message);
        } finally {
          deleteAllBtn.disabled = false;
        }
      });
    }

    // 4b. Khởi tạo 2 nút chọn Chế Độ Xử Lý Tiêu Đề (1. Chạy Như Cũ Qua Skill 01 | 2. Dùng Tiêu Đề Gốc Vào Thẳng Skill 02)
    applyAdasTitleModeUI(window.currentAdasTitleMode || currentAdasTitleMode, false);
    document.querySelectorAll(".adas-title-mode-card").forEach((card) => {
      card.addEventListener("click", () => {
        const m = card.getAttribute("data-title-mode") || "rewrite";
        currentAdasTitleMode = m === "original" ? "original" : "rewrite";
        window.currentAdasTitleMode = currentAdasTitleMode;
        appendInstantLogToUI(
          m === "original"
            ? "📌 Đã chọn chế độ: DÙNG TIÊU ĐỀ GỐC (Bỏ qua Skill 01 • Giữ nguyên tiêu đề gốc tạo thẳng Giàn ý 7 Phần ở Skill 02)."
            : "🔄 Đã chọn chế độ: CHẠY NHƯ CŨ (Dùng Skill 01 viết lại 5 tiêu đề mới & chọn LOCKED_TITLE trước khi lập Giàn ý).",
          "SCRIPT",
          "INFO"
        );
      });
    });

    // 5. Nút Lưu Tiêu Đề & Thông Tin Vào Kho (Mỗi dòng 1 tiêu đề — Mã tự động theo STT)
    const saveIdeaBtn = document.getElementById("btn-adas-save-idea");
    if (saveIdeaBtn && rawInputEl) {
      saveIdeaBtn.addEventListener("click", async () => {
        const raw = rawInputEl.value.trim();
        if (!raw) {
          alert("Vui lòng dán 1 hoặc nhiều Tiêu đề (mỗi tiêu đề 1 dòng) trước khi lưu!");
          return;
        }
        const res = await fetch("/api/adas/ideas/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            raw_text: raw,
            custom_id: null,
            use_original_title: (window.currentAdasTitleMode || currentAdasTitleMode) === "original"
          })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          renderSavedIdeasList(data.ideas || []);
          rawInputEl.value = "";
          refreshDetectedCountBadge();
          const orig = saveIdeaBtn.innerText;
          const cnt = data.saved_count || 1;
          saveIdeaBtn.innerText = cnt > 1
            ? `✅ Đã Lưu ${cnt} Tiêu Đề Theo STT!`
            : `✅ Đã Lưu STT #${data.idea.ma_id}!`;
          setTimeout(() => { saveIdeaBtn.innerText = orig; }, 2200);
        } else {
          alert(data.detail || "Lỗi lưu tiêu đề!");
        }
      });
    }

    // 6. Nút Xem Trước Lệnh Step 2 Sẽ Gửi
    const previewStep2Btn = document.getElementById("btn-adas-preview-step2");
    if (previewStep2Btn && rawInputEl) {
      previewStep2Btn.addEventListener("click", async () => {
        const raw = rawInputEl.value.trim();
        if (!raw) {
          alert("Vui lòng dán Tiêu đề để xem trước lệnh Step 2!");
          return;
        }
        const res = await fetch("/api/adas/ideas/preview-prompt", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            raw_text: raw,
            custom_id: "1",
            use_original_title: (window.currentAdasTitleMode || currentAdasTitleMode) === "original"
          })
        });
        if (res.ok) {
          const data = await res.json();
          currentProjectDetailData = {
            ma_id: data.parsed.ma_id,
            step2_prompt: data.step2_prompt,
            seo_pack: "Chưa chạy Step 6",
            script_clean: "Chưa chạy Step 4",
            step2_output: "Chưa chạy Step 2",
            step3_output: "Chưa chạy Step 3",
            step5_output: "Chưa chạy Step 5"
          };
          const modal = document.getElementById("adas-detail-modal");
          const titleEl = document.getElementById("adas-detail-modal-title");
          if (titleEl) titleEl.innerText = `📋 XEM TRƯỚC LỆNH PROMPT STEP 2 — STT #${data.parsed.ma_id}`;
          switchDetailModalTab("step2_prompt");
          if (modal) modal.style.display = "flex";
        }
      });
    }

    // 7. Nút Lưu & Chỉ Viết KB + SEO + Thumbnail (Không Render Video)
    const saveAndScriptOnlyBtn = document.getElementById("btn-adas-save-and-script-only");
    if (saveAndScriptOnlyBtn && rawInputEl) {
      saveAndScriptOnlyBtn.addEventListener("click", async () => {
        const raw = rawInputEl.value.trim();
        if (!raw) {
          alert("Vui lòng dán 1 hoặc nhiều Tiêu đề (mỗi tiêu đề 1 dòng)!");
          return;
        }
        const res = await fetch("/api/adas/ideas/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            raw_text: raw,
            custom_id: null,
            use_original_title: (window.currentAdasTitleMode || currentAdasTitleMode) === "original"
          })
        });
        const data = await res.json();
        if (res.ok && data.success && data.idea) {
          renderSavedIdeasList(data.ideas || []);
          rawInputEl.value = "";
          refreshDetectedCountBadge();
          const idsToRun = (data.saved_ids && data.saved_ids.length > 0) ? data.saved_ids : [data.idea.ma_id];
          await triggerRunADAS(idsToRun, false);
        } else {
          alert(data.detail || "Không thể lưu tiêu đề!");
        }
      });
    }

    // 7b. Nút Lưu & Chạy Ngay (Hỗ trợ cả 1 mã hoặc SLL nhiều mã vừa dán)
    const saveAndRunBtn = document.getElementById("btn-adas-save-and-run");
    if (saveAndRunBtn && rawInputEl) {
      saveAndRunBtn.addEventListener("click", async () => {
        const raw = rawInputEl.value.trim();
        if (!raw) {
          alert("Vui lòng dán 1 hoặc nhiều Tiêu đề (mỗi tiêu đề 1 dòng)!");
          return;
        }
        const res = await fetch("/api/adas/ideas/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            raw_text: raw,
            custom_id: null,
            use_original_title: (window.currentAdasTitleMode || currentAdasTitleMode) === "original"
          })
        });
        const data = await res.json();
        if (res.ok && data.success && data.idea) {
          renderSavedIdeasList(data.ideas || []);
          rawInputEl.value = "";
          refreshDetectedCountBadge();
          const idsToRun = (data.saved_ids && data.saved_ids.length > 0) ? data.saved_ids : [data.idea.ma_id];
          await triggerRunADAS(idsToRun, null);
        } else {
          alert(data.detail || "Không thể lưu tiêu đề!");
        }
      });
    }

    // 8. Nút Mở Folder Kịch Bản, Nhập Từ Máy Khác, Khôi Phục Kịch Bản Cũ, Render Tất Cả Kịch Bản Đã Xong & Nút Chạy Đa Luồng (Kịch Bản -> Voice)
    const openProjectsDirBtn = document.getElementById("btn-adas-open-projects-dir");
    if (openProjectsDirBtn) {
      openProjectsDirBtn.addEventListener("click", async () => {
        const projInputEl = document.getElementById("adas-projects-dir-input") || document.getElementById("render-projects-dir");
        const baseOut = (projInputEl && projInputEl.value.trim())
          ? projInputEl.value.trim().replace(/[\\/]+$/, "")
          : ((outputDirInput && outputDirInput.value.trim()) ? outputDirInput.value.trim().replace(/[\\/]+$/, "") : "projects");
        await openSystemFolder(baseOut);
      });
    }

    const importExternalBtn = document.getElementById("btn-adas-import-external");
    if (importExternalBtn) {
      importExternalBtn.addEventListener("click", async () => {
        const origTxt = importExternalBtn.innerText;
        importExternalBtn.disabled = true;
        importExternalBtn.innerText = "📂 Đang chọn thư mục...";
        try {
          const browseRes = await fetch("/api/browse-directory", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: "Chọn Thư Mục Chứa Kịch Bản + Thumbnail + SEO Từ Máy Khác" })
          });
          const browseData = await browseRes.json().catch(() => ({}));
          if (!browseData.path) {
            return;
          }
          importExternalBtn.innerText = "⏳ Đang nạp dự án...";
          appendInstantLogToUI(`📥 Đang nhập Kịch bản + Thumbnail + SEO từ thư mục: ${browseData.path}...`, "SCRIPT", "INFO");
          const impRes = await fetch("/api/adas/ideas/import-external", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_path: browseData.path })
          });
          const impData = await impRes.json().catch(() => ({}));
          if (impRes.ok && impData.success) {
            renderSavedIdeasList(impData.ideas || []);
            const idsStr = (impData.imported_ids || []).join(", ");
            alert(
              `✅ Đã nhập thành công ${impData.imported_count} dự án (Kịch bản + Thumbnail + SEO) từ máy khác!\n\n` +
              `• Các mã vừa nạp: ${idsStr || "(Đã đồng bộ)"}\n` +
              `• Tổng số dự án trong kho: ${impData.total_count} mã\n\n` +
              `👉 Bạn có thể bấm ngay "🎬 Render" trên từng dòng hoặc "🎬 Render Tất Cả Đã Xong"!`
            );
          } else {
            alert(impData.detail || "Không tìm thấy kịch bản hợp lệ trong thư mục đã chọn!");
          }
        } catch (err) {
          alert("Lỗi khi nhập dự án từ máy khác: " + err.message);
        } finally {
          importExternalBtn.disabled = false;
          importExternalBtn.innerText = origTxt;
        }
      });
    }

    async function handleRefreshProjectsFolder(btnEl) {
      if (!btnEl) return;
      const origHtml = btnEl.innerHTML;
      btnEl.disabled = true;
      btnEl.innerText = "⏳ Đang cập nhật...";
      try {
        const projInputEl = document.getElementById("adas-projects-dir-input") || document.getElementById("render-projects-dir");
        const customOut = (projInputEl && projInputEl.value)
          ? projInputEl.value.trim()
          : ((outputDirInput && outputDirInput.value) ? outputDirInput.value.trim() : "");
        const res = await fetch("/api/adas/ideas/sync-folder", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ folder_path: customOut || "" })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          renderSavedIdeasList(data.ideas || []);
          appendInstantLogToUI(
            `🔄 Đã cập nhật lại thư mục projects/: Hiện có ${data.total_count} dự án (${data.script_done_count} kịch bản xong, ${data.video_done_count} video MP4, +${data.restored_count || 0} mới, -${data.removed_count || 0} đã xóa).`,
            "SCRIPT",
            "INFO"
          );
          alert(
            `✅ Đã cập nhật lại thư mục dự án thành công!\n\n` +
            `• Folder Project: ${data.projects_dir || "projects/"}\n` +
            `• Tổng số folder hiện có: ${data.total_count} mã\n` +
            `• Kịch bản đã viết xong (Sẵn sàng Render): ${data.script_done_count} kịch bản\n` +
            `• Video MP4 đã xuất: ${data.video_done_count} video\n` +
            `• Đã thêm mới: +${data.restored_count || 0} | Đã dọn folder bị xóa: -${data.removed_count || 0}`
          );
        }
      } catch (err) {
        alert("Lỗi khi cập nhật thư mục dự án: " + err.message);
      } finally {
        btnEl.disabled = false;
        btnEl.innerHTML = origHtml;
      }
    }

    ["btn-adas-refresh-folder", "btn-adas-restore-scripts", "btn-render-refresh-folder"].forEach((btnId) => {
      const b = document.getElementById(btnId);
      if (b) {
        b.addEventListener("click", () => handleRefreshProjectsFolder(b));
      }
    });

    async function handleCheckAndRepairAllProjects(btnEl) {
      if (!btnEl) return;
      if (!confirm(
        "🛡️ BẠN CÓ MUỐN QUÉT & DỌN SẠCH TOÀN BỘ KỊCH BẢN + VIDEO LỖI (PHƯƠNG ÁN 1 — 2 GIAI ĐOẠN SIÊU TỐC)?\n\n" +
        "Hệ thống sẽ thực hiện tự động:\n" +
        "1️⃣ GIAI ĐOẠN 1 (1–2 giây): Quét toàn bộ kịch bản (.txt) và phụ đề (.srt) trong kho để xóa sạch 100% các dòng [LOCKED_TITLE], PART A/B/C, STEP 3 bị rò rỉ.\n" +
        "2️⃣ GIAI ĐOẠN 2 (4–8 giây/video): Chỉ với các dự án ĐÃ TẠO VIDEO (.mp4) hoặc VOICE (.wav) bị đọc nhầm câu tiêu đề -> Tự động cắt bỏ chính xác giây đọc nhầm bằng FFmpeg Stream Copy & Python WAV Slicer (hiển thị trực tiếp từng video 1/N, 2/N đang cắt).\n" +
        "3️⃣ Xuất báo cáo chi tiết tại BAO_CAO_CHECK_VA_DON_TOAN_BO.txt.\n\n" +
        "Bấm OK để bắt đầu quét và dọn sạch ngay!"
      )) {
        return;
      }

      const allRepairBtns = ["btn-adas-check-repair-all", "btn-check-repair-all-nav"]
        .map((id) => document.getElementById(id))
        .filter(Boolean);
      const origHtmlMap = new Map();
      allRepairBtns.forEach((b) => {
        origHtmlMap.set(b, b.innerHTML);
        b.disabled = true;
        b.innerText = "⚡ Bước 1/2: Đang dọn Kịch bản...";
      });

      appendInstantLogToUI(
        "🛡️ [CHECK TOÀN BỘ - 2 GIAI ĐOẠN SIÊU TỐC] Bắt đầu Giai đoạn 1: Quét & dọn sạch toàn bộ Kịch bản (.txt/.srt)...",
        "SYSTEM",
        "INFO"
      );

      const customOut = (outputDirInput && outputDirInput.value) ? outputDirInput.value.trim() : "";

      const showCompletionSummary = (data) => {
        if (Array.isArray(data.ideas)) {
          renderSavedIdeasList(data.ideas);
        }
        const totalProj = data.total_projects || data.total_scanned || 0;
        const totalLines = data.total_leaked_lines_removed || data.total_lines_removed || 0;
        const repairedScriptStr = (data.repaired_script_ids && data.repaired_script_ids.length > 0)
          ? data.repaired_script_ids.join(", ")
          : "Không có (Đã sạch 100%)";
        const repairedVideoStr = (data.repaired_video_ids && data.repaired_video_ids.length > 0)
          ? data.repaired_video_ids.join(", ")
          : "Không có video nào bị dính";
        const repairedVoiceStr = (data.repaired_voice_ids && data.repaired_voice_ids.length > 0)
          ? data.repaired_voice_ids.join(", ")
          : "Không có file voice nào bị dính";

        appendInstantLogToUI(
          `✅ [CHECK TOÀN BỘ HOÀN TẤT] Đã quét ${totalProj} dự án (${data.elapsed_sec || 0}s) | ` +
          `Sửa kịch bản: ${data.scripts_repaired_count || 0} mã (${totalLines} dòng) | ` +
          `Dọn phụ đề SRT: ${data.srts_repaired_count || 0} mã | ` +
          `Cắt dọn Voice WAV: ${data.voices_repaired_count || 0} mã | ` +
          `Cắt dọn Video MP4: ${data.videos_repaired_count || 0} video.`,
          "SYSTEM",
          "INFO"
        );

        alert(
          `🎉 HOÀN TẤT CHECK & DỌN SẠCH TOÀN BỘ (PHƯƠNG ÁN 1)!\n\n` +
          `• Tổng số dự án đã kiểm tra: ${totalProj} dự án (Tổng thời gian: ${data.elapsed_sec || 0}s | Dọn KB: ${data.phase1_script_sec || 0}s)\n` +
          `• Số kịch bản (.txt) đã lọc sạch [LOCKED_TITLE]: ${data.scripts_repaired_count || 0} kịch bản (${totalLines} dòng lỗi)\n` +
          `• Số phụ đề (.srt) đã dọn & dịch khớp thời gian: ${data.srts_repaired_count || 0} file\n` +
          `• Số file Voice (.wav) đã cắt bỏ đoạn đọc nhầm: ${data.voices_repaired_count || 0} file\n` +
          `• Số Video (.mp4) đã cắt bỏ đoạn đọc nhầm: ${data.videos_repaired_count || 0} video\n\n` +
          `📌 Mã kịch bản đã sửa: ${repairedScriptStr}\n` +
          `📌 Mã Voice đã dọn: ${repairedVoiceStr}\n` +
          `📌 Mã Video MP4 đã dọn: ${repairedVideoStr}\n\n` +
          `📄 Báo cáo chi tiết đã lưu tại:\n${data.report_path || "BAO_CAO_CHECK_VA_DON_TOAN_BO.txt"}`
        );
      };

      try {
        const startRes = await fetch("/api/adas/check-and-repair-all", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "start", folder_path: customOut || "" })
        });
        const startData = await startRes.json().catch(() => ({}));
        if (!startRes.ok || !startData.success) {
          alert("❌ Lỗi khi khởi chạy Check & Dọn Toàn Bộ: " + (startData.detail || startData.error || "Không xác định"));
          return;
        }

        // Nếu server trả về kết quả đồng bộ ngay lập tức (fallback)
        if (!startData.async_started && (startData.total_scanned !== undefined || startData.total_projects !== undefined)) {
          showCompletionSummary(startData);
          return;
        }

        // Vòng lặp theo dõi tiến độ thời gian thực mỗi 0.7 giây (không bao giờ bị treo HTTP)
        let seenLogCount = 0;
        while (true) {
          await new Promise((r) => setTimeout(r, 700));
          const stRes = await fetch("/api/adas/check-and-repair-all", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "status" })
          });
          if (!stRes.ok) continue;
          const stData = await stRes.json().catch(() => ({}));
          if (!stData || !stData.success) continue;

          const logsArr = Array.isArray(stData.logs) ? stData.logs : [];
          while (seenLogCount < logsArr.length) {
            appendInstantLogToUI(logsArr[seenLogCount], "SCRIPT", "INFO");
            seenLogCount++;
          }

          const pct = Math.round(Number(stData.progress || 0));
          const rawMsg = String(stData.status_text || "Đang xử lý...");
          let shortBtnTxt = `⏳ ${pct}% • Đang dọn lỗi...`;
          const mStep1 = rawMsg.match(/Đang quét\s+(\d+\/\d+)/i);
          const mStep2 = rawMsg.match(/Video\s+(\d+\/\d+\s*•\s*[A-Za-z0-9_]+)/i);
          if (mStep2) {
            shortBtnTxt = `✂️ ${pct}% • Video ${mStep2[1]}`;
          } else if (mStep1) {
            shortBtnTxt = `⚡ ${pct}% • Quét KB ${mStep1[1]}`;
          }
          allRepairBtns.forEach((b) => {
            b.innerText = shortBtnTxt;
          });

          if (stData.completed || !stData.running) {
            if (stData.error) {
              alert("❌ Lỗi khi Check & Dọn Toàn Bộ: " + stData.error);
            } else if (stData.result) {
              showCompletionSummary(stData.result);
            }
            break;
          }
        }
      } catch (err) {
        alert("❌ Lỗi kết nối khi Check & Dọn Toàn Bộ: " + err.message);
      } finally {
        allRepairBtns.forEach((b) => {
          b.disabled = false;
          if (origHtmlMap.has(b)) {
            b.innerHTML = origHtmlMap.get(b);
          }
        });
      }
    }

    ["btn-adas-check-repair-all", "btn-check-repair-all-nav"].forEach((btnId) => {
      const b = document.getElementById(btnId);
      if (b) {
        b.addEventListener("click", () => handleCheckAndRepairAllProjects(b));
      }
    });

    const retryErrorsBtn = document.getElementById("btn-adas-retry-errors");
    if (retryErrorsBtn) {
      retryErrorsBtn.addEventListener("click", async () => {
        const res = await fetch("/api/adas/ideas");
        if (!res.ok) return;
        const data = await res.json();
        const errOrIncompleteIds = (data.ideas || [])
          .filter((it) => {
            const hasFullScript = !!it.has_script && (it.pure_char_count || 0) >= 35000;
            const isErr = it.status === "ERROR" || it.status === "ERROR_VIDEO" || it.status === "PARTIAL_SCRIPT";
            return isErr || !hasFullScript;
          })
          .map((it) => it.ma_id);
        if (errOrIncompleteIds.length === 0) {
          alert("✅ Tuyệt vời! Không có kịch bản nào bị lỗi hay thiếu Part trong kho (Tất cả đã hoàn thành đủ 3 Part >= 35,000 chữ).\n\n👉 Nếu bạn muốn viết lại từ đầu cho một mã cụ thể, hãy bấm nút '🔁 Viết Lại' ngay trên dòng của mã đó!");
          return;
        }
        appendInstantLogToUI(
          `🔁 Kích hoạt viết lại / chạy bù cho ${errOrIncompleteIds.length} mã lỗi/thiếu: ${errOrIncompleteIds.join(", ")} (Tự động Retry tối đa 3 lần)...`,
          "SCRIPT",
          "INFO"
        );
        await triggerRunADAS(errOrIncompleteIds, null, false);
      });
    }

    const renderReadyBtn = document.getElementById("btn-adas-render-ready");
    if (renderReadyBtn) {
      renderReadyBtn.addEventListener("click", async () => {
        const res = await fetch("/api/adas/ideas");
        if (!res.ok) return;
        const data = await res.json();
        const readyIds = (data.ideas || [])
          .filter((it) => (!!it.has_script && (it.pure_char_count || 0) >= 35000) && (!it.has_video_mp4 || it.status !== "COMPLETED_VIDEO"))
          .map((it) => it.ma_id);
        if (readyIds.length === 0) {
          alert("Hiện chưa có dự án nào đã viết xong đủ 3 Part kịch bản (>= 35,000 chữ) mà đang chờ xuất MP4!\n\n• Với các dự án đang thiếu Part B/C (màu cam), hãy bấm '▶️ Viết Tiếp' hoặc '▶️ Chạy Đa Luồng' để hoàn thành đủ 3 Part trước.");
          return;
        }
        await triggerRenderOnly(readyIds, true);
      });
    }

    const scriptOnlyAllBtn = document.getElementById("btn-adas-script-only-all");
    if (scriptOnlyAllBtn) {
      scriptOnlyAllBtn.addEventListener("click", async () => {
        const res = await fetch("/api/adas/ideas");
        if (!res.ok) return;
        const data = await res.json();
        const pendingScriptIds = (data.ideas || [])
          .filter((it) => {
            const hasFullScript = !!it.has_script && (it.pure_char_count || 0) >= 35000;
            const hasThumb = !!it.has_thumbnail;
            const hasSeo = !!it.has_seo;
            return !(hasFullScript && hasThumb && hasSeo);
          })
          .map((it) => it.ma_id);
        if (pendingScriptIds.length === 0) {
          alert("Tất cả các mã trong kho đã có đủ Kịch bản 3 Part (>= 35,000 chữ) + SEO + Thumbnail!\n\n👉 Bạn có thể copy thư mục sang máy khác hoặc bấm '🎬 Render Tất Cả Đã Xong' nếu muốn xuất MP4.");
          return;
        }
        await triggerRunADAS(pendingScriptIds, false);
      });
    }

    const runAllBtn = document.getElementById("btn-adas-run-all");
    if (runAllBtn) {
      runAllBtn.addEventListener("click", async () => {
        const res = await fetch("/api/adas/ideas");
        if (!res.ok) return;
        const data = await res.json();
        const pendingIds = (data.ideas || [])
          .filter((it) => !it.has_video_mp4 && it.status !== "COMPLETED_VIDEO")
          .map((it) => it.ma_id);
        if (pendingIds.length === 0) {
          alert("Tất cả các mã trong kho đã hoàn tất xuất Video MP4! Bạn có thể bấm '🎬 Render MP4' trên từng mã nếu muốn xuất lại.");
          return;
        }
        await triggerRunADAS(pendingIds, null);
      });
    }

    const stopBtn = document.getElementById("btn-adas-stop");
    if (stopBtn) {
      stopBtn.addEventListener("click", async () => {
        await fetch("/api/adas/stop", { method: "POST" });
      });
    }

    // 9. Modal Xem Chi Tiết Kết Quả Dự Án Mexico & Phóng To Ảnh Thumbnail
    const closeDetailBtn = document.getElementById("btn-close-adas-detail-modal");
    const detailModal = document.getElementById("adas-detail-modal");
    if (closeDetailBtn && detailModal) {
      closeDetailBtn.addEventListener("click", () => {
        detailModal.style.display = "none";
        detailModal.classList.add("hidden");
      });
    }

    const detailOpenFolderBtn = document.getElementById("btn-adas-detail-open-folder");
    if (detailOpenFolderBtn) {
      detailOpenFolderBtn.addEventListener("click", async () => {
        if (!currentProjectDetailData) return;
        const dir = currentProjectDetailData.raw_project_dir || currentProjectDetailData.project_dir;
        if (dir) await openSystemFolder(dir);
      });
    }

    const regenThumbsBtn = document.getElementById("btn-adas-regenerate-thumbs");
    if (regenThumbsBtn) {
      regenThumbsBtn.addEventListener("click", async () => {
        if (!currentProjectDetailData || !currentProjectDetailData.ma_id) return;
        const mid = currentProjectDetailData.ma_id;
        const origTxt = regenThumbsBtn.innerText;
        regenThumbsBtn.disabled = true;
        regenThumbsBtn.innerText = "⏳ Đang vẽ lại...";
        try {
          const res = await fetch(`/api/adas/project/${encodeURIComponent(mid)}/generate-thumbnails?force=true`, {
            method: "POST"
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            alert(data.detail || "Không thể khởi chạy vẽ lại Thumbnail!");
          } else {
            alert(`🎨 Đã bắt đầu vẽ & tách lại cặp Thumbnail + Nền Xanh cho dự án Mexico #${mid}!`);
          }
        } catch (e) {
          alert("Lỗi khởi chạy vẽ lại Thumbnail: " + e.message);
        } finally {
          regenThumbsBtn.disabled = false;
          regenThumbsBtn.innerText = origTxt;
        }
      });
    }

    document.querySelectorAll(".adas-view-tab").forEach((b) => {
      b.addEventListener("click", () => switchDetailModalTab(b.dataset.tab));
    });

    document.querySelectorAll(".adas-script-stage-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (!currentProjectDetailData) return;
        const stg = btn.dataset.stage || "full_script";
        document.querySelectorAll(".adas-script-stage-btn").forEach((b) => {
          if (b.dataset.stage === stg) {
            b.className = "adas-script-stage-btn px-2 py-0.5 rounded bg-primary-container/20 text-primary-container border border-primary-container/40 font-bold";
          } else {
            b.className = "adas-script-stage-btn px-2 py-0.5 rounded bg-surface-container hover:bg-surface-container-high text-on-surface-variant";
          }
        });
        const txtArea = document.getElementById("adas-detail-textarea");
        if (!txtArea) return;
        if (stg === "part_a") {
          txtArea.value = currentProjectDetailData.part_a || "(Không tìm thấy file part_a.txt riêng — xem tại Toàn Bộ 7 Phần)";
        } else if (stg === "part_b") {
          txtArea.value = currentProjectDetailData.part_b || "(Không tìm thấy file part_b.txt riêng — xem tại Toàn Bộ 7 Phần)";
        } else if (stg === "part_c") {
          txtArea.value = currentProjectDetailData.part_c || "(Không tìm thấy file part_c.txt riêng — xem tại Toàn Bộ 7 Phần)";
        } else {
          txtArea.value = currentProjectDetailData.full_script || currentProjectDetailData.script_clean || "";
        }
      });
    });

    // Sự kiện cho Lightbox Phóng To Ảnh Thumbnail & Nền Xanh
    const zoomModal = document.getElementById("mexico-image-zoom-modal");
    const closeZoomBtn = document.getElementById("btn-close-mexico-zoom");
    const zoomInBtn = document.getElementById("btn-zoom-in");
    const zoomOutBtn = document.getElementById("btn-zoom-out");
    const zoomResetBtn = document.getElementById("btn-zoom-reset");
    const zoomSwitchMainBtn = document.getElementById("btn-zoom-switch-main");
    const zoomSwitchGreenBtn = document.getElementById("btn-zoom-switch-green");
    const zoomViewport = document.getElementById("mexico-zoom-viewport");

    if (closeZoomBtn && zoomModal) {
      closeZoomBtn.addEventListener("click", () => {
        zoomModal.style.display = "none";
        zoomModal.classList.add("hidden");
      });
    }
    if (zoomInBtn) zoomInBtn.addEventListener("click", () => updateMexicoZoomScale(currentZoomScale + 0.25));
    if (zoomOutBtn) zoomOutBtn.addEventListener("click", () => updateMexicoZoomScale(currentZoomScale - 0.25));
    if (zoomResetBtn) zoomResetBtn.addEventListener("click", () => updateMexicoZoomScale(1.0));
    if (zoomSwitchMainBtn) zoomSwitchMainBtn.addEventListener("click", () => openMexicoImageZoomLightbox("main"));
    if (zoomSwitchGreenBtn) zoomSwitchGreenBtn.addEventListener("click", () => openMexicoImageZoomLightbox("green"));
    if (zoomViewport) {
      zoomViewport.addEventListener("wheel", (ev) => {
        ev.preventDefault();
        const delta = ev.deltaY < 0 ? 0.2 : -0.2;
        updateMexicoZoomScale(currentZoomScale + delta);
      }, { passive: false });
      zoomViewport.addEventListener("click", (ev) => {
        if (ev.target === zoomViewport && zoomModal) {
          zoomModal.style.display = "none";
          zoomModal.classList.add("hidden");
        }
      });
    }
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") {
        if (zoomModal && !zoomModal.classList.contains("hidden") && zoomModal.style.display !== "none") {
          zoomModal.style.display = "none";
          zoomModal.classList.add("hidden");
          return;
        }
        ["adas-detail-modal", "stock-modal", "license-modal", "step2-template-modal"].forEach((mid) => {
          const mEl = document.getElementById(mid);
          if (mEl && (!mEl.classList.contains("hidden") || mEl.style.display === "flex")) {
            mEl.style.display = "none";
            mEl.classList.add("hidden");
          }
        });
      }
    });

    const copyDetailBtn = document.getElementById("btn-adas-copy-detail");
    if (copyDetailBtn) {
      copyDetailBtn.addEventListener("click", () => {
        const txtArea = document.getElementById("adas-detail-textarea");
        if (txtArea && txtArea.value) {
          navigator.clipboard.writeText(txtArea.value);
          const orig = copyDetailBtn.innerText;
          copyDetailBtn.innerText = "✅ Đã Copy!";
          setTimeout(() => { copyDetailBtn.innerText = orig; }, 1800);
        }
      });
    }

    const pushToSingleBtn = document.getElementById("btn-adas-push-to-single");
    if (pushToSingleBtn) {
      pushToSingleBtn.addEventListener("click", async () => {
        if (!currentProjectDetailData || !currentProjectDetailData.script_clean) {
          alert("Dự án Mexico này chưa có kịch bản hoàn chỉnh.");
          return;
        }
        if (detailModal) {
          detailModal.style.display = "none";
          detailModal.classList.add("hidden");
        }
        await triggerRenderOnly([currentProjectDetailData.ma_id], false);
      });
    }

    // 10. Modal Cấu Hình Mẫu Lệnh Step 2
    const openTplBtn = document.getElementById("btn-open-step2-tpl-modal");
    const closeTplBtn = document.getElementById("btn-close-step2-tpl-modal");
    const tplModal = document.getElementById("step2-template-modal");
    const tplTextarea = document.getElementById("step2-template-textarea");
    const saveTplBtn = document.getElementById("btn-save-step2-tpl");

    if (openTplBtn && tplModal && tplTextarea) {
      openTplBtn.addEventListener("click", async () => {
        const res = await fetch("/api/adas/template/step2");
        if (res.ok) {
          const data = await res.json();
          tplTextarea.value = data.template_text || "";
        }
        tplModal.style.display = "flex";
      });
    }
    if (closeTplBtn && tplModal) {
      closeTplBtn.addEventListener("click", () => { tplModal.style.display = "none"; });
    }
    if (saveTplBtn && tplTextarea && tplModal) {
      saveTplBtn.addEventListener("click", async () => {
        const res = await fetch("/api/adas/template/step2", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ template_text: tplTextarea.value })
        });
        if (res.ok) {
          tplModal.style.display = "none";
        }
      });
    }

    // Khởi chạy tải dữ liệu ban đầu & lặp kiểm tra trạng thái 3 Acc
    refreshChatGPTAccountsBar(false);
    loadSavedIdeas();
    setInterval(() => refreshChatGPTAccountsBar(false), 6000);
  }

  // ============================================================================
  // 12. TRUNG TÂM NHẬT KÝ HỆ THỐNG, TELEMETRY RADIAL GAUGES & DIAGNOSTICS
  // ============================================================================
  let currentLogLevelFilter = "ALL";
  let currentLogCatFilter = "ALL";
  let latestLogEntriesCache = [];
  let latestLogPathsCache = null;
  let isTerminalAutoScroll = true;

  function setupTelemetryPolling() {
    const CIRCUMFERENCE = 226.2; // 2 * Math.PI * 36

    function updateSvgRadialArc(el, pct) {
      if (!el) return;
      if (el.tagName && el.tagName.toLowerCase() === "path") {
        el.setAttribute("stroke-dasharray", `${pct}, 100`);
      } else {
        const offset = CIRCUMFERENCE * (1 - pct / 100);
        el.setAttribute("stroke-dashoffset", offset.toFixed(1));
      }
    }

    async function pollTelemetryNow() {
      try {
        const res = await fetch("/api/telemetry");
        if (!res.ok) return;
        const t = await res.json();

        // 1. GPU Gauge & VRAM
        const gpuPct = Math.max(0, Math.min(100, Math.round(t.gpu_load_pct ?? t.gpu_percent ?? 0)));
        const gpuCircle = document.getElementById("gauge-gpu-circle");
        const gpuPctEl = document.getElementById("gauge-gpu-pct");
        const gpuTempEl = document.getElementById("gauge-gpu-temp");
        const gpuNameEl = document.getElementById("gauge-gpu-name");
        const vramTextEl = document.getElementById("gauge-vram-text");
        const vramBarEl = document.getElementById("gauge-vram-bar");
        const renderVramBar = document.getElementById("render-vram-bar");
        const renderVramText = document.getElementById("render-vram-text");
        const gpuFanEl = document.getElementById("telemetry-gpu-fan");

        if (gpuPctEl) gpuPctEl.innerText = `${gpuPct}%`;
        updateSvgRadialArc(gpuCircle, gpuPct);
        if (gpuTempEl && t.gpu_temp_c) gpuTempEl.innerText = `${t.gpu_temp_c}°C`;
        if (gpuNameEl && t.gpu_name) gpuNameEl.innerText = t.gpu_name;
        if (t.vram_total_gb) {
          const vramStr = `VRAM: ${Number(t.vram_used_gb || 0).toFixed(1)} / ${Number(t.vram_total_gb).toFixed(1)} GB`;
          const vramPct = Math.max(4, Math.min(100, Math.round(t.vram_pct ?? t.vram_percent ?? 0)));
          if (vramTextEl) vramTextEl.innerText = vramStr;
          if (vramBarEl) vramBarEl.style.width = `${vramPct}%`;
          if (renderVramBar) renderVramBar.style.width = `${vramPct}%`;
          if (renderVramText) renderVramText.innerText = `${Number(t.vram_used_gb || 0).toFixed(1)} / ${Number(t.vram_total_gb).toFixed(1)} GB`;
        }
        if (gpuFanEl && t.gpu_fan_pct !== undefined) {
          const rpmEst = Math.round(900 + (t.gpu_fan_pct / 100) * 1800);
          gpuFanEl.innerText = `${t.gpu_fan_pct}% (${rpmEst} RPM)`;
        }

        // 2. System Memory Gauge
        const ramPct = Math.max(0, Math.min(100, Math.round(t.ram_pct ?? t.ram_percent ?? 0)));
        const ramCircle = document.getElementById("gauge-ram-circle");
        const ramPctEl = document.getElementById("gauge-ram-pct");
        const ramTextEl = document.getElementById("gauge-ram-text");
        const ramBarEl = document.getElementById("gauge-ram-bar");

        if (ramPctEl) ramPctEl.innerText = `${ramPct}%`;
        updateSvgRadialArc(ramCircle, ramPct);
        if (ramTextEl && t.ram_total_gb) {
          ramTextEl.innerText = `${Number(t.ram_used_gb || 0).toFixed(1)} / ${Number(t.ram_total_gb).toFixed(1)} GB RAM`;
        }
        if (ramBarEl) ramBarEl.style.width = `${Math.max(4, ramPct)}%`;

        // 3. CPU Gauge
        const cpuPct = Math.max(0, Math.min(100, Math.round(t.cpu_load_pct ?? t.cpu_percent ?? 0)));
        const cpuCircle = document.getElementById("gauge-cpu-circle");
        const cpuPctEl = document.getElementById("gauge-cpu-pct");
        const cpuThreadsEl = document.getElementById("gauge-cpu-threads");
        const cpuNameEl = document.getElementById("gauge-cpu-name");
        const cpuBarEl = document.getElementById("gauge-cpu-bar");
        const headerCpuThreads = document.getElementById("header-cpu-threads");

        if (cpuPctEl) cpuPctEl.innerText = `${cpuPct}%`;
        updateSvgRadialArc(cpuCircle, cpuPct);
        if (cpuThreadsEl && t.cpu_threads) cpuThreadsEl.innerText = `${t.cpu_threads} Th`;
        if (headerCpuThreads && t.cpu_threads) headerCpuThreads.innerText = `${t.cpu_threads} CORES`;
        if (cpuNameEl && t.cpu_name) cpuNameEl.innerText = t.cpu_name;
        if (cpuBarEl) cpuBarEl.style.width = `${Math.max(4, cpuPct)}%`;

        // 4. CDP AI Chrome Gauge
        const cdpCountEl = document.getElementById("gauge-cdp-count");
        const cdpPortsBox = document.getElementById("gauge-cdp-ports-status");
        if (cdpCountEl && t.cdp_active_count !== undefined) {
          cdpCountEl.innerText = `${t.cdp_active_count}/5 ACTIVE`;
        }
        if (cdpPortsBox && Array.isArray(t.cdp_ports)) {
          cdpPortsBox.innerHTML = t.cdp_ports.map((p) => {
            const label = p.label || p.acc || `P${p.port}`;
            if (p.open) {
              return `<span class="flex items-center gap-1 text-[10px] font-mono text-primary-container"><span class="w-1.5 h-1.5 rounded-full bg-primary-container shadow-[0_0_6px_rgba(0,255,135,0.8)]"></span>${label} Ready</span>`;
            }
            return `<span class="flex items-center gap-1 text-[10px] font-mono text-on-surface-variant"><span class="w-1.5 h-1.5 rounded-full bg-outline-variant"></span>${label} Idle</span>`;
          }).join("");
        }

        // Update GPU balancer badge in Tab 3
        const balEl = document.getElementById("gpu-balancer-badge");
        if (balEl) {
          balEl.innerText = `TỰ CÂN ĐỐI 90%: GPU ${gpuPct}% • CPU ${cpuPct}%`;
        }
      } catch (e) {
        // Ignore transient errors
      }
    }

    pollTelemetryNow();
    setInterval(pollTelemetryNow, 4000);
  }

  function formatLogEntryHtml(e) {
    const lvl = e.level || "INFO";
    const color =
      lvl === "ERROR"
        ? "#ff6b6b"
        : lvl === "WARN"
        ? "#ffd54f"
        : e.category === "VIDEO" || e.category === "VOICE" || e.category === "RENDER"
        ? "#00e676"
        : "#00e5ff";
    const projBadge = e.project_id ? `<strong style="color: var(--accent-gold);">[${e.project_id}]</strong> ` : "";
    const safeMsg = (e.message || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return `<div style="margin-bottom: 3px; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 2px;">
      <span style="color: #8899ac;">[${e.timestamp || ""}]</span>
      <span style="color: ${color}; font-weight: 700;">[${lvl}/${e.category || "SYS"}]</span>
      ${projBadge}<span style="color: ${lvl === "ERROR" ? "#ff9e9e" : "#e2e8f0"};">${safeMsg}</span>
    </div>`;
  }

  function entryMatchesFilter(e) {
    if (!e) return false;
    const lvl = (e.level || "INFO").toUpperCase();
    const cat = (e.category || "SYSTEM").toUpperCase();
    if (currentLogLevelFilter === "ERROR") {
      if (lvl !== "ERROR" && lvl !== "WARN" && lvl !== "WARNING" && !(e.message || "").includes("❌") && !(e.message || "").includes("⚠️")) {
        return false;
      }
    }
    if (currentLogCatFilter && currentLogCatFilter !== "ALL") {
      if (currentLogCatFilter === "VIDEO") {
        if (!["VIDEO", "VOICE", "RENDER", "STOCK"].includes(cat)) return false;
      } else if (cat !== currentLogCatFilter) {
        return false;
      }
    }
    return true;
  }

  function pushLogEntryToConsole(entry) {
    if (!entry) return;
    const last = latestLogEntriesCache[latestLogEntriesCache.length - 1];
    if (last && last.timestamp === entry.timestamp && last.message === entry.message) {
      return;
    }
    latestLogEntriesCache.push(entry);
    if (latestLogEntriesCache.length > 300) {
      latestLogEntriesCache = latestLogEntriesCache.slice(-300);
    }
    const lineCntEl = document.getElementById("log-line-count");
    if (lineCntEl) lineCntEl.innerText = `${latestLogEntriesCache.length} dòng`;
    if (!entryMatchesFilter(entry)) return;
    const consoleEl = document.getElementById("system-log-console");
    if (!consoleEl) return;
    if (consoleEl.innerText.includes("Chưa có bản ghi nhật ký") || consoleEl.innerText.includes("Đang tải nhật ký")) {
      consoleEl.innerHTML = "";
    }
    consoleEl.insertAdjacentHTML("beforeend", formatLogEntryHtml(entry));
    if (isTerminalAutoScroll) {
      consoleEl.scrollTop = consoleEl.scrollHeight;
    }
  }

  function appendInstantLogToUI(message, category = "SYSTEM", level = "INFO", projectId = "") {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const ts = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    pushLogEntryToConsole({
      timestamp: ts,
      level: level,
      category: category,
      project_id: projectId,
      message: message
    });
  }

  async function fetchSystemLogs() {
    const consoleEl = document.getElementById("system-log-console");
    if (!consoleEl) return;
    try {
      const qs = new URLSearchParams({
        limit: "200",
        level: currentLogLevelFilter,
        category: currentLogCatFilter
      });
      const res = await fetch(`/api/logs?${qs.toString()}`);
      if (!res.ok) return;
      const data = await res.json();
      latestLogEntriesCache = data.entries || [];
      latestLogPathsCache = data.log_paths || null;
      const lineCntEl = document.getElementById("log-line-count");
      if (lineCntEl) lineCntEl.innerText = `${latestLogEntriesCache.length} dòng`;

      if (latestLogEntriesCache.length === 0) {
        consoleEl.innerHTML = `<div style="color: var(--text-secondary);">Chưa có bản ghi nhật ký nào khớp bộ lọc hiện tại.</div>`;
        return;
      }

      const wasAtBottom = consoleEl.scrollHeight - consoleEl.scrollTop - consoleEl.clientHeight < 60;
      consoleEl.innerHTML = latestLogEntriesCache.map((e) => formatLogEntryHtml(e)).join("");

      if (isTerminalAutoScroll && wasAtBottom) {
        consoleEl.scrollTop = consoleEl.scrollHeight;
      }
    } catch (e) {
      // Bỏ qua nếu server đang bận
    }
  }

  async function triggerInstallMissingLibs() {
    const btn = document.getElementById("btn-install-missing-libs");
    const origHtml = btn ? btn.innerHTML : "";
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>Đang cài đặt...`;
    }
    appendInstantLogToUI("⚡ Đang gửi yêu cầu kiểm tra và cài đặt các thư viện thiếu / PyTorch CUDA...", "SYSTEM", "INFO");
    try {
      const res = await fetch("/api/diagnostics/install-missing?install_cuda=true", { method: "POST" });
      const data = await res.json();
      alert(data.message || "Đã bắt đầu kiểm tra và cài đặt thư viện trong nền. Vui lòng theo dõi bảng Nhật Ký Hệ Thống!");
      await fetchSystemLogs();
    } catch (e) {
      alert("Lỗi khi gọi cài đặt thư viện: " + e.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = origHtml || `<span class="material-symbols-outlined text-[16px]">build_circle</span>Cài Thư Viện Thiếu &amp; CUDA`;
      }
    }
  }

  async function runSystemDiagnosticsUI(silentOnStartup = false) {
    const box = document.getElementById("diagnostics-report-box");
    const btn = document.getElementById("btn-run-diagnostics");
    const summaryBadgesEl = document.getElementById("diag-summary-badges");
    const detailsListEl = document.getElementById("diag-details-list");
    const passCounterEl = document.getElementById("diag-pass-counter");
    const origBtnHtml = btn ? btn.innerHTML : "";

    if (!silentOnStartup && btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>Đang kiểm tra...`;
    }

    try {
      const res = await fetch("/api/diagnostics");
      const data = await res.json();
      const checks = data.checks || [];
      const missingReqs = data.missing_requirements || [];

      const okCount = checks.filter(c => c.status === "OK").length;
      if (passCounterEl && checks.length > 0) {
        passCounterEl.innerText = `PASS: ${okCount}/${checks.length} CHECKS`;
      }

      if (summaryBadgesEl && checks.length > 0) {
        summaryBadgesEl.innerHTML = checks.slice(0, 6).map((c) => {
          const isOk = c.status === "OK";
          const isWarn = c.status === "WARN";
          const cls = isOk
            ? "bg-primary-container/10 border-primary-container/30 text-primary-container"
            : isWarn
            ? "bg-tertiary/10 border-tertiary/30 text-tertiary"
            : "bg-error/10 border-error/30 text-error";
          const dotCls = isOk ? "bg-primary-container" : isWarn ? "bg-tertiary" : "bg-error";
          return `<span class="px-2.5 py-1 rounded-md border ${cls} font-mono text-[11px] font-bold flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full ${dotCls}"></span>${c.name}: ${c.status}
          </span>`;
        }).join("");
      }

      if (detailsListEl && checks.length > 0) {
        const missingBannerHtml = missingReqs.length > 0
          ? `<div class="p-2.5 rounded-lg bg-error-container/25 border border-error/40 text-xs space-y-1.5 mb-2">
              <div class="font-bold text-error">⚠️ PHÁT HIỆN ${missingReqs.length} THƯ VIỆN / PHẦN MỀM TỐI ƯU GPU CẦN CÀI ĐẶT:</div>
              ${missingReqs.map((r) => `
                <div class="p-1.5 rounded bg-surface-container-lowest/80 border border-outline-variant/20">
                  <div class="font-bold text-tertiary">🔸 ${r.title}</div>
                  <div class="text-on-surface-variant text-[10px]">• ${r.reason}</div>
                </div>
              `).join("")}
              <button type="button" id="btn-diag-auto-install" class="px-3 py-1 rounded bg-primary-container text-on-primary-container font-bold text-xs">
                ⚡ Tự Động Tải &amp; Cài Thư Viện Thiếu / PyTorch CUDA Ngay
              </button>
            </div>`
          : "";

        detailsListEl.innerHTML = missingBannerHtml + checks.map((c) => {
          const isOk = c.status === "OK";
          const isWarn = c.status === "WARN";
          const iconName = isOk ? "check_circle" : isWarn ? "warning" : "error";
          const iconColor = isOk ? "text-primary-container" : isWarn ? "text-tertiary" : "text-error";
          const badgeCls = isOk
            ? "bg-primary-container/15 text-primary-container border-primary-container/30"
            : isWarn
            ? "bg-tertiary/15 text-tertiary border-tertiary/30"
            : "bg-error/15 text-error border-error/30";
          return `
            <div class="flex items-center justify-between p-2 rounded-lg bg-surface-container/60 border border-outline-variant/15 hover:border-outline-variant/40 transition-colors">
              <div class="flex items-center gap-2.5 min-w-0 pr-2">
                <span class="material-symbols-outlined ${iconColor} text-[16px] shrink-0">${iconName}</span>
                <div class="min-w-0">
                  <div class="text-xs font-bold text-on-surface">${c.name}</div>
                  <div class="text-[10px] font-mono text-on-surface-variant truncate">${c.detail || ""}</div>
                </div>
              </div>
              <span class="px-2 py-0.5 rounded ${badgeCls} font-mono text-[10px] font-bold border shrink-0">${c.status}</span>
            </div>
          `;
        }).join("");

        const autoInstallBtn = document.getElementById("btn-diag-auto-install");
        if (autoInstallBtn) autoInstallBtn.addEventListener("click", triggerInstallMissingLibs);
      }

      await fetchSystemLogs();
    } catch (e) {
      if (box && !silentOnStartup) {
        box.style.display = "block";
        box.innerHTML = `<div class="text-error text-xs">❌ Không kết nối được tới Server để kiểm tra lỗi: ${e.message}</div>`;
      }
    } finally {
      if (btn && !silentOnStartup) {
        btn.disabled = false;
        btn.innerHTML = origBtnHtml || `<span class="material-symbols-outlined text-[16px]">fact_check</span>Kiểm Tra Hệ Thống &amp; Thư Viện`;
      }
    }
  }

  function setupSystemLogsAndDiagnostics() {
    const diagBtn = document.getElementById("btn-run-diagnostics");
    if (diagBtn) {
      diagBtn.addEventListener("click", () => runSystemDiagnosticsUI(false));
    }

    const installLibsBtn = document.getElementById("btn-install-missing-libs");
    if (installLibsBtn) {
      installLibsBtn.addEventListener("click", triggerInstallMissingLibs);
    }

    const openLogsBtn = document.getElementById("btn-open-logs-folder");
    if (openLogsBtn) {
      openLogsBtn.addEventListener("click", async () => {
        const dirPath = (latestLogPathsCache && latestLogPathsCache.logs_dir) ? latestLogPathsCache.logs_dir : "logs";
        await openSystemFolder(dirPath);
      });
    }

    const copyLogsBtn = document.getElementById("btn-copy-logs");
    if (copyLogsBtn) {
      copyLogsBtn.addEventListener("click", () => {
        const text = latestLogEntriesCache
          .map((e) => `[${e.timestamp}] [${e.level}/${e.category}]${e.project_id ? " [" + e.project_id + "]" : ""} ${e.message}`)
          .join("\n");
        navigator.clipboard.writeText(text || "Không có log");
        const orig = copyLogsBtn.innerHTML;
        copyLogsBtn.innerHTML = `<span class="material-symbols-outlined text-[14px]">check</span>Đã Copy!`;
        setTimeout(() => { copyLogsBtn.innerHTML = orig; }, 1800);
      });
    }

    const clearLogsBtn = document.getElementById("btn-clear-logs");
    if (clearLogsBtn) {
      clearLogsBtn.addEventListener("click", async () => {
        await fetch("/api/logs/clear", { method: "POST" });
        await fetchSystemLogs();
      });
    }

    // Auto-scroll toggle button in Terminal Header
    const autoScrollBtn = document.getElementById("btn-quick-autoscroll");
    const autoScrollLbl = document.getElementById("lbl-autoscroll-state");
    if (autoScrollBtn) {
      autoScrollBtn.addEventListener("click", () => {
        isTerminalAutoScroll = !isTerminalAutoScroll;
        if (autoScrollLbl) autoScrollLbl.innerText = isTerminalAutoScroll ? "ON" : "OFF";
        autoScrollBtn.style.opacity = isTerminalAutoScroll ? "1" : "0.55";
      });
    }

    // Terminal Quick Command Injection Bar
    const termInput = document.getElementById("terminal-quick-input");
    const termExecBtn = document.getElementById("btn-terminal-exec");

    async function runTerminalQuickCommand() {
      if (!termInput) return;
      const cmd = termInput.value.trim() || "status";
      termInput.value = "";
      if (termExecBtn) termExecBtn.disabled = true;
      try {
        const res = await fetch("/api/diagnostics/exec-cmd", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: cmd })
        });
        const data = await res.json().catch(() => ({}));
        if (data && data.output) {
          await fetchSystemLogs();
        }
      } catch (e) {
        appendInstantLogToUI(`Lỗi thực thi lệnh '${cmd}': ${e.message}`, "SYSTEM", "ERROR");
      } finally {
        if (termExecBtn) termExecBtn.disabled = false;
      }
    }

    if (termExecBtn) {
      termExecBtn.addEventListener("click", runTerminalQuickCommand);
    }
    if (termInput) {
      termInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          runTerminalQuickCommand();
        }
      });
    }

    document.querySelectorAll(".log-filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".log-filter-btn").forEach((b) => {
          b.className = "log-filter-btn px-3 py-1 rounded bg-surface-container hover:bg-surface-container-high text-on-surface-variant font-label-sm text-label-sm transition-all";
        });
        btn.className = "log-filter-btn active px-3 py-1 rounded bg-primary-container text-on-primary-container font-label-sm text-label-sm font-bold shadow-[0_0_8px_rgba(0,255,135,0.3)] transition-all";
        const f = btn.dataset.filter !== undefined ? btn.dataset.filter : "";
        if (f === "ERROR") {
          currentLogLevelFilter = "ERROR";
          currentLogCatFilter = "ALL";
        } else if (f === "ADAS") {
          currentLogLevelFilter = "ALL";
          currentLogCatFilter = "SCRIPT";
        } else if (f === "RENDER" || f === "VOICE") {
          currentLogLevelFilter = "ALL";
          currentLogCatFilter = "VIDEO";
        } else {
          currentLogLevelFilter = btn.dataset.level || "ALL";
          currentLogCatFilter = btn.dataset.cat || "ALL";
        }
        fetchSystemLogs();
      });
    });

    fetchSystemLogs();
    setInterval(fetchSystemLogs, 2500);
    setTimeout(() => runSystemDiagnosticsUI(true), 1500);
  }

  let voicePresetsCache = [];

  async function setupVoiceSelectorAndTuning() {
    const mainSel = document.getElementById("voice-preset-select");
    const adasSel = document.getElementById("adas-voice-select");
    const badgeEl = document.getElementById("voice-engine-badge");
    const descEl = document.getElementById("voice-preset-desc") || document.getElementById("voice-desc-hint");
    const slidersBox = document.getElementById("voice-tuning-sliders");

    const speedRange = document.getElementById("voice-speed-range");
    const pitchRange = document.getElementById("voice-pitch-range");
    const intoRange = document.getElementById("voice-intonation-range");
    const pauseRange = document.getElementById("voice-pause-range");

    const speedVal = document.getElementById("voice-speed-val") || document.getElementById("lbl-voice-speed");
    const pitchVal = document.getElementById("voice-pitch-val") || document.getElementById("lbl-voice-pitch");
    const intoVal = document.getElementById("voice-intonation-val") || document.getElementById("lbl-voice-intonation");
    const pauseVal = document.getElementById("voice-pause-val") || document.getElementById("lbl-voice-pause");

    const previewBtn = document.getElementById("btn-preview-voice");
    const resetDramaBtn = document.getElementById("btn-reset-drama-voice");
    const audioPlayer = document.getElementById("voice-preview-player");
    const srvBtn1 = document.getElementById("btn-gpu-server-1");
    const srvBtn2 = document.getElementById("btn-gpu-server-2");
    const balancerBadge = document.getElementById("gpu-balancer-badge");

    // Mini Preview Player Bar elements
    const btnMiniPlay = document.getElementById("btn-mini-voice-play");
    const miniPlayIcon = document.getElementById("mini-voice-play-icon");
    const miniProgressFill = document.getElementById("voice-mini-progress-fill");
    const miniTimeCur = document.getElementById("voice-mini-time-cur");
    const miniTimeDur = document.getElementById("voice-mini-time-dur");

    function formatShortAudioTime(sec) {
      const s = Math.max(0, Math.floor(sec || 0));
      const mm = String(Math.floor(s / 60)).padStart(2, "0");
      const ss = String(s % 60).padStart(2, "0");
      return `${mm}:${ss}`;
    }

    if (audioPlayer) {
      audioPlayer.addEventListener("loadedmetadata", () => {
        if (miniTimeDur && isFinite(audioPlayer.duration)) {
          miniTimeDur.innerText = formatShortAudioTime(audioPlayer.duration);
        }
      });
      audioPlayer.addEventListener("timeupdate", () => {
        const dur = audioPlayer.duration || 1;
        const cur = audioPlayer.currentTime || 0;
        const pct = Math.max(0, Math.min(100, (cur / dur) * 100));
        if (miniProgressFill) miniProgressFill.style.width = `${pct}%`;
        if (miniTimeCur) miniTimeCur.innerText = formatShortAudioTime(cur);
      });
      audioPlayer.addEventListener("play", () => {
        if (miniPlayIcon) miniPlayIcon.innerText = "pause";
      });
      audioPlayer.addEventListener("pause", () => {
        if (miniPlayIcon) miniPlayIcon.innerText = "play_arrow";
      });
      audioPlayer.addEventListener("ended", () => {
        if (miniPlayIcon) miniPlayIcon.innerText = "play_arrow";
        if (miniProgressFill) miniProgressFill.style.width = "100%";
      });
    }

    if (btnMiniPlay) {
      btnMiniPlay.addEventListener("click", () => {
        if (audioPlayer && audioPlayer.src) {
          if (audioPlayer.paused) {
            audioPlayer.play().catch(() => {});
          } else {
            audioPlayer.pause();
          }
        } else if (previewBtn) {
          previewBtn.click();
        }
      });
    }

    function applyServerButtonsUI(serverMode, statusData) {
      activeGpuServerMode = serverMode || "voicevox_gpu";
      const isOmni = activeGpuServerMode === "omnivoice_gpu";
      const hw = (statusData && statusData.hardware_load) ? statusData.hardware_load : null;

      if (srvBtn1) {
        if (!isOmni) {
          srvBtn1.className = "gpu-server-btn active group relative p-3.5 rounded-xl bg-primary-container/10 border-2 border-primary-container text-left transition-all shadow-[0_0_20px_rgba(0,230,118,0.12)]";
        } else {
          srvBtn1.className = "gpu-server-btn group relative p-3.5 rounded-xl bg-surface-container-low hover:bg-surface-container border border-outline-variant/30 hover:border-primary-container/50 text-left transition-all";
        }
      }
      if (srvBtn2) {
        if (isOmni) {
          srvBtn2.className = "gpu-server-btn active group relative p-3.5 rounded-xl bg-secondary-container/10 border-2 border-secondary-container text-left transition-all shadow-[0_0_20px_rgba(0,210,255,0.12)]";
        } else {
          srvBtn2.className = "gpu-server-btn group relative p-3.5 rounded-xl bg-surface-container-low hover:bg-surface-container border border-outline-variant/30 hover:border-secondary-container/50 text-left transition-all";
        }
      }
      if (balancerBadge && hw) {
        balancerBadge.innerText = `TỰ CÂN ĐỐI 90%: GPU ${Math.round(hw.gpu_percent || 0)}% • CPU ${Math.round(hw.cpu_percent || 0)}%`;
      }
    }

    function shortVoiceOptionLabel(nameStr) {
      const s = String(nameStr || "").replace(/\s*\(VoiceStudio Clone\)\s*/gi, "").trim();
      return s.length > 34 ? s.slice(0, 24) + "..." + s.slice(-8) : s;
    }

    function applyConfigToUI(cfg, presets, statusData = null) {
      if (!cfg) return;
      const presetId = cfg.selected_preset_id || "04_mx_ong_gia_padre_implacable";
      if (mainSel && mainSel.value !== presetId) mainSel.value = presetId;
      if (adasSel && adasSel.value !== presetId) adasSel.value = presetId;

      const presetObj = (presets || voicePresetsCache).find((p) => p.id === presetId) || null;
      if (descEl && presetObj && presetObj.description) {
        descEl.innerText = presetObj.description;
      }

      applyServerButtonsUI("omnivoice_gpu", statusData);

      if (badgeEl) {
        badgeEl.innerHTML = `🟢 VoiceStudio Clone (Kho_Voice)`;
      }
      if (slidersBox) {
        slidersBox.style.opacity = "1";
        slidersBox.style.pointerEvents = "auto";
      }

      const sp = Number(cfg.speedScale ?? 1.00).toFixed(2);
      const vol = Number(cfg.volumeScale ?? 1.00).toFixed(2);
      const it = Number(cfg.intonationScale ?? 0.95).toFixed(2);
      const pa = Number(cfg.pauseLengthScale ?? 1.12).toFixed(2);

      if (speedRange) speedRange.value = sp;
      if (pitchRange) pitchRange.value = vol;
      if (intoRange) intoRange.value = it;
      if (pauseRange) pauseRange.value = pa;

      if (speedVal) speedVal.innerText = `${sp}x`;
      if (pitchVal) pitchVal.innerText = `${Math.round(Number(vol) * 100)}%`;
      if (intoVal) intoVal.innerText = it;
      if (pauseVal) pauseVal.innerText = `${pa}x`;
    }

    async function saveVoiceSettings(payload) {
      try {
        const res = await fetch("/api/voice-engine/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (data && data.config) {
          applyConfigToUI(data.config, voicePresetsCache, data.status || null);
        }
      } catch (e) {}
    }

    async function switchGpuVoiceServer(targetServerMode) {
      const targetBtn = targetServerMode === "omnivoice_gpu" ? srvBtn2 : srvBtn1;
      if (targetBtn) {
        targetBtn.disabled = true;
      }
      try {
        const res = await fetch("/api/voice-engine/switch-server", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active_gpu_server: "omnivoice_gpu", activate_server_now: true })
        });
        const data = await res.json();
        if (data && data.config) {
          applyConfigToUI(data.config, voicePresetsCache, data.status || null);
          appendInstantLogToUI(
            "🟢 Đã kích hoạt VoiceStudio Clone (Kho_Voice)!",
            "VOICE",
            "INFO"
          );
        }
      } catch (e) {
        alert("Lỗi chuyển đổi VoiceStudio: " + e.message);
      } finally {
        if (targetBtn) targetBtn.disabled = false;
      }
    }

    if (srvBtn1) {
      srvBtn1.addEventListener("click", () => switchGpuVoiceServer("omnivoice_gpu"));
    }
    if (srvBtn2) {
      srvBtn2.addEventListener("click", () => switchGpuVoiceServer("omnivoice_gpu"));
    }

    try {
      const res = await fetch("/api/voice-engine/status");
      const data = await res.json();
      voicePresetsCache = data.presets || [];
      if (voicePresetsCache.length > 0) {
        if (mainSel) {
          mainSel.innerHTML = voicePresetsCache
            .map((p) => `<option value="${p.id}" title="${p.name}">🎙️ ${shortVoiceOptionLabel(p.name)}</option>`)
            .join("");
        }
        if (adasSel) {
          adasSel.innerHTML = voicePresetsCache
            .map((p) => `<option value="${p.id}" title="${p.name}">🎙️ ${shortVoiceOptionLabel(p.name)}</option>`)
            .join("");
        }
      }
      applyConfigToUI(data.config, voicePresetsCache, data);
    } catch (e) {}

    async function onPresetSelectChange(selectedId) {
      const preset = voicePresetsCache.find((p) => p.id === selectedId);
      if (!preset) return;
      await saveVoiceSettings({
        active_gpu_server: "omnivoice_gpu",
        selected_preset_id: preset.id,
        engine_mode: "voicestudio_clone",
        speaker_id: preset.speaker_id,
        speedScale: preset.speedScale,
        pitchScale: preset.pitchScale,
        intonationScale: preset.intonationScale,
        pauseLengthScale: preset.pauseLengthScale,
        volumeScale: preset.volumeScale ?? 1.0,
        ref_wav: preset.ref_wav,
        activate_server_now: true
      });
    }

    if (mainSel) {
      mainSel.addEventListener("change", () => onPresetSelectChange(mainSel.value));
    }
    if (adasSel) {
      adasSel.addEventListener("change", () => onPresetSelectChange(adasSel.value));
    }

    function bindSlider(rangeEl, valEl, formatFn, fieldKey) {
      if (!rangeEl) return;
      rangeEl.addEventListener("input", () => {
        if (valEl) valEl.innerText = formatFn(rangeEl.value);
      });
      rangeEl.addEventListener("change", async () => {
        const payload = {};
        payload[fieldKey] = parseFloat(rangeEl.value);
        await saveVoiceSettings(payload);
      });
    }

    bindSlider(speedRange, speedVal, (v) => `${Number(v).toFixed(2)}x`, "speedScale");
    bindSlider(pitchRange, pitchVal, (v) => `${Math.round(Number(v) * 100)}%`, "volumeScale");
    bindSlider(intoRange, intoVal, (v) => Number(v).toFixed(2), "intonationScale");
    bindSlider(pauseRange, pauseVal, (v) => `${Number(v).toFixed(2)}x`, "pauseLengthScale");

    if (resetDramaBtn) {
      resetDramaBtn.addEventListener("click", async () => {
        await onPresetSelectChange("Drama");
      });
    }

    if (previewBtn) {
      previewBtn.addEventListener("click", async () => {
        const origHtml = previewBtn.innerHTML;
        previewBtn.disabled = true;
        previewBtn.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>Đang tạo âm thanh...`;
        try {
          const res = await fetch("/api/voice-engine/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              selected_preset_id: mainSel ? mainSel.value : "Drama",
              speedScale: speedRange ? parseFloat(speedRange.value) : 0.94,
              pitchScale: pitchRange ? parseFloat(pitchRange.value) : -0.02,
              intonationScale: intoRange ? parseFloat(intoRange.value) : 0.95,
              pauseLengthScale: pauseRange ? parseFloat(pauseRange.value) : 1.12,
            }),
          });
          const data = await res.json();
          if (!res.ok) {
            alert(data.detail || "Không thể tạo âm thanh nghe thử!");
            return;
          }
          if (audioPlayer && data.audio_url) {
            audioPlayer.src = data.audio_url;
            audioPlayer.play().catch(() => {});
          }
        } catch (e) {
          alert("Lỗi nghe thử giọng: " + e.message);
        } finally {
          previewBtn.disabled = false;
          previewBtn.innerHTML = origHtml;
        }
      });
    }
  }

  function setupWindowCloseAutoShutdown() {
    // Báo ngay khi cửa sổ mở (hoặc F5 tải lại) để hủy lệnh tắt nếu người dùng chỉ bấm F5
    fetch("/api/app/heartbeat-alive", { method: "POST" }).catch(() => {});

    let closeSent = false;
    const sendCloseSignal = () => {
      if (closeSent || window.__isRestartingForUpdate) return;
      closeSent = true;
      try {
        if (navigator.sendBeacon) {
          navigator.sendBeacon("/api/app/window-closed", new Blob(["{}"], { type: "application/json" }));
        } else {
          fetch("/api/app/window-closed", { method: "POST", keepalive: true }).catch(() => {});
        }
      } catch (e) {}
    };

    window.addEventListener("pagehide", sendCloseSignal);
    window.addEventListener("beforeunload", sendCloseSignal);
  }

  function setupGithubOtaAutoUpdater() {
    const verBadge = document.getElementById("app-version-badge");
    const btnCheck = document.getElementById("btn-check-update-header");
    const iconCheck = document.getElementById("icon-check-update-header");
    const textCheck = document.getElementById("text-check-update-header");
    const btnApplyHeader = document.getElementById("btn-apply-update-header");
    const textApplyHeader = document.getElementById("btn-apply-update-header-text");

    const btnCheckNav = document.getElementById("btn-check-update-nav");
    const iconCheckNav = document.getElementById("icon-check-update-nav");
    const textCheckNav = document.getElementById("text-check-update-nav");
    const btnApplyNav = document.getElementById("btn-apply-update-nav");
    const textApplyNav = document.getElementById("btn-apply-update-nav-text");

    const bannerEl = document.getElementById("ota-update-banner");
    const bannerVerTag = document.getElementById("ota-banner-ver-tag");
    const bannerMsg = document.getElementById("ota-banner-msg");
    const btnBannerApply = document.getElementById("btn-ota-banner-apply");
    const textBannerApply = document.getElementById("btn-ota-banner-apply-text");
    const btnBannerDismiss = document.getElementById("btn-ota-banner-dismiss");

    let dismissedVersion = sessionStorage.getItem("dismissed_ota_version") || "";
    let latestUpdateInfo = null;
    let isApplyingUpdate = false;

    const renderUpdateUI = (info, isManualCheck = false) => {
      if (!info) return;
      latestUpdateInfo = info;
      const curVer = info.current_version || "V1.0.0";
      const newVer = info.latest_version || curVer;
      const hasUpdate = !!info.update_available;

      if (verBadge) verBadge.innerText = curVer;
      if (textCheck) {
        textCheck.innerText = hasUpdate ? `Có bản mới: ${newVer}` : `Cập nhật: ${curVer}`;
      }
      if (textCheckNav) {
        textCheckNav.innerText = hasUpdate ? `🔥 CÓ BẢN MỚI: ${newVer}` : `🔄 CẬP NHẬT (${curVer})`;
      }

      if (hasUpdate) {
        if (btnApplyHeader) {
          btnApplyHeader.classList.remove("hidden");
          btnApplyHeader.classList.add("flex");
        }
        if (textApplyHeader) {
          textApplyHeader.innerText = `🚀 Cập nhật ${newVer}`;
        }
        if (btnApplyNav) {
          btnApplyNav.classList.remove("hidden");
          btnApplyNav.classList.add("flex");
        }
        if (textApplyNav) {
          textApplyNav.innerText = `🚀 CẬP NHẬT ${newVer}`;
        }
        if (bannerVerTag) {
          bannerVerTag.innerText = `MỚI: ${newVer}`;
        }
        if (bannerMsg) {
          const note = info.changelog ? ` — ${info.changelog}` : "";
          bannerMsg.innerText = `🎉 Đã có bản cập nhật ${newVer} trên GitHub (Bản hiện tại: ${curVer})${note}`;
          bannerMsg.title = info.changelog || "";
        }
        if (bannerEl && (isManualCheck || dismissedVersion !== `${newVer}_${info.latest_build || ""}`)) {
          bannerEl.classList.remove("hidden");
          bannerEl.classList.add("flex");
        }
        if (isManualCheck) {
          executeApplyUpdate();
        }
      } else {
        if (btnApplyHeader) {
          btnApplyHeader.classList.add("hidden");
          btnApplyHeader.classList.remove("flex");
        }
        if (btnApplyNav) {
          btnApplyNav.classList.add("hidden");
          btnApplyNav.classList.remove("flex");
        }
        if (bannerEl) {
          bannerEl.classList.add("hidden");
          bannerEl.classList.remove("flex");
        }
        if (isManualCheck) {
          if (info.success === false && info.error) {
            alert(`⚠️ Không thể kiểm tra cập nhật lúc này:\n${info.error}`);
          } else if (confirm(`✅ Máy của bạn đang ở phiên bản ${curVer} (Build #${info.current_build || 104}).\n\nBạn có muốn tải và đồng bộ lại mã nguồn mới nhất của bản ${newVer} từ GitHub ngay bây giờ không?`)) {
            executeApplyUpdate();
          }
        }
      }
    };

    const checkUpdateNow = async (forceRefresh = false, isManual = false) => {
      if (isApplyingUpdate) return;
      if (isManual) {
        if (iconCheck) iconCheck.classList.add("animate-spin");
        if (iconCheckNav) iconCheckNav.classList.add("animate-spin");
      }
      try {
        const res = await fetch(`/api/update/check?force=${forceRefresh ? "true" : "false"}`);
        if (res.ok) {
          const data = await res.json();
          renderUpdateUI(data, isManual);
        } else {
          // Dự phòng trực tiếp tới GitHub nếu tiến trình server cũ chưa khởi động lại
          const ghRes = await fetch(`https://raw.githubusercontent.com/phamngocthu661-lang/mexico-ong-gia-studio/main/version.json?t=${Date.now()}`);
          if (ghRes.ok) {
            const ghData = await ghRes.json();
            const curVer = (verBadge && verBadge.innerText.trim()) || "V1.0.0";
            const latestVer = ghData.version || "V1.0.0";
            const latestBuild = Number(ghData.build_number || 100);
            renderUpdateUI({
              success: true,
              update_available: latestVer !== curVer,
              current_version: curVer,
              latest_version: latestVer,
              changelog: ghData.changelog || ""
            }, isManual);
          }
        }
      } catch (e) {
        if (isManual) {
          alert("Không thể kết nối kiểm tra cập nhật: " + e.message);
        }
      } finally {
        if (isManual) {
          if (iconCheck) iconCheck.classList.remove("animate-spin");
          if (iconCheckNav) iconCheckNav.classList.remove("animate-spin");
        }
      }
    };

    const showFullResetOverlay = (titleText, subText) => {
      let ov = document.getElementById("ota-full-reset-overlay");
      if (!ov) {
        ov = document.createElement("div");
        ov.id = "ota-full-reset-overlay";
        ov.style.cssText = "position:fixed;inset:0;z-index:999999;background:rgba(8,12,16,0.94);backdrop-filter:blur(8px);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px;text-align:center;color:#e2f1e8;font-family:Inter,sans-serif;";
        ov.innerHTML = `
          <div style="max-width:560px;background:#111920;border:2px solid #00e676;border-radius:16px;padding:28px 32px;box-shadow:0 0 40px rgba(0,230,118,0.25);">
            <div style="font-size:38px;margin-bottom:12px;">🔄</div>
            <div id="ota-reset-title" style="font-size:18px;font-weight:800;color:#00e676;margin-bottom:10px;line-height:1.4;"></div>
            <div id="ota-reset-sub" style="font-size:13px;color:#b0c4b8;line-height:1.6;"></div>
          </div>
        `;
        document.body.appendChild(ov);
      }
      const tEl = document.getElementById("ota-reset-title");
      const sEl = document.getElementById("ota-reset-sub");
      if (tEl) tEl.innerText = titleText;
      if (sEl) sEl.innerText = subText;
    };

    const removeFullResetOverlay = () => {
      const ov = document.getElementById("ota-full-reset-overlay");
      if (ov) ov.remove();
    };

    const executeApplyUpdate = async () => {
      if (isApplyingUpdate) return;
      const targetVer = (latestUpdateInfo && latestUpdateInfo.latest_version) || "mới nhất";
      const curVer = (latestUpdateInfo && latestUpdateInfo.current_version) || "V1.0.0";
      const note = (latestUpdateInfo && latestUpdateInfo.changelog)
        ? `\n\n📋 Nội dung nâng cấp:\n${latestUpdateInfo.changelog}`
        : "";

      if (!confirm(`🚀 Bạn có muốn tự động tải bản cập nhật [${targetVer}], đóng toàn bộ tác vụ đang chạy và RESET khởi động lại ứng dụng hoàn toàn không?${note}\n\n(Toàn bộ kịch bản, Checkpoint đang render dở, kho Stock và cấu hình của bạn được giữ nguyên 100%)`)) {
        return;
      }

      isApplyingUpdate = true;
      window.__isRestartingForUpdate = true;
      if (btnBannerApply) btnBannerApply.disabled = true;
      if (btnApplyHeader) btnApplyHeader.disabled = true;
      if (btnApplyNav) btnApplyNav.disabled = true;
      if (textBannerApply) textBannerApply.innerText = "⏳ Đang đóng tác vụ & cập nhật...";
      if (textApplyHeader) textApplyHeader.innerText = "⏳ Đang Reset & cập nhật...";
      if (textApplyNav) textApplyNav.innerText = "⏳ ĐANG RESET & CẬP NHẬT...";

      showFullResetOverlay(
        `Đang đóng toàn bộ tác vụ & tải bản cập nhật ${targetVer}...`,
        "Hệ thống đang dừng sạch các tiến trình FFmpeg, Voice Engine (run.exe), AI và tải mã nguồn mới nhất từ GitHub. Vui lòng đợi trong giây lát..."
      );

      try {
        const res = await fetch("/api/update/apply?restart=true", { method: "POST" });
        let data = null;
        if (res.status === 404) {
          data = { success: true, restarting: false, old_version: curVer, new_version: targetVer };
        } else {
          data = await res.json();
        }
        if ((res.status !== 404 && !res.ok) || !data || !data.success) {
          window.__isRestartingForUpdate = false;
          removeFullResetOverlay();
          alert(`❌ Cập nhật thất bại: ${(data && data.error) || "Lỗi không xác định"}`);
          return;
        }
        const buildTag = data.build_number ? ` (Build #${data.build_number})` : "";
        if (textBannerApply) textBannerApply.innerText = `✅ Đã lên ${data.new_version}!`;
        if (textApplyHeader) textApplyHeader.innerText = `✅ Đã lên ${data.new_version}!`;
        if (textApplyNav) textApplyNav.innerText = `✅ ĐÃ LÊN ${data.new_version}!`;

        showFullResetOverlay(
          `✅ Đã nâng cấp lên ${data.new_version}${buildTag}! Đang Reset khởi động lại ứng dụng...`,
          "Toàn bộ tác vụ cũ đã được đóng sạch. Ứng dụng đang tắt tiến trình cũ và tự động bật lại cửa sổ mới hoàn toàn trong vài giây..."
        );

        // Chờ tiến trình Server cũ tắt hẳn (2.2s), sau đó kiểm tra tới khi Server mới bật lên thì nạp lại trang
        setTimeout(() => {
          let attempts = 0;
          const pollTimer = setInterval(async () => {
            attempts += 1;
            try {
              const ping = await fetch("/api/update/status?_t=" + Date.now(), { cache: "no-store" });
              if (ping.ok) {
                clearInterval(pollTimer);
                window.location.replace("/?v=" + Date.now());
              }
            } catch (err) {
              // Server đang trong quá trình khởi động lại
            }
            if (attempts > 35) {
              clearInterval(pollTimer);
              window.location.replace("/?v=" + Date.now());
            }
          }, 800);
        }, 2200);
      } catch (e) {
        window.__isRestartingForUpdate = false;
        removeFullResetOverlay();
        alert("❌ Lỗi khi tải bản cập nhật: " + e.message);
      } finally {
        isApplyingUpdate = false;
        if (btnBannerApply) btnBannerApply.disabled = false;
        if (btnApplyHeader) btnApplyHeader.disabled = false;
        if (btnApplyNav) btnApplyNav.disabled = false;
      }
    };

    if (btnCheck) {
      btnCheck.addEventListener("click", () => {
        checkUpdateNow(true, true);
      });
    }
    if (btnCheckNav) {
      btnCheckNav.addEventListener("click", () => {
        checkUpdateNow(true, true);
      });
    }
    if (btnApplyHeader) {
      btnApplyHeader.addEventListener("click", executeApplyUpdate);
    }
    if (btnApplyNav) {
      btnApplyNav.addEventListener("click", executeApplyUpdate);
    }
    if (btnBannerApply) {
      btnBannerApply.addEventListener("click", executeApplyUpdate);
    }
    if (btnBannerDismiss) {
      btnBannerDismiss.addEventListener("click", () => {
        if (latestUpdateInfo && latestUpdateInfo.latest_version) {
          dismissedVersion = latestUpdateInfo.latest_version;
          sessionStorage.setItem("dismissed_ota_version", dismissedVersion);
        }
        if (bannerEl) {
          bannerEl.classList.add("hidden");
          bannerEl.classList.remove("flex");
        }
      });
    }

    // Kiểm tra ngay khi mở ứng dụng và tự động kiểm tra định kỳ mỗi 2 phút
    checkUpdateNow(false, false);
    setInterval(() => {
      checkUpdateNow(false, false);
    }, 120000);
  }

  function setupPerformanceModeSelector() {
    let currentPerfMode = localStorage.getItem("studio_perf_mode") || "full_100";

    const applyPerfModeUI = (mode) => {
      const is70 = mode === "work_70";
      currentPerfMode = is70 ? "work_70" : "full_100";
      localStorage.setItem("studio_perf_mode", currentPerfMode);

      document.querySelectorAll(".perf-mode-btn").forEach((btn) => {
        const active = btn.dataset.perfMode === currentPerfMode;
        if (active) {
          btn.className = "perf-mode-btn active whitespace-nowrap flex items-center gap-1 px-2.5 py-1 rounded bg-primary-container text-on-primary-fixed font-label-md text-[11px] font-bold shadow-[0_0_10px_rgba(0,255,135,0.35)] transition-all";
        } else {
          btn.className = "perf-mode-btn whitespace-nowrap flex items-center gap-1 px-2.5 py-1 rounded bg-transparent hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface font-label-md text-[11px] font-semibold transition-all";
        }
      });

      document.querySelectorAll(".perf-mode-card").forEach((card) => {
        const active = card.dataset.perfMode === currentPerfMode;
        const dot = card.querySelector(".perf-dot");
        const titleDiv = card.querySelector("div:first-child");
        if (active) {
          card.className = "perf-mode-card active p-2 rounded-lg bg-primary-container/15 border-2 border-primary-container text-left transition-all";
          if (titleDiv) {
            titleDiv.classList.add("text-primary");
            titleDiv.classList.remove("text-on-surface");
          }
          if (dot) {
            dot.className = "perf-dot w-2 h-2 rounded-full bg-primary-container shadow-[0_0_6px_rgba(0,255,135,0.8)]";
          }
        } else {
          card.className = "perf-mode-card p-2 rounded-lg bg-surface-container-lowest hover:bg-surface-container border border-surface-container-high text-left transition-all";
          if (titleDiv) {
            titleDiv.classList.remove("text-primary");
            titleDiv.classList.add("text-on-surface");
          }
          if (dot) {
            dot.className = "perf-dot w-2 h-2 rounded-full bg-surface-container-highest";
          }
        }
      });

      document.querySelectorAll(".perf-mode-status-label").forEach((lbl) => {
        lbl.innerText = is70
          ? "Đang chọn: 💼 Chạy 70% (Tối đa 3 luồng)"
          : "Đang chọn: 🔥 Chạy Full 100% (Như hiện tại)";
      });

      const balancerBadge = document.getElementById("gpu-balancer-badge");
      if (balancerBadge) {
        balancerBadge.innerText = is70
          ? "💼 Chế độ 70% (Vừa làm việc khác): Giới hạn ~70% GPU & CPU (Tối đa 3 luồng)"
          : "⚡ Chế độ Full 100%: Mục tiêu ~90% GPU & CPU (Tối đa 5 video)";
      }
    };

    const setPerfMode = async (targetMode, notifyUser = true) => {
      const norm = targetMode === "work_70" ? "work_70" : "full_100";
      applyPerfModeUI(norm);
      try {
        await fetch("/api/performance-mode", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode: norm }),
        });
      } catch (e) {}
      if (notifyUser) {
        appendInstantLogToUI(
          norm === "work_70"
            ? "💼 Đã bật Chức năng 2: Chạy 70% Công Suất (Khóa cứng tối đa 3 luồng • Giới hạn 70% CPU/GPU • 1 tab AI/Acc) — Vừa chạy vừa làm việc khác mượt mà!"
            : "🔥 Đã bật Chức năng 1: Chạy Full 100% Công Suất như hiện tại (Ngưỡng 90% CPU/GPU • Tối đa 5 video • 3 tab AI/Acc)!",
          "SYSTEM",
          "INFO"
        );
      }
    };

    document.querySelectorAll(".perf-mode-btn, .perf-mode-card").forEach((el) => {
      el.addEventListener("click", () => {
        const m = el.dataset.perfMode || "full_100";
        setPerfMode(m, true);
      });
    });

    // Đồng bộ trạng thái ban đầu giữa Giao diện và Server
    const explicitLocalMode = localStorage.getItem("studio_perf_mode");
    applyPerfModeUI(currentPerfMode);
    if (explicitLocalMode === "work_70" || explicitLocalMode === "full_100") {
      setPerfMode(explicitLocalMode, false);
    } else {
      fetch("/api/performance-mode")
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (d && d.mode) {
            applyPerfModeUI(d.mode);
          }
        })
        .catch(() => {});
    }
  }

  function setupSkill04InteractivePreview() {
    const previewContainer = document.getElementById("preview-container");
    const greenStage = document.getElementById("preview-green-layers-stage");
    const scriptCharBox = document.getElementById("preview-script-char-box");
    const karaokeSubBox = document.getElementById("preview-karaoke-sub-box");
    const karaokeWordsEl = document.getElementById("preview-karaoke-words");
    const karaokePosTag = document.getElementById("preview-karaoke-pos-tag");
    const badgeSubFontsizeTop = document.getElementById("badge-sub-fontsize-top");

    const greenLibSelect = document.getElementById("green-lib-select");
    const greenLibSelectTop = document.getElementById("green-lib-select-top");
    const addGreenBtn = document.getElementById("btn-add-green-layer");
    const addGreenBtnTop = document.getElementById("btn-add-green-layer-top");
    const importGreenBtn = document.getElementById("btn-import-green-file");
    const pickGreenToPreviewBtn = document.getElementById("btn-pick-green-to-preview");
    const greenFileUploadInput = document.getElementById("green-file-upload-input");
    const openGreenFolderBtn = document.getElementById("btn-open-green-icons-folder");
    const stackListEl = document.getElementById("green-layers-stack-list");
    const countLabelEl = document.getElementById("green-layers-count-label");
    const saveLayoutBtn = document.getElementById("btn-save-video-layout");
    const saveLayoutBtnTop = document.getElementById("btn-save-video-layout-top");
    const saveMsgEl = document.getElementById("video-layout-save-msg");

    // Điều khiển cỡ chữ Phụ đề Karaoke (Font Size px)
    const karaokeFontsizeRange = document.getElementById("karaoke-fontsize-range");
    const karaokeFontsizeInput = document.getElementById("karaoke-fontsize-input");
    const btnSubFontDec = document.getElementById("btn-sub-font-dec");
    const btnSubFontInc = document.getElementById("btn-sub-font-inc");
    const karaokeMaxwordsInput = document.getElementById("karaoke-maxwords-input");
    const layerPropFontsizeRange = document.getElementById("layer-prop-fontsize-range");
    const layerPropFontsizeVal = document.getElementById("layer-prop-fontsize-val");

    const propX = document.getElementById("layer-prop-x");
    const propY = document.getElementById("layer-prop-y");
    const propW = document.getElementById("layer-prop-w");
    const propH = document.getElementById("layer-prop-h");
    const propOpacity = document.getElementById("layer-prop-opacity");
    const propOpacityVal = document.getElementById("layer-prop-opacity-val");
    const stockDarkenRange = document.getElementById("stock-darken-range");
    const stockDarkenVal = document.getElementById("stock-darken-val");
    const stockDarkenOverlay = document.getElementById("preview-stock-darken-overlay");
    const selectedTitleEl = document.getElementById("selected-layer-title");
    const selectedZBadgeEl = document.getElementById("selected-layer-z-badge");

    // Nút nạp giọng mẫu mới vào VoiceStudio (Kho_Voice) bằng hộp thoại trình duyệt trực tiếp
    const importVoiceBtn = document.getElementById("btn-import-voice-sample");
    const voiceSampleUploadInput = document.getElementById("voice-sample-upload-input");
    if (importVoiceBtn && voiceSampleUploadInput) {
      importVoiceBtn.addEventListener("click", () => {
        voiceSampleUploadInput.value = "";
        voiceSampleUploadInput.click();
      });
      voiceSampleUploadInput.addEventListener("change", async (ev) => {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;
        const origHtml = importVoiceBtn.innerHTML;
        importVoiceBtn.disabled = true;
        importVoiceBtn.innerText = "⏳ Đang nạp...";
        try {
          const res = await fetch("/api/voice-engine/upload-sample", {
            method: "POST",
            headers: {
              "Content-Type": "application/octet-stream",
              "X-File-Name": encodeURIComponent(file.name),
            },
            body: file,
          });
          const data = await res.json();
          if (res.ok && data.success) {
            appendInstantLogToUI(`🎙️ Đã nạp mẫu giọng Clone mới vào Kho_Voice: ${data.selected_preset_id}`, "VOICE", "INFO");
            const voiceSel = document.getElementById("voice-preset-select");
            if (voiceSel && data.status && Array.isArray(data.status.presets)) {
              voiceSel.innerHTML = data.status.presets
                .map((p) => `<option value="${p.id}" ${p.id === data.selected_preset_id ? "selected" : ""}>🎙️ ${p.name}</option>`)
                .join("");
            }
          }
        } catch (err) {
          console.error(err);
        } finally {
          importVoiceBtn.disabled = false;
          importVoiceBtn.innerHTML = origHtml;
        }
      });
    }

    const openKhoVoiceBtn = document.getElementById("btn-open-kho-voice-dir");
    if (openKhoVoiceBtn) {
      openKhoVoiceBtn.addEventListener("click", () => openSystemFolder("Kho_Voice"));
    }

    if (openGreenFolderBtn) {
      openGreenFolderBtn.addEventListener("click", () => openSystemFolder("Kho_Green"));
    }

    // Trạng thái bố cục chuẩn 1920x1080 (đồng bộ 100% giữa Frontend và Backend)
    let layoutState = {
      canvas_width: 1920,
      canvas_height: 1080,
      stock_darken: { brightness: -0.12, contrast: 1.05, saturation: 0.92 },
      subtitle_karaoke: { enabled: true, x: 70, y: 910, width: 1340, height: 110, fontSize: 52, font_size: 52, maxWordsPerLine: 5, max_words_per_line: 5 },
      script_character_green: { enabled: true, x: 1410, y: 300, width: 490, height: 780, opacity: 0.90, snapBottom: true, locked_bottom: true },
      green_video_layers: [
        { id: "layer_nen_den", name: "NÈN DEN.jpg", file: "NÈN DEN.jpg", enabled: true, x: 0, y: 830, width: 1920, height: 250, opacity: 0.78, zIndex: 10, chromaKey: false, keyColor: "#00FF00" },
        { id: "layer_song_am", name: "SONG6.mp4", file: "SONG6.mp4", enabled: true, x: 55, y: 205, width: 310, height: 125, opacity: 0.95, zIndex: 20, chromaKey: true, keyColor: "#00FF00" },
        { id: "layer_nut_sub", name: "SUB.mp4", file: "SUB.mp4", enabled: true, x: 45, y: 45, width: 330, height: 145, opacity: 1.0, zIndex: 30, chromaKey: true, keyColor: "#00FF00" },
      ],
    };

    function normalizeIncomingLayout(raw) {
      if (!raw || typeof raw !== "object") return;
      const gLayers = Array.isArray(raw.green_video_layers)
        ? raw.green_video_layers
        : Array.isArray(raw.green_layers)
        ? raw.green_layers
        : layoutState.green_video_layers;
      const sChar = raw.script_character_green || raw.script_green_character || layoutState.script_character_green || {};
      const sSub = raw.subtitle_karaoke || raw.karaoke_subtitle || layoutState.subtitle_karaoke || {};
      const sBg = raw.stock_darken || raw.stock_background || layoutState.stock_darken || {};

      const fs = Math.max(20, Math.min(110, Math.round(Number(sSub.fontSize ?? sSub.font_size ?? 52))));
      const mw = Math.max(2, Math.min(12, Math.round(Number(sSub.maxWordsPerLine ?? sSub.max_words_per_line ?? 5))));
      const subW = Math.max(260, Math.min(1880, Math.round(Number(sSub.width ?? 1340))));
      const subH = Math.max(60, Math.min(380, Math.round(Number(sSub.height ?? 110))));
      const subX = Math.max(0, Math.min(1920 - subW, Math.round(Number(sSub.x ?? (sSub.centerX ? sSub.centerX - subW / 2 : 70)))));
      const subY = Math.max(0, Math.min(1080 - subH, Math.round(Number(sSub.y ?? (sSub.centerY ? sSub.centerY - subH / 2 : 910)))));

      const charW = Math.max(120, Math.min(1200, Math.round(Number(sChar.width ?? 490))));
      const charH = Math.max(180, Math.min(1060, Math.round(Number(sChar.height ?? 780))));
      const charX = Math.max(0, Math.min(1920 - charW, Math.round(Number(sChar.x ?? 1410))));
      const charOp = Math.max(0.1, Math.min(1.0, Number(sChar.opacity ?? 0.90)));

      layoutState.green_video_layers = gLayers.map((l, idx) => ({
        ...l,
        id: l.id || `green_layer_${idx + 1}`,
        name: l.name || l.file || `Layer ${idx + 1}`,
        file: l.file || "SUB.mp4",
        enabled: l.enabled !== false,
        x: Math.round(Number(l.x ?? 45)),
        y: Math.round(Number(l.y ?? 45)),
        width: Math.max(40, Math.round(Number(l.width ?? 330))),
        height: Math.max(40, Math.round(Number(l.height ?? 145))),
        opacity: Math.max(0.1, Math.min(1.0, Number(l.opacity ?? 1.0))),
        zIndex: Number(l.zIndex ?? (idx + 1) * 10),
      }));
      layoutState.green_layers = layoutState.green_video_layers;

      layoutState.script_character_green = {
        ...sChar,
        enabled: sChar.enabled !== false,
        x: charX,
        y: 1080 - charH,
        width: charW,
        height: charH,
        opacity: charOp,
        snapBottom: true,
        locked_bottom: true,
      };
      layoutState.script_green_character = layoutState.script_character_green;

      layoutState.subtitle_karaoke = {
        ...sSub,
        enabled: sSub.enabled !== false,
        x: subX,
        y: subY,
        width: subW,
        height: subH,
        centerX: Math.round(subX + subW / 2),
        centerY: Math.round(subY + subH / 2),
        fontSize: fs,
        font_size: fs,
        maxWordsPerLine: mw,
        max_words_per_line: mw,
      };
      layoutState.karaoke_subtitle = layoutState.subtitle_karaoke;

      layoutState.stock_darken = {
        brightness: Number(sBg.brightness ?? -0.12),
        contrast: Number(sBg.contrast ?? 1.05),
        saturation: Number(sBg.saturation ?? 0.92),
        stock_speed: Number(sBg.stock_speed ?? 0.75),
      };
      layoutState.stock_background = layoutState.stock_darken;
    }

    let greenLibraryItems = [];
    // selectedTarget: { type: 'script_char' | 'karaoke_sub' | 'green_layer', id?: string }
    let selectedTarget = { type: "karaoke_sub" };
    const mediaElementsMap = new Map();

    // 1. Hiệu ứng chạy chữ Karaoke (CapCut Word-by-Word Box) ở Lớp #1 Cao Nhất — Đồng bộ 1:1 với .ASS Renderer
    const sampleKaraokeLines = [
      ["CENA", "FAMILIAR", "SIN", "SABER", "NADA"],
      ["VEINTE", "MIL", "EUROS", "EN", "LA"],
      ["MI", "YERNO", "ME", "PIDIÓ", "TODO"],
    ];
    let kLineIdx = 0;
    let kWordIdx = 0;
    setInterval(() => {
      if (!karaokeWordsEl) return;
      const maxW = Math.max(2, Math.min(12, Number(layoutState.subtitle_karaoke?.maxWordsPerLine || 5)));
      const fs = Math.max(20, Math.min(110, Math.round(Number(layoutState.subtitle_karaoke?.fontSize ?? 78))));
      const pWidth = (previewContainer && previewContainer.clientWidth > 100) ? previewContainer.clientWidth : 780;
      const previewScale = pWidth / 1920;
      const padX = Math.max(4, Math.round(fs * 0.145 * previewScale));
      const padY = Math.max(3, Math.round(fs * 0.125 * previewScale));
      const rad = Math.max(4, Math.round(fs * 0.18 * previewScale));
      const fullWords = sampleKaraokeLines[kLineIdx % sampleKaraokeLines.length];
      const words = fullWords.slice(0, maxW);
      karaokeWordsEl.innerHTML = words
        .map((w, idx) => {
          const u = String(w).toUpperCase();
          if (idx === kWordIdx % words.length) {
            return `<span class="inline-flex items-center justify-center bg-[#7C00FF] text-[#FFFF00] shadow-[0_0_10px_rgba(124,0,255,0.65)] leading-none" id="preview-karaoke-active-box" style="padding: ${padY}px ${padX}px; border-radius: ${rad}px;">${u}</span>`;
          }
          return `<span class="inline-flex items-center justify-center leading-none" style="color: #FFFF00;">${u}</span>`;
        })
        .join("");
      kWordIdx++;
      if (kWordIdx >= words.length) {
        kWordIdx = 0;
        kLineIdx = (kLineIdx + 1) % sampleKaraokeLines.length;
      }
    }, 420);

    // 2. Hàm Chroma Key thời gian thực trên Canvas cho các lớp Video/Ảnh Green trong Kho_Green
    function drawChromaKeyFrame(sourceEl, canvas, ctx, useChromaKey = true) {
      if (!canvas || !ctx || !sourceEl) return;
      const cw = canvas.width || 320;
      const ch = canvas.height || 180;
      try {
        ctx.clearRect(0, 0, cw, ch);
        ctx.drawImage(sourceEl, 0, 0, cw, ch);
        if (!useChromaKey) return;
        const frame = ctx.getImageData(0, 0, cw, ch);
        const data = frame.data;
        for (let i = 0; i < data.length; i += 4) {
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];
          if (g > 95 && g > r * 1.28 && g > b * 1.28) {
            const excess = g - Math.max(r, b);
            if (excess > 50) {
              data[i + 3] = 0;
            } else {
              data[i + 3] = Math.max(0, Math.min(255, Math.round((1 - excess / 50) * 255)));
              data[i + 1] = Math.min(g, Math.round((r + b) * 0.6));
            }
          }
        }
        ctx.putImageData(frame, 0, 0);
      } catch (e) {}
    }

    function renderGreenStageDOM() {
      if (!greenStage) return;
      greenStage.innerHTML = "";
      const layersSorted = [...(layoutState.green_video_layers || [])].sort((a, b) => (a.zIndex || 10) - (b.zIndex || 10));

      layersSorted.forEach((layer, idx) => {
        if (layer.enabled === false) return;
        const wrap = document.createElement("div");
        const isSelected = selectedTarget.type === "green_layer" && selectedTarget.id === layer.id;
        wrap.className = `preview-green-item absolute cursor-move select-none ${
          isSelected ? "ring-2 ring-[#00ff87] shadow-[0_0_16px_rgba(0,255,135,0.45)]" : "hover:ring-1 hover:ring-secondary/70"
        }`;
        wrap.dataset.layerId = layer.id;
        wrap.style.zIndex = String(10 + idx);
        wrap.style.left = `${((layer.x || 0) / 1920) * 100}%`;
        wrap.style.top = `${((layer.y || 0) / 1080) * 100}%`;
        wrap.style.width = `${((layer.width || 360) / 1920) * 100}%`;
        wrap.style.height = `${((layer.height || 220) / 1080) * 100}%`;
        wrap.style.opacity = String(layer.opacity !== undefined ? layer.opacity : 1.0);

        const canvas = document.createElement("canvas");
        canvas.width = 320;
        canvas.height = 180;
        canvas.className = "w-full h-full object-fill pointer-events-none";
        wrap.appendChild(canvas);

        // Nhãn tên lớp Green + Z-order
        const badge = document.createElement("div");
        badge.className = "absolute top-1 left-1 px-1.5 py-0.2 rounded bg-black/80 text-[#00ff87] font-mono text-[8.5px] font-bold border border-[#00ff87]/40 pointer-events-none truncate max-w-[92%]";
        badge.textContent = `#3.${layersSorted.length - idx} • ${layer.file} (Op:${Number(layer.opacity ?? 1).toFixed(2)})`;
        wrap.appendChild(badge);

        // 4 góc kéo chỉnh kích thước (Resize Handles)
        ["nw", "ne", "sw", "se"].forEach((dir) => {
          const h = document.createElement("div");
          const posCls =
            dir === "nw" ? "-top-1.5 -left-1.5 cursor-nwse-resize" :
            dir === "ne" ? "-top-1.5 -right-1.5 cursor-nesw-resize" :
            dir === "sw" ? "-bottom-1.5 -left-1.5 cursor-nesw-resize" :
                           "-bottom-1.5 -right-1.5 cursor-nwse-resize";
          h.className = `green-resize-handle absolute ${posCls} w-3.5 h-3.5 bg-[#00ff87] border border-black rounded-sm z-30 ${isSelected ? "block" : "hidden"}`;
          h.dataset.resizeDir = dir;
          h.dataset.layerId = layer.id;
          wrap.appendChild(h);
        });

        wrap.addEventListener("mousedown", (ev) => {
          ev.stopPropagation();
          selectLayer({ type: "green_layer", id: layer.id });
          const rDir = ev.target?.dataset?.resizeDir;
          if (rDir) {
            startDragOrResize(ev, { mode: "resize", dir: rDir, target: { type: "green_layer", id: layer.id } });
          } else {
            startDragOrResize(ev, { mode: "move", target: { type: "green_layer", id: layer.id } });
          }
        });

        greenStage.appendChild(wrap);

        // Khởi tạo hoặc lấy media element để vẽ Chroma Key lên Canvas
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        const ext = (layer.file || "").split(".").pop().toLowerCase();
        const isImg = ["png", "jpg", "jpeg", "webp"].includes(ext);
        const mapKey = `${layer.id}::${layer.file}`;
        let mediaObj = mediaElementsMap.get(mapKey);
        if (!mediaObj) {
          if (isImg) {
            const img = new Image();
            img.crossOrigin = "anonymous";
            img.src = `/kho_green/${encodeURIComponent(layer.file)}`;
            mediaObj = { el: img, isVideo: false };
          } else {
            const vid = document.createElement("video");
            vid.crossOrigin = "anonymous";
            vid.src = `/kho_green/${encodeURIComponent(layer.file)}`;
            vid.loop = true;
            vid.muted = true;
            vid.playsInline = true;
            vid.autoplay = true;
            vid.play().catch(() => {});
            mediaObj = { el: vid, isVideo: true };
          }
          mediaElementsMap.set(mapKey, mediaObj);
        } else if (mediaObj.isVideo) {
          mediaObj.el.play().catch(() => {});
        }
        mediaObj.canvas = canvas;
        mediaObj.ctx = ctx;
        mediaObj.useChromaKey = layer.chromaKey !== undefined ? Boolean(layer.chromaKey) : !isImg;
      });
    }

    // Vòng lặp vẽ Chroma Key trực tiếp trên màn hình Preview (~18 FPS mượt nhẹ)
    setInterval(() => {
      const layers = layoutState.green_video_layers || [];
      layers.forEach((layer) => {
        if (layer.enabled === false) return;
        const mapKey = `${layer.id}::${layer.file}`;
        const m = mediaElementsMap.get(mapKey);
        if (!m || !m.canvas || !m.ctx) return;
        if (m.isVideo && m.el.readyState >= 2) {
          drawChromaKeyFrame(m.el, m.canvas, m.ctx, m.useChromaKey);
        } else if (!m.isVideo && m.el.complete) {
          drawChromaKeyFrame(m.el, m.canvas, m.ctx, m.useChromaKey);
        }
      });
    }, 55);

    // 3. Cập nhật vị trí, kích thước & CỠ CHỮ của Phụ đề Karaoke (Lớp #1) và Ảnh Nhân Vật Kịch Bản (Lớp #2 — Sát đáy)
    function applyScriptCharAndKaraokeDOM() {
      const sc = layoutState.script_character_green || {};
      sc.width = Math.max(120, Math.min(1200, Number(sc.width || 490)));
      sc.height = Math.max(180, Math.min(1060, Number(sc.height || 780)));
      sc.x = Math.max(0, Math.min(1920 - sc.width, Number(sc.x !== undefined ? sc.x : 1410)));
      // Bắt buộc luôn nằm sát đáy dưới cùng (y = 1080 - height)
      sc.y = 1080 - sc.height;
      sc.opacity = Math.max(0.1, Math.min(1.0, Number(sc.opacity !== undefined ? sc.opacity : 0.90)));
      layoutState.script_green_character = sc;

      if (scriptCharBox) {
        scriptCharBox.style.left = `${(sc.x / 1920) * 100}%`;
        scriptCharBox.style.bottom = "0%";
        scriptCharBox.style.top = "auto";
        scriptCharBox.style.width = `${(sc.width / 1920) * 100}%`;
        scriptCharBox.style.height = `${(sc.height / 1080) * 100}%`;
        scriptCharBox.style.opacity = String(sc.opacity);
        const opTag = document.getElementById("preview-script-char-opacity-tag");
        if (opTag) opTag.textContent = `OPACITY ${sc.opacity.toFixed(2)}`;
        const inner = document.getElementById("preview-script-char-inner");
        if (inner) {
          if (selectedTarget.type === "script_char") {
            inner.classList.add("ring-2", "ring-[#00ff87]");
          } else {
            inner.classList.remove("ring-2", "ring-[#00ff87]");
          }
        }
      }

      const ks = layoutState.subtitle_karaoke || {};
      ks.width = Math.max(260, Math.min(1880, Number(ks.width || 1360)));
      ks.height = Math.max(52, Math.min(240, Number(ks.height || 88)));
      ks.x = Math.max(0, Math.min(1920 - ks.width, Number(ks.x !== undefined ? ks.x : 30)));
      ks.y = Math.max(0, Math.min(1080 - ks.height, Number(ks.y !== undefined ? ks.y : 906)));
      const fs = Math.max(20, Math.min(110, Math.round(Number(ks.fontSize ?? ks.font_size ?? 64))));
      const mw = Math.max(2, Math.min(12, Math.round(Number(ks.maxWordsPerLine ?? ks.max_words_per_line ?? 5))));
      ks.fontSize = fs;
      ks.font_size = fs;
      ks.maxWordsPerLine = mw;
      ks.max_words_per_line = mw;
      ks.centerX = Math.round(ks.x + ks.width / 2);
      ks.centerY = Math.round(ks.y + ks.height / 2);
      layoutState.karaoke_subtitle = ks;

      // Tính tỷ lệ khung Preview thực tế theo chuẩn libass (EM = Fontsize * 2048/2288) để chữ & hộp Karaoke trên Preview khớp 1:1 với Video
      const pWidth = (previewContainer && previewContainer.clientWidth > 100) ? previewContainer.clientWidth : 780;
      const previewScale = pWidth / 1920;
      const scaledPx = Math.max(9, Math.round(fs * (2048 / 2288) * previewScale));

      if (karaokeWordsEl) {
        karaokeWordsEl.style.fontSize = `${scaledPx}px`;
      }
      const activeBoxEl = document.getElementById("preview-karaoke-active-box");
      if (activeBoxEl) {
        const padX = Math.max(4, Math.round(fs * 0.12 * previewScale));
        const padY = Math.max(3, Math.round(fs * 0.095 * previewScale));
        const rad = Math.max(4, Math.round(fs * 0.16 * previewScale));
        activeBoxEl.style.padding = `${padY}px ${padX}px`;
        activeBoxEl.style.borderRadius = `${rad}px`;
      }
      if (karaokePosTag) {
        karaokePosTag.textContent = `Cỡ chữ: ${fs}px • Tâm (${ks.centerX}, ${ks.centerY})`;
      }
      if (badgeSubFontsizeTop) {
        badgeSubFontsizeTop.textContent = `${fs}px • Z=100`;
      }
      if (karaokeFontsizeRange) karaokeFontsizeRange.value = String(fs);
      if (karaokeFontsizeInput) karaokeFontsizeInput.value = String(fs);
      if (layerPropFontsizeRange) layerPropFontsizeRange.value = String(fs);
      if (layerPropFontsizeVal) layerPropFontsizeVal.textContent = `${fs} px`;
      if (karaokeMaxwordsInput) karaokeMaxwordsInput.value = String(mw);

      if (karaokeSubBox) {
        karaokeSubBox.style.left = `${(ks.x / 1920) * 100}%`;
        karaokeSubBox.style.top = `${(ks.y / 1080) * 100}%`;
        karaokeSubBox.style.bottom = "auto";
        karaokeSubBox.style.width = `${(ks.width / 1920) * 100}%`;
        karaokeSubBox.style.height = `${(ks.height / 1080) * 100}%`;
        karaokeSubBox.style.minHeight = "0px";
        if (selectedTarget.type === "karaoke_sub") {
          karaokeSubBox.classList.add("ring-2", "ring-amber-400");
        } else {
          karaokeSubBox.classList.remove("ring-2", "ring-amber-400");
        }
      }

      const dark = Math.abs(Number(layoutState.stock_darken?.brightness ?? -0.12));
      if (stockDarkenOverlay) {
        stockDarkenOverlay.style.background = `rgba(0,0,0,${Math.min(0.45, dark).toFixed(2)})`;
      }
      if (stockDarkenRange) stockDarkenRange.value = String(dark.toFixed(2));
      if (stockDarkenVal) stockDarkenVal.textContent = `-${dark.toFixed(2)} (Tối nhẹ)`;
    }

    let _autoSaveTimer = null;
    function scheduleAutoSaveLayout() {
      if (_autoSaveTimer) clearTimeout(_autoSaveTimer);
      _autoSaveTimer = setTimeout(() => {
        layoutState.green_layers = layoutState.green_video_layers;
        layoutState.script_green_character = layoutState.script_character_green;
        layoutState.karaoke_subtitle = layoutState.subtitle_karaoke;
        layoutState.stock_background = layoutState.stock_darken;
        fetch("/api/video-layout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(layoutState),
        }).catch(() => {});
      }, 350);
    }

    // Hàm cập nhật Cỡ chữ Phụ đề Karaoke từ bất kỳ thanh trượt / nút cộng trừ / kéo góc nào (Giữ cố định tâm centerY của khung)
    function setKaraokeFontSize(newSize) {
      const fs = Math.max(20, Math.min(110, Math.round(Number(newSize) || 78)));
      layoutState.subtitle_karaoke = layoutState.subtitle_karaoke || {};
      const oldY = Number(layoutState.subtitle_karaoke.y ?? 898);
      const oldH = Number(layoutState.subtitle_karaoke.height ?? 100);
      const curCenterY = Math.round(oldY + oldH / 2);
      const nextH = Math.max(52, Math.min(200, Math.round(fs * 1.30)));
      layoutState.subtitle_karaoke.fontSize = fs;
      layoutState.subtitle_karaoke.font_size = fs;
      layoutState.subtitle_karaoke.height = nextH;
      layoutState.subtitle_karaoke.y = Math.max(0, Math.min(1080 - nextH, Math.round(curCenterY - nextH / 2)));
      layoutState.karaoke_subtitle = layoutState.subtitle_karaoke;
      applyScriptCharAndKaraokeDOM();
      renderLayerStackList();
      if (selectedTarget.type === "karaoke_sub") {
        syncInspectorInputsFromSelection();
      }
      scheduleAutoSaveLayout();
    }

    if (karaokeFontsizeRange) {
      karaokeFontsizeRange.addEventListener("input", () => setKaraokeFontSize(karaokeFontsizeRange.value));
    }
    if (karaokeFontsizeInput) {
      karaokeFontsizeInput.addEventListener("input", () => setKaraokeFontSize(karaokeFontsizeInput.value));
    }
    if (layerPropFontsizeRange) {
      layerPropFontsizeRange.addEventListener("input", () => setKaraokeFontSize(layerPropFontsizeRange.value));
    }
    if (btnSubFontDec) {
      btnSubFontDec.addEventListener("click", () => {
        const cur = Number(layoutState.subtitle_karaoke?.fontSize || 52);
        setKaraokeFontSize(cur - 2);
      });
    }
    if (btnSubFontInc) {
      btnSubFontInc.addEventListener("click", () => {
        const cur = Number(layoutState.subtitle_karaoke?.fontSize || 52);
        setKaraokeFontSize(cur + 2);
      });
    }
    if (karaokeMaxwordsInput) {
      karaokeMaxwordsInput.addEventListener("input", () => {
        const mw = Math.max(2, Math.min(12, parseInt(karaokeMaxwordsInput.value, 10) || 5));
        layoutState.subtitle_karaoke = layoutState.subtitle_karaoke || {};
        layoutState.subtitle_karaoke.maxWordsPerLine = mw;
        layoutState.subtitle_karaoke.max_words_per_line = mw;
        layoutState.karaoke_subtitle = layoutState.subtitle_karaoke;
        applyScriptCharAndKaraokeDOM();
      });
    }

    if (previewContainer && typeof ResizeObserver !== "undefined") {
      const ro = new ResizeObserver(() => {
        applyScriptCharAndKaraokeDOM();
      });
      ro.observe(previewContainer);
    }

    // 4. Hiển thị danh sách Tách Lớp (Layer Stack) rõ ràng cái nào trên cái nào dưới
    function renderLayerStackList() {
      if (!stackListEl) return;
      const greenLayersDesc = [...(layoutState.green_video_layers || [])].sort((a, b) => (b.zIndex || 10) - (a.zIndex || 10));
      if (countLabelEl) {
        countLabelEl.textContent = `Đang bật ${greenLayersDesc.filter(l => l.enabled !== false).length}/${greenLayersDesc.length} lớp Green`;
      }

      let html = "";
      // Tầng #1 Cao nhất: Sub Karaoke
      const isSubSel = selectedTarget.type === "karaoke_sub";
      const subFs = Number(layoutState.subtitle_karaoke?.fontSize ?? 52);
      html += `
        <div class="layer-stack-row cursor-pointer p-1.5 rounded flex items-center justify-between text-[11px] font-mono border ${
          isSubSel ? "bg-amber-500/20 border-amber-400 text-amber-200" : "bg-surface-container-low border-surface-container-high text-on-surface"
        }" data-select-type="karaoke_sub">
          <div class="flex items-center gap-1.5 truncate">
            <span class="px-1.5 py-0.2 rounded bg-amber-400 text-black font-bold text-[9.5px]">LỚP #1 (TRÊN CÙNG)</span>
            <span class="font-bold truncate">🎤 Phụ Đề Karaoke (Cỡ chữ: ${subFs}px)</span>
          </div>
          <span class="text-[9.5px] text-amber-300 shrink-0">Z=100</span>
        </div>
      `;

      // Tầng #2: Ảnh Green Nhân Vật Theo Kịch Bản (Đáy phải • Opacity 0.9)
      const isCharSel = selectedTarget.type === "script_char";
      const charOp = Number(layoutState.script_character_green?.opacity ?? 0.90).toFixed(2);
      html += `
        <div class="layer-stack-row cursor-pointer p-1.5 rounded flex items-center justify-between text-[11px] font-mono border ${
          isCharSel ? "bg-primary-container/20 border-primary-container text-primary" : "bg-surface-container-low border-surface-container-high text-on-surface"
        }" data-select-type="script_char">
          <div class="flex items-center gap-1.5 truncate">
            <span class="px-1.5 py-0.2 rounded bg-primary-container text-black font-bold text-[9.5px]">LỚP #2</span>
            <span class="font-bold truncate">👴🏽 Ảnh Green Kịch Bản (Đáy phải)</span>
          </div>
          <span class="text-[9.5px] text-primary-container shrink-0">Op:${charOp}</span>
        </div>
      `;

      // Tầng #3.x: Các lớp Video Green trong Kho_Green (từ trên xuống dưới)
      greenLayersDesc.forEach((layer, idx) => {
        const isSel = selectedTarget.type === "green_layer" && selectedTarget.id === layer.id;
        const opStr = Number(layer.opacity ?? 1.0).toFixed(2);
        html += `
          <div class="layer-stack-row cursor-pointer p-1.5 rounded flex items-center justify-between gap-1 text-[11px] font-mono border ${
            isSel ? "bg-secondary/20 border-secondary text-primary" : "bg-surface-container-low border-surface-container-high text-on-surface"
          }" data-select-type="green_layer" data-layer-id="${layer.id}">
            <div class="flex items-center gap-1.5 truncate min-w-0">
              <span class="px-1.5 py-0.2 rounded bg-secondary text-black font-bold text-[9.5px] shrink-0">LỚP #3.${idx + 1}</span>
              <span class="font-bold truncate ${layer.enabled === false ? "line-through opacity-50" : ""}">${layer.file}</span>
              <span class="text-[9.5px] text-secondary shrink-0">(Op:${opStr})</span>
            </div>
            <div class="flex items-center gap-1 shrink-0">
              <button class="btn-layer-up px-1 py-0.2 rounded bg-surface-container-high hover:bg-surface-bright text-[10px]" data-layer-id="${layer.id}" title="Đẩy lớp Green này LÊN TRÊN" type="button">🔼</button>
              <button class="btn-layer-down px-1 py-0.2 rounded bg-surface-container-high hover:bg-surface-bright text-[10px]" data-layer-id="${layer.id}" title="Hạ lớp Green này XUỐNG DƯỚI" type="button">🔽</button>
              <button class="btn-layer-toggle px-1 py-0.2 rounded bg-surface-container-high hover:bg-surface-bright text-[10px]" data-layer-id="${layer.id}" title="Ẩn / Hiện lớp Green này" type="button">${layer.enabled === false ? "🚫" : "👁️"}</button>
              <button class="btn-layer-del px-1 py-0.2 rounded bg-error-container text-on-error text-[10px]" data-layer-id="${layer.id}" title="Xóa lớp Green này khỏi bố cục" type="button">🗑️</button>
            </div>
          </div>
        `;
      });

      // Tầng #4 Dưới cùng: Video Stock nền
      html += `
        <div class="p-1.5 rounded flex items-center justify-between text-[10.5px] font-mono bg-surface-container-lowest border border-surface-container text-on-surface-variant">
          <span>🎞️ LỚP #4 (DƯỚI CÙNG): Video Stock Nền Có Sẵn (Làm tối nhẹ)</span>
          <span>Z=0</span>
        </div>
      `;

      stackListEl.innerHTML = html;

      stackListEl.querySelectorAll(".layer-stack-row").forEach((row) => {
        row.addEventListener("click", (ev) => {
          if (ev.target.closest("button")) return;
          const st = row.dataset.selectType;
          const lid = row.dataset.layerId;
          selectLayer({ type: st, id: lid });
        });
      });

      stackListEl.querySelectorAll(".btn-layer-up").forEach((btn) => {
        btn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          moveGreenLayerZ(btn.dataset.layerId, +1);
        });
      });
      stackListEl.querySelectorAll(".btn-layer-down").forEach((btn) => {
        btn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          moveGreenLayerZ(btn.dataset.layerId, -1);
        });
      });
      stackListEl.querySelectorAll(".btn-layer-toggle").forEach((btn) => {
        btn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          const l = (layoutState.green_video_layers || []).find((x) => x.id === btn.dataset.layerId);
          if (l) {
            l.enabled = l.enabled === false ? true : false;
            refreshAllPreviewUI();
          }
        });
      });
      stackListEl.querySelectorAll(".btn-layer-del").forEach((btn) => {
        btn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          layoutState.green_video_layers = (layoutState.green_video_layers || []).filter((x) => x.id !== btn.dataset.layerId);
          layoutState.green_layers = layoutState.green_video_layers;
          if (selectedTarget.id === btn.dataset.layerId) {
            selectedTarget = { type: "script_char" };
          }
          refreshAllPreviewUI();
        });
      });
    }

    function moveGreenLayerZ(layerId, dir) {
      const sorted = [...(layoutState.green_video_layers || [])].sort((a, b) => (a.zIndex || 10) - (b.zIndex || 10));
      const idx = sorted.findIndex((x) => x.id === layerId);
      if (idx < 0) return;
      const swapIdx = idx + dir;
      if (swapIdx < 0 || swapIdx >= sorted.length) return;
      const tmp = sorted[idx];
      sorted[idx] = sorted[swapIdx];
      sorted[swapIdx] = tmp;
      sorted.forEach((item, i) => {
        item.zIndex = (i + 1) * 10;
      });
      layoutState.green_video_layers = sorted;
      layoutState.green_layers = sorted;
      refreshAllPreviewUI();
    }

    function selectLayer(target) {
      selectedTarget = target;
      syncInspectorInputsFromSelection();
      renderGreenStageDOM();
      applyScriptCharAndKaraokeDOM();
      renderLayerStackList();
    }

    function getActiveLayerObject() {
      if (selectedTarget.type === "script_char") return layoutState.script_character_green;
      if (selectedTarget.type === "karaoke_sub") return layoutState.subtitle_karaoke;
      return (layoutState.green_video_layers || []).find((x) => x.id === selectedTarget.id) || layoutState.script_character_green;
    }

    function syncInspectorInputsFromSelection() {
      const obj = getActiveLayerObject();
      if (!obj) return;
      if (selectedTarget.type === "script_char") {
        if (selectedTitleEl) selectedTitleEl.innerHTML = `<span class="material-symbols-outlined text-[15px] shrink-0">person_pin</span> <span class="truncate">2. Đang chỉnh: Lớp #2 Ảnh Green Kịch Bản (Đáy phải)</span>`;
        if (selectedZBadgeEl) selectedZBadgeEl.textContent = "Lớp #2 (Dưới Sub)";
        if (propY) propY.disabled = true;
        if (propOpacity) propOpacity.disabled = false;
      } else if (selectedTarget.type === "karaoke_sub") {
        if (selectedTitleEl) selectedTitleEl.innerHTML = `<span class="material-symbols-outlined text-[15px] shrink-0">subtitles</span> <span class="truncate">2. Đang chỉnh: Lớp #1 Phụ Đề Karaoke (Cỡ chữ ${obj.fontSize || 52}px)</span>`;
        if (selectedZBadgeEl) selectedZBadgeEl.textContent = "Lớp #1 (Cao nhất)";
        if (propY) propY.disabled = false;
        if (propOpacity) propOpacity.disabled = true;
      } else {
        if (selectedTitleEl) selectedTitleEl.innerHTML = `<span class="material-symbols-outlined text-[15px] shrink-0">movie</span> <span class="truncate">2. Đang chỉnh: Video Green [${obj.file}]</span>`;
        if (selectedZBadgeEl) selectedZBadgeEl.textContent = `Z-Index: ${obj.zIndex || 10}`;
        if (propY) propY.disabled = false;
        if (propOpacity) propOpacity.disabled = false;
      }
      if (propX) propX.value = String(Math.round(obj.x || 0));
      if (propY) propY.value = String(Math.round(obj.y || 0));
      if (propW) propW.value = String(Math.round(obj.width || 360));
      if (propH) propH.value = String(Math.round(obj.height || 220));
      const op = Number(obj.opacity !== undefined ? obj.opacity : 1.0);
      if (propOpacity) propOpacity.value = String(op.toFixed(2));
      if (propOpacityVal) propOpacityVal.textContent = `${op.toFixed(2)} (${Math.round(op * 100)}%)`;
    }

    [propX, propY, propW, propH, propOpacity].forEach((inp) => {
      if (!inp) return;
      inp.addEventListener("input", () => {
        const obj = getActiveLayerObject();
        if (!obj) return;
        if (propX) obj.x = Math.max(0, Math.min(1900, parseInt(propX.value, 10) || 0));
        if (propW) obj.width = Math.max(40, Math.min(1920, parseInt(propW.value, 10) || 360));
        if (propH) {
          const newH = Math.max(40, Math.min(1080, parseInt(propH.value, 10) || 220));
          obj.height = newH;
          if (selectedTarget.type === "karaoke_sub") {
            const mappedFs = Math.max(20, Math.min(110, Math.round(newH / 2.1)));
            obj.fontSize = mappedFs;
            obj.font_size = mappedFs;
          }
        }
        if (selectedTarget.type === "script_char") {
          obj.y = 1080 - obj.height;
          if (propY) propY.value = String(obj.y);
        } else if (propY) {
          obj.y = Math.max(0, Math.min(1060, parseInt(propY.value, 10) || 0));
        }
        if (propOpacity && selectedTarget.type !== "karaoke_sub") {
          obj.opacity = Math.max(0.1, Math.min(1.0, parseFloat(propOpacity.value) || 0.9));
          if (propOpacityVal) propOpacityVal.textContent = `${obj.opacity.toFixed(2)} (${Math.round(obj.opacity * 100)}%)`;
        }
        renderGreenStageDOM();
        applyScriptCharAndKaraokeDOM();
        renderLayerStackList();
      });
    });

    if (stockDarkenRange) {
      stockDarkenRange.addEventListener("input", () => {
        const val = parseFloat(stockDarkenRange.value) || 0.12;
        layoutState.stock_darken = layoutState.stock_darken || {};
        layoutState.stock_darken.brightness = -Math.abs(val);
        layoutState.stock_background = layoutState.stock_darken;
        applyScriptCharAndKaraokeDOM();
      });
    }

    // 5. Kéo thả (Drag) & Phóng to/Thu nhỏ (Resize) trực tiếp trên khung 16:9 Preview
    function startDragOrResize(startEv, action) {
      if (!previewContainer) return;
      startEv.preventDefault();
      const rect = previewContainer.getBoundingClientRect();
      const scaleX = 1920 / Math.max(1, rect.width);
      const scaleY = 1080 / Math.max(1, rect.height);
      const obj =
        action.target.type === "script_char" ? layoutState.script_character_green :
        action.target.type === "karaoke_sub" ? layoutState.subtitle_karaoke :
        (layoutState.green_video_layers || []).find((x) => x.id === action.target.id);
      if (!obj) return;

      const startX = startEv.clientX;
      const startY = startEv.clientY;
      const origX = Number(obj.x || 0);
      const origY = Number(obj.y || 0);
      const origW = Number(obj.width || 360);
      const origH = Number(obj.height || 220);
      const origFs = Number(obj.fontSize || obj.font_size || 52);

      function onMove(ev) {
        const dx = Math.round((ev.clientX - startX) * scaleX);
        const dy = Math.round((ev.clientY - startY) * scaleY);
        if (action.mode === "move") {
          obj.x = Math.max(0, Math.min(1920 - origW, origX + dx));
          if (action.target.type === "script_char") {
            obj.y = 1080 - obj.height;
          } else {
            obj.y = Math.max(0, Math.min(1080 - origH, origY + dy));
          }
        } else if (action.mode === "resize") {
          const dir = action.dir || "se";
          if (dir.includes("e")) obj.width = Math.max(100, Math.min(1920 - origX, origW + dx));
          if (dir.includes("s")) obj.height = Math.max(60, Math.min(1080 - origY, origH + dy));
          if (dir.includes("w")) {
            const newW = Math.max(100, origW - dx);
            obj.x = Math.max(0, origX + (origW - newW));
            obj.width = newW;
          }
          if (dir.includes("n")) {
            const newH = Math.max(60, origH - dy);
            if (action.target.type === "script_char") {
              obj.height = Math.min(1060, newH);
              obj.y = 1080 - obj.height;
            } else {
              obj.y = Math.max(0, origY + (origH - newH));
              obj.height = newH;
            }
          }
          // Nếu đang kéo 4 góc của khung Phụ Đề Karaoke -> Phóng to / thu nhỏ cỡ chữ trực tiếp!
          if (action.target.type === "karaoke_sub") {
            const ratioW = obj.width / Math.max(200, origW);
            const ratioH = obj.height / Math.max(60, origH);
            const scaleFactor = Math.max(0.45, Math.min(2.2, (ratioW + ratioH) / 2));
            const nextFs = Math.max(20, Math.min(110, Math.round(origFs * scaleFactor)));
            obj.fontSize = nextFs;
            obj.font_size = nextFs;
          }
        }
        syncInspectorInputsFromSelection();
        renderGreenStageDOM();
        applyScriptCharAndKaraokeDOM();
      }

      function onUp() {
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        renderLayerStackList();
        scheduleAutoSaveLayout();
      }

      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    }

    if (scriptCharBox) {
      scriptCharBox.addEventListener("mousedown", (ev) => {
        ev.stopPropagation();
        selectLayer({ type: "script_char" });
        const rDir = ev.target?.dataset?.resizeDir;
        if (rDir) {
          startDragOrResize(ev, { mode: "resize", dir: rDir, target: { type: "script_char" } });
        } else {
          startDragOrResize(ev, { mode: "move", target: { type: "script_char" } });
        }
      });
    }

    if (karaokeSubBox) {
      karaokeSubBox.addEventListener("mousedown", (ev) => {
        ev.stopPropagation();
        selectLayer({ type: "karaoke_sub" });
        const rDir = ev.target?.dataset?.resizeDir;
        if (rDir) {
          startDragOrResize(ev, { mode: "resize", dir: rDir, target: { type: "karaoke_sub" } });
        } else {
          startDragOrResize(ev, { mode: "move", target: { type: "karaoke_sub" } });
        }
      });
    }

    function refreshAllPreviewUI() {
      renderGreenStageDOM();
      applyScriptCharAndKaraokeDOM();
      renderLayerStackList();
      syncInspectorInputsFromSelection();
    }

    // 6. Hàm thêm 1 file Video/Ảnh Green vào màn hình Preview ngay lập tức
    function addGreenLayerToPreview(chosenFile, customX = null, customY = null) {
      if (!chosenFile) return;
      const layers = layoutState.green_video_layers || [];
      const maxZ = layers.reduce((m, x) => Math.max(m, x.zIndex || 10), 0);
      const newId = `green_layer_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
      const offset = (layers.length % 5) * 32;
      const ext = chosenFile.split(".").pop().toLowerCase();
      const isImg = ["png", "jpg", "jpeg", "webp"].includes(ext);
      const newLayer = {
        id: newId,
        name: chosenFile,
        file: chosenFile,
        type: isImg ? "image" : "video",
        enabled: true,
        x: customX !== null ? customX : 60 + offset,
        y: customY !== null ? customY : 60 + offset,
        width: 380,
        height: 210,
        opacity: 1.0,
        zIndex: maxZ + 10,
        chromaKey: !isImg,
        keyColor: "#00FF00",
        similarity: 0.28,
        blend: 0.08,
      };
      layers.push(newLayer);
      layoutState.green_video_layers = layers;
      layoutState.green_layers = layers;
      selectLayer({ type: "green_layer", id: newId });
      if (saveMsgEl) {
        saveMsgEl.textContent = `➕ Đã đưa [${chosenFile}] lên màn hình Preview! Hãy kéo thả vị trí / kích thước rồi bấm Lưu.`;
        saveMsgEl.className = "text-[10.5px] font-mono text-primary-container font-bold text-center";
      }
    }

    if (addGreenBtn && greenLibSelect) {
      addGreenBtn.addEventListener("click", () => {
        addGreenLayerToPreview(greenLibSelect.value);
      });
    }
    if (addGreenBtnTop && greenLibSelectTop) {
      addGreenBtnTop.addEventListener("click", () => {
        addGreenLayerToPreview(greenLibSelectTop.value);
      });
    }

    // 7. Chọn file Video/Ảnh Green trực tiếp từ máy tính -> Nạp vào Kho_Green VÀ đưa thẳng lên màn hình Preview!
    async function uploadGreenFilesAndAddToPreview(fileList, dropX = null, dropY = null) {
      if (!fileList || fileList.length === 0) return;
      const files = Array.from(fileList);
      if (pickGreenToPreviewBtn) {
        pickGreenToPreviewBtn.disabled = true;
        pickGreenToPreviewBtn.innerText = "⏳ Đang đưa Video Green vào Preview...";
      }
      try {
        for (let i = 0; i < files.length; i++) {
          const f = files[i];
          const res = await fetch("/api/green-library/upload", {
            method: "POST",
            headers: {
              "Content-Type": "application/octet-stream",
              "X-File-Name": encodeURIComponent(f.name),
            },
            body: f,
          });
          const data = await res.json();
          if (res.ok && data.success && data.added_file) {
            greenLibraryItems = data.items || greenLibraryItems;
            populateGreenLibraryDropdown();
            if (greenLibSelect) greenLibSelect.value = data.added_file;
            if (greenLibSelectTop) greenLibSelectTop.value = data.added_file;
            addGreenLayerToPreview(
              data.added_file,
              dropX !== null ? dropX + i * 25 : null,
              dropY !== null ? dropY + i * 25 : null
            );
            appendInstantLogToUI(`🎬 Đã nạp & đưa Video Green lên Preview: ${data.added_file}`, "RENDER", "INFO");
          }
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (pickGreenToPreviewBtn) {
          pickGreenToPreviewBtn.disabled = false;
          pickGreenToPreviewBtn.innerHTML = `<span class="material-symbols-outlined text-[16px] shrink-0">video_call</span><span class="truncate">🎬 ➕ Chọn File Green Từ Máy</span>`;
        }
      }
    }

    [pickGreenToPreviewBtn, importGreenBtn].forEach((btn) => {
      if (btn && greenFileUploadInput) {
        btn.addEventListener("click", () => {
          greenFileUploadInput.value = "";
          greenFileUploadInput.click();
        });
      }
    });

    if (greenFileUploadInput) {
      greenFileUploadInput.addEventListener("change", (ev) => {
        if (ev.target.files && ev.target.files.length > 0) {
          uploadGreenFilesAndAddToPreview(ev.target.files);
        }
      });
    }

    // Hỗ trợ Kéo & Thả (Drag & Drop) file Video/Ảnh Green từ máy tính thẳng vào khung Preview 16:9
    if (previewContainer) {
      previewContainer.addEventListener("dragover", (ev) => {
        ev.preventDefault();
        previewContainer.classList.add("ring-2", "ring-[#00ff87]");
      });
      previewContainer.addEventListener("dragleave", () => {
        previewContainer.classList.remove("ring-2", "ring-[#00ff87]");
      });
      previewContainer.addEventListener("drop", (ev) => {
        ev.preventDefault();
        previewContainer.classList.remove("ring-2", "ring-[#00ff87]");
        if (ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files.length > 0) {
          const rect = previewContainer.getBoundingClientRect();
          const dropX = Math.max(0, Math.min(1500, Math.round(((ev.clientX - rect.left) / Math.max(1, rect.width)) * 1920 - 160)));
          const dropY = Math.max(0, Math.min(840, Math.round(((ev.clientY - rect.top) / Math.max(1, rect.height)) * 1080 - 90)));
          uploadGreenFilesAndAddToPreview(ev.dataTransfer.files, dropX, dropY);
        }
      });
    }

    // 8. Nút Lưu Bố Cục Preview & Tạo Cache Video Green
    async function handleSaveVideoLayout(triggerBtn) {
      const origHtml = triggerBtn ? triggerBtn.innerHTML : "";
      if (triggerBtn) {
        triggerBtn.disabled = true;
        triggerBtn.innerText = "⏳ Đang lưu & tạo Cache...";
      }
      try {
        layoutState.green_layers = layoutState.green_video_layers;
        layoutState.script_green_character = layoutState.script_character_green;
        layoutState.karaoke_subtitle = layoutState.subtitle_karaoke;
        layoutState.stock_background = layoutState.stock_darken;

        const res = await fetch("/api/video-layout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(layoutState),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          if (data.layout) normalizeIncomingLayout(data.layout);
          refreshAllPreviewUI();
          if (saveMsgEl) {
            saveMsgEl.textContent = `✅ Đã lưu Vị trí / Kích thước / Cỡ chữ (${layoutState.subtitle_karaoke?.fontSize || 52}px) / Opacity & đóng gói Cache Video Green!`;
            saveMsgEl.className = "text-[10.5px] font-mono text-primary-container font-bold text-center";
          }
          appendInstantLogToUI("💾 Đã lưu bố cục Preview (Tách lớp Video Green + Ảnh Green sát đáy phải Opacity 0.9 + Karaoke Sub cao nhất)!", "RENDER", "INFO");
        }
      } catch (err) {
        if (saveMsgEl) saveMsgEl.textContent = "❌ Lỗi lưu cấu hình: " + err.message;
      } finally {
        if (triggerBtn) {
          triggerBtn.disabled = false;
          triggerBtn.innerHTML = origHtml;
        }
      }
    }

    if (saveLayoutBtn) {
      saveLayoutBtn.addEventListener("click", () => handleSaveVideoLayout(saveLayoutBtn));
    }
    if (saveLayoutBtnTop) {
      saveLayoutBtnTop.addEventListener("click", () => handleSaveVideoLayout(saveLayoutBtnTop));
    }

    function populateGreenLibraryDropdown() {
      const shortName = (fn) => {
        const s = String(fn || "");
        return s.length > 32 ? s.slice(0, 22) + "..." + s.slice(-7) : s;
      };
      const html = (!greenLibraryItems || greenLibraryItems.length === 0)
        ? `<option value="SUB.mp4">🎬 SUB.mp4 (Kho_Green)</option>`
        : greenLibraryItems
            .map((it) => `<option value="${it.file}" title="${it.file} (${it.size_kb} KB)">${it.type === "video" ? "🎬" : "🖼️"} ${shortName(it.file)} (${it.size_kb} KB)</option>`)
            .join("");
      if (greenLibSelect) greenLibSelect.innerHTML = html;
      if (greenLibSelectTop) greenLibSelectTop.innerHTML = html;
    }

    // Tải dữ liệu ban đầu từ Backend (/api/video-layout)
    fetch("/api/video-layout")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.layout) {
          normalizeIncomingLayout(data.layout);
        }
        if (data && Array.isArray(data.green_library)) {
          greenLibraryItems = data.green_library;
          populateGreenLibraryDropdown();
        }
        refreshAllPreviewUI();
      })
      .catch(() => {
        refreshAllPreviewUI();
      });
  }

  // Init App (sau khi toàn bộ biến trạng thái & hàm đã được khởi tạo đầy đủ, chống lỗi TDZ 100%)
  initApp();
  safeSetup(setupSystemLogsAndDiagnostics, "SystemLogsAndDiagnostics");
  safeSetup(setupVoiceSelectorAndTuning, "VoiceSelectorAndTuning");
  safeSetup(setupWindowCloseAutoShutdown, "WindowCloseAutoShutdown");
  safeSetup(setupGithubOtaAutoUpdater, "GithubOtaAutoUpdater");
  safeSetup(setupPerformanceModeSelector, "PerformanceModeSelector");
  safeSetup(setupSkill04InteractivePreview, "Skill04InteractivePreview");
});