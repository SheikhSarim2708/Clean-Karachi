
const API_BASE_URL = "http://127.0.0.1:5000";

const statCards = document.querySelectorAll(".admin-stat-card h2");
const recentSection = document.querySelector(".admin-recent");
const emptyState = document.querySelector(".admin-empty-state");

async function adminRequest(url) {
    const response = await fetch(`${API_BASE_URL}${url}`, {
        credentials: "include"
    });

    const data = await response.json();

    if (response.status === 401 || response.status === 403) {
        window.location.href = "login.html";
        throw new Error("Admin login required.");
    }

    if (!response.ok) {
        throw new Error(data.message || "Unable to load dashboard.");
    }

    return data;
}

async function loadAdminStats() {
    try {
        const data = await adminRequest("/api/admin/reports/summary");

        const summary = data.summary || data;

        statCards[0].textContent =
            summary.total_complaints ?? summary.total ?? 0;

        statCards[1].textContent =
            summary.pending ?? summary.pending_complaints ?? 0;

        statCards[2].textContent =
            summary.in_progress ?? summary.in_progress_complaints ?? 0;

        statCards[3].textContent =
            summary.resolved ?? summary.resolved_complaints ?? 0;

    } catch (error) {
        console.error("Statistics error:", error);
    }
}

async function loadRecentComplaints() {
    try {
        const data = await adminRequest(
            "/api/admin/complaints?page=1&page_size=5"
        );

        const complaints = data.complaints || [];

        const container = document.createElement("div");
        container.className = "admin-recent-list";

        if (complaints.length === 0) {
            emptyState.style.display = "block";
            return;
        }

        emptyState.style.display = "none";

        complaints.forEach(complaint => {
            const card = document.createElement("article");
            card.className = "admin-recent-card";

            const title = document.createElement("h3");
            title.textContent = complaint.title || "Untitled Complaint";

            const details = document.createElement("p");
            details.textContent =
                `Complaint #${complaint.id} | ${complaint.category || "N/A"} | ${complaint.area || "N/A"}`;

            const status = document.createElement("p");
            status.textContent =
                `Status: ${(complaint.status || "pending").replace("_", " ")}`;

            const date = document.createElement("p");
            date.textContent = complaint.created_at
                ? new Date(complaint.created_at).toLocaleDateString()
                : "";

            card.append(title, details, status, date);
            container.appendChild(card);
        });

        recentSection.appendChild(container);

    } catch (error) {
        console.error("Recent complaints error:", error);
    }
}

async function initializeAdminDashboard() {
    await Promise.all([
        loadAdminStats(),
        loadRecentComplaints()
    ]);
}

initializeAdminDashboard();
