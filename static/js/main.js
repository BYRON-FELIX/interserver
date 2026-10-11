/* ============================================================
   InterServer dashboard — frontend interactions
   ============================================================ */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {

        /* ---------------------------------------------------
           Sidebar toggle (mobile / collapsed mode)
        --------------------------------------------------- */
        const sidebar     = document.getElementById("sidebar");
        const main        = document.querySelector(".main");
        const toggleBtn   = document.getElementById("sidebarToggle");

        if (toggleBtn && sidebar) {
            toggleBtn.addEventListener("click", function () {
                sidebar.classList.toggle("open");
                if (main) main.classList.toggle("expanded");
            });
        }

        /* ---------------------------------------------------
           Click outside to close on mobile
        --------------------------------------------------- */
        document.addEventListener("click", function (e) {
            if (!sidebar || !toggleBtn) return;
            const isMobile = window.innerWidth <= 900;
            if (!isMobile) return;

            const clickedInside  = sidebar.contains(e.target);
            const clickedToggle  = toggleBtn.contains(e.target);

            if (!clickedInside && !clickedToggle) {
                sidebar.classList.remove("open");
                if (main) main.classList.remove("expanded");
            }
        });

        /* ---------------------------------------------------
           Keyboard shortcut: Ctrl/Cmd + K focuses search
        --------------------------------------------------- */
        const search = document.querySelector(".topbar-search");
        if (search) {
            document.addEventListener("keydown", function (e) {
                if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                    e.preventDefault();
                    search.focus();
                    search.select();
                }
            });
        }

    });
})();