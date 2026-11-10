
const API_BASE_URL = "http://127.0.0.1:5000";

const params = new URLSearchParams(window.location.search);
const complaintId = params.get("id");

const statusBadge = document.querySelector(".detail-status");
const complaintReference = document.querySelector(".detail-card-heading h2");
const complaintDate = document.querySelector(".detail-date");
const detailFields = document.querySelectorAll(".detail-field p");
const statusForm = document.querySelector(".status-update-card form");
const statusSelect = document.getElementById("complaint-status");

function showMessage(message, isError = false) {
    let messageBox = document.getElementById("staff-detail-message");

    if (!messageBox) {
        messageBox = document.createElement("p");
        messageBox.id = "staff-detail-message";
        statusForm.before(messageBox);
    }

    messageBox.textContent = message;
    messageBox.style.color = isError ? "red" : "green";
    messageBox.style.marginTop = "15px";
}

async function loadComplaintDetails() {
    if (!complaintId) {
        showMessage("Complaint ID is missing.", true);
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/staff/complaints/${complaintId}`,
            { credentials: "include" }
        );

        const data = await response.json();

        if (response.status === 401 || response.status === 403) {
            window.location.href = "login.html";
            return;
        }

        if (!response.ok) {
            throw new Error(data.message || "Unable to load complaint.");
        }

        const complaint = data.complaint || data;

        complaintReference.textContent = `#${complaint.id || complaintId}`;

        complaintDate.textContent = complaint.created_at
            ? new Date(complaint.created_at).toLocaleDateString()
            : "";

        detailFields[0].textContent = complaint.title || "N/A";
        detailFields[1].textContent = complaint.category || "N/A";
        detailFields[2].textContent = complaint.area || "N/A";
        detailFields[3].textContent = complaint.address_detail || "N/A";
        detailFields[4].textContent = complaint.description || "N/A";

        const currentStatus = complaint.status || "assigned";

        statusBadge.textContent = currentStatus.replace("_", " ");
        statusBadge.className = `detail-status status-${currentStatus}`;

        statusSelect.value = currentStatus;

        if (currentStatus === "assigned") {
            statusSelect.innerHTML = `
                <option value="assigned">Assigned</option>
                <option value="in_progress">In Progress</option>
            `;
        } else if (currentStatus === "in_progress") {
            statusSelect.innerHTML = `
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
            `;
        } else {
            statusSelect.innerHTML = `
                <option value="resolved">Resolved</option>
            `;
        }

        statusSelect.value = currentStatus;

    } catch (error) {
        showMessage(error.message, true);
    }
}

statusForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const newStatus = statusSelect.value;
    const button = statusForm.querySelector("button[type='submit']");

    button.disabled = true;
    button.textContent = "Updating...";

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/staff/complaints/${complaintId}/status`,
            {
                method: "PUT",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    status: newStatus
                })
            }
        );

        const data = await response.json();

        if (response.status === 401 || response.status === 403) {
            window.location.href = "login.html";
            return;
        }

        if (!response.ok) {
            throw new Error(data.message || "Status update failed.");
        }

        alert("Complaint status updated successfully!");
        window.location.href = "staff-dashboard.html";

    } catch (error) {
        showMessage(error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Update Status";
    }
});

loadComplaintDetails();
