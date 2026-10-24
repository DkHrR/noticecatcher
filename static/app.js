document.addEventListener("DOMContentLoaded", function () {
  var btnRun = document.getElementById("btn-run");
  var stateStart = document.getElementById("state-start");
  var stateLoading = document.getElementById("state-loading");
  var stateResults = document.getElementById("state-results");
  var stateError = document.getElementById("state-error");
  var errorMessage = document.getElementById("error-message");
  var noticesList = document.getElementById("notices-list");
  var needsCheckList = document.getElementById("needs-check-list");
  var btnDownload = document.getElementById("btn-download");

  if (!btnRun) return;

  function showError(msg) {
    if (stateLoading) stateLoading.classList.add("hidden");
    if (stateStart) stateStart.classList.remove("hidden");
    if (errorMessage) errorMessage.textContent = msg;
    if (stateError) stateError.classList.remove("hidden");
  }

  function clearElement(el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  function renderNotices(notices) {
    clearElement(noticesList);
    if (!notices || notices.length === 0) {
      var emptyMsg = document.createElement("p");
      emptyMsg.className = "card-source";
      emptyMsg.textContent = "No notices found.";
      noticesList.appendChild(emptyMsg);
      return;
    }

    notices.forEach(function (n) {
      var card = document.createElement("div");
      card.className = "notice-card";

      var header = document.createElement("div");
      header.className = "card-header";

      var title = document.createElement("h3");
      title.className = "card-title";
      title.textContent = n.title || "Untitled Notice";
      if (n.kind === "cancel") {
        title.classList.add("cancelled");
      }
      header.appendChild(title);

      if (n.kind === "cancel") {
        var badge = document.createElement("span");
        badge.className = "badge-cancelled";
        badge.textContent = "Cancelled";
        header.appendChild(badge);
      }
      card.appendChild(header);

      var meta = document.createElement("div");
      meta.className = "card-meta";

      if (n.date) {
        var dateSpan = document.createElement("span");
        dateSpan.textContent = "Date: " + n.date;
        meta.appendChild(dateSpan);
      }

      if (n.time) {
        if (n.date) {
          var dot = document.createElement("span");
          dot.className = "dot-separator";
          dot.textContent = "•";
          meta.appendChild(dot);
        }
        var timeSpan = document.createElement("span");
        timeSpan.textContent = "Time: " + n.time;
        meta.appendChild(timeSpan);
      }

      if (n.date || n.time) {
        card.appendChild(meta);
      }

      if (n.sender) {
        var src = document.createElement("p");
        src.className = "card-source";
        src.textContent = "From message: " + n.sender;
        card.appendChild(src);
      }

      noticesList.appendChild(card);
    });
  }

  function renderNeedsCheck(items) {
    clearElement(needsCheckList);
    if (!items || items.length === 0) {
      var emptyMsg = document.createElement("p");
      emptyMsg.className = "card-source";
      emptyMsg.textContent = "No items need checking.";
      needsCheckList.appendChild(emptyMsg);
      return;
    }

    items.forEach(function (item) {
      var card = document.createElement("div");
      card.className = "notice-card";

      var title = document.createElement("h3");
      title.className = "card-title";
      title.textContent = item.title || "Unclear notice";
      card.appendChild(title);

      var meta = document.createElement("p");
      meta.className = "card-meta";
      meta.textContent = "Original words: ";

      var tag = document.createElement("span");
      tag.className = "unclear-tag";
      tag.textContent = '"' + (item.words || item.date_text || "") + '"';
      meta.appendChild(tag);
      card.appendChild(meta);

      if (item.sender) {
        var src = document.createElement("p");
        src.className = "card-source";
        src.textContent = "From message: " + item.sender;
        card.appendChild(src);
      }

      needsCheckList.appendChild(card);
    });
  }

  function pollJobStatus(jobId) {
    var interval = setInterval(function () {
      fetch("/status/" + jobId)
        .then(function (res) {
          if (!res.ok) {
            throw new Error("Status check failed (" + res.status + ")");
          }
          return res.json();
        })
        .then(function (data) {
          if (data.status === "completed") {
            clearInterval(interval);
            stateLoading.classList.add("hidden");

            var result = data.result || {};
            var notices = result.notices || [];
            var needsCheck = result.needs_check || [];

            renderNotices(notices);
            renderNeedsCheck(needsCheck);

            if (btnDownload) {
              btnDownload.setAttribute("href", "/download/" + jobId + ".ics");
            }
            stateResults.classList.remove("hidden");
          } else if (data.status === "failed") {
            clearInterval(interval);
            showError("Processing failed: " + (data.error || "Unknown error"));
          }
        })
        .catch(function (err) {
          clearInterval(interval);
          showError("Error: " + err.message);
        });
    }, 500);
  }

  btnRun.addEventListener("click", function () {
    if (stateError) stateError.classList.add("hidden");
    if (stateStart) stateStart.classList.add("hidden");
    if (stateLoading) stateLoading.classList.remove("hidden");
    if (stateResults) stateResults.classList.add("hidden");

    fetch("/run-sample", { method: "POST" })
      .then(function (res) {
        if (res.status === 501) {
          return res.text().then(function (text) {
            throw new Error(text || "not wired yet");
          });
        }
        if (!res.ok) {
          throw new Error("HTTP error " + res.status);
        }
        return res.json();
      })
      .then(function (data) {
        if (!data.job_id) {
          throw new Error("Invalid response from server");
        }
        pollJobStatus(data.job_id);
      })
      .catch(function (err) {
        showError(err.message);
      });
  });
});
