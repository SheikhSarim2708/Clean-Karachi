
const API_BASE_URL = "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", async function () {

    const statNumbers = document.querySelectorAll(".stat-number");
    const filter = document.querySelector(".staff-filter");
    const emptyState = document.querySelector(".staff-empty-state");
    const section = document.querySelector(".assigned-complaints");

    let allComplaints = [];

    let complaintList = document.getElementById("staff-complaint-list");

    if (!complaintList) {
        complaintList = document.createElement("div");
        complaintList.id = "staff-complaint-list";

        emptyState.insertAdjacentElement("afterend", complaintList);
    }

    async function loadComplaints() {

        try {
            const response = await fetch(
                `${API_BASE_URL}/api/staff/complaints`,
                {
                    method: "GET",
                    credentials: "include"
                }
            );

            const data = await response.json();

            if (response.status === 401) {
                alert("Please login first.");
                window.location.href = "login.html";
                return;
            }

            if (response.status === 403) {
                alert("Staff access required.");
                window.location.href = "login.html";
                return;
            }

            if (!response.ok) {
                throw new Error(data.error || "Unable to load complaints.");
            }

            allComplaints = Array.isArray(data)
                ? data
                : (data.complaints || []);

            updateDashboard();

        } catch (error) {
            console.error("Staff dashboard error:", error);
            alert(error.message || "Unable to connect to server.");
        }
    }

    function updateDashboard() {

        const assigned = allComplaints.length;

        const pending = allComplaints.filter(
            item => item.status === "assigned"
        ).length;

        const inProgress = allComplaints.filter(
            item => item.status === "in_progress"
        ).length;

        const resolved = allComplaints.filter(
            item => item.status === "resolved"
        ).length;

        statNumbers[0].textContent = assigned;
        statNumbers[1].textContent = pending;
        statNumbers[2].textContent = inProgress;
        statNumbers[3].textContent = resolved;

        displayComplaints();
    }

    function displayComplaints() {

        const selectedStatus = filter.value;

        const filteredComplaints = selectedStatus === "all"
            ? allComplaints
            : allComplaints.filter(
                item => item.status === selectedStatus
            );

        complaintList.innerHTML = "";

        if (filteredComplaints.length === 0) {
            emptyState.style.display = "block";
            emptyState.querySelector("h3").textContent =
                allComplaints.length === 0
                    ? "No Assigned Complaints"
                    : "No Complaints Found";

            return;
        }

        emptyState.style.display = "none";

        filteredComplaints.forEach(function (complaint) {

            const card = document.createElement("div");
            card.className = "staff-complaint-card";

            const title = document.createElement("h3");
            title.textContent = complaint.title;

            const category = document.createElement("p");
            category.textContent =
                "Category: " + (complaint.category || "N/A");

            const area = document.createElement("p");
            area.textContent =
                "Area: " + (complaint.area || "N/A");

            const status = document.createElement("p");
            status.textContent =
                "Status: " + complaint.status.replace("_", " ");

            const date = document.createElement("p");
            date.textContent = "Date: " +
                (complaint.created_at
                    ? new Date(complaint.created_at).toLocaleDateString()
                    : "N/A");

            const button = document.createElement("button");
            button.type = "button";
            button.textContent = "View Details";

            button.addEventListener("click", function () {
                window.location.href =
                    "staff-complaint-details.html?id=" + complaint.id;
            });

            card.appendChild(title);
            card.appendChild(category);
            card.appendChild(area);
            card.appendChild(status);
            card.appendChild(date);
            card.appendChild(button);

            complaintList.appendChild(card);
        });
    }

    // Filter event
    filter.addEventListener("change", displayComplaints);

    await loadComplaints();

});
