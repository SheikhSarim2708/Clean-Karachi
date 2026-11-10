
const API_BASE_URL = "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", async function () {

    const stats = document.querySelectorAll(".dashboard-stat-card h2");
    const emptyState = document.querySelector(".dashboard-empty-state");
    const complaintsSection = document.querySelector(".my-complaints-section");

    if (!complaintsSection || stats.length < 4) {
        console.error("Dashboard elements not found.");
        return;
    }

    let complaintsContainer = document.getElementById("citizen-complaints-list");

    if (!complaintsContainer) {
        complaintsContainer = document.createElement("div");
        complaintsContainer.id = "citizen-complaints-list";

        if (emptyState) {
            emptyState.insertAdjacentElement("afterend", complaintsContainer);
        } else {
            complaintsSection.appendChild(complaintsContainer);
        }
    }

    try {

        const response = await fetch(`${API_BASE_URL}/api/complaints`, {
            method: "GET",
            credentials: "include"
        });

        const data = await response.json();

        if (response.status === 401) {
            alert("Please login to access your dashboard.");
            window.location.href = "login.html";
            return;
        }

        if (!response.ok) {
            throw new Error(data.error || "Unable to load complaints.");
        }

        const complaints = Array.isArray(data)
            ? data
            : (data.complaints || []);

        const total = complaints.length;

        const pending = complaints.filter(
            item => item.status === "pending"
        ).length;

        const inProgress = complaints.filter(
            item => item.status === "in_progress"
        ).length;

        const resolved = complaints.filter(
            item => item.status === "resolved"
        ).length;

        stats[0].textContent = total;
        stats[1].textContent = pending;
        stats[2].textContent = inProgress;
        stats[3].textContent = resolved;

        if (total === 0) {
            if (emptyState) {
                emptyState.style.display = "block";
            }

            complaintsContainer.innerHTML = "";
            return;
        }

        if (emptyState) {
            emptyState.style.display = "none";
        }

        complaints.sort(function (a, b) {
            return new Date(b.created_at) - new Date(a.created_at);
        });

        const recentComplaints = complaints.slice(0, 5);

        complaintsContainer.innerHTML = "";

        recentComplaints.forEach(function (complaint) {

            const card = document.createElement("div");
            card.className = "citizen-complaint-item";

            const title = document.createElement("h3");
            title.textContent = complaint.title;

            const details = document.createElement("p");
            details.textContent =
                "Category: " + (complaint.category || "N/A") +
                " | Area: " + (complaint.area || "N/A");

            const status = document.createElement("p");
            status.textContent =
                "Status: " + complaint.status.replace("_", " ");

            const date = document.createElement("p");
            date.textContent = "Submitted: " +
                (complaint.created_at
                    ? new Date(complaint.created_at).toLocaleDateString()
                    : "N/A");

            const viewButton = document.createElement("button");
            viewButton.type = "button";
            viewButton.textContent = "View Details";

            viewButton.addEventListener("click", function () {
                window.location.href =
                    "complaint-details.html?id=" + complaint.id;
            });

            card.appendChild(title);
            card.appendChild(details);
            card.appendChild(status);
            card.appendChild(date);
            card.appendChild(viewButton);

            complaintsContainer.appendChild(card);
        });

    } catch (error) {
        console.error("Dashboard error:", error);
        alert(error.message || "Unable to connect to server.");
    }

});
