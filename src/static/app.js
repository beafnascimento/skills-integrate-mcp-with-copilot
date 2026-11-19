document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const accountButton = document.getElementById("account-button");
  const accountMenu = document.getElementById("account-menu");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const accountStatus = document.getElementById("account-status");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");
  let isTeacher = false;

  function showMessage(message, type = "error") {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  function updateAccountControls(username = "") {
    accountStatus.textContent = username ? `Signed in as ${username}` : "Student view";
    loginButton.classList.toggle("hidden", isTeacher);
    logoutButton.classList.toggle("hidden", !isTeacher);
    signupForm.closest("section").classList.toggle("hidden", !isTeacher);
  }

  async function responseMessage(response) {
    const result = await response.json();
    return result.detail || result.message || "An error occurred";
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error(await responseMessage(response));
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      while (activitySelect.options.length > 1) {
        activitySelect.remove(1);
      }

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) => `<li>
                      <span class="participant-email">${escapeHtml(email)}</span>
                      ${
                        isTeacher
                          ? `<button class="delete-btn" data-activity="${escapeHtml(name)}" data-email="${escapeHtml(email)}" aria-label="Remove ${escapeHtml(email)} from ${escapeHtml(name)}">❌</button>`
                          : ""
                      }
                    </li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
      return true;
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
      return false;
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      if (response.ok) {
        // Refresh activities list to show updated participants
        const refreshed = await fetchActivities();
        showMessage(
          refreshed
            ? await responseMessage(response)
            : "Unregistered successfully, but failed to refresh activities.",
          refreshed ? "success" : "error"
        );
      } else {
        showMessage(await responseMessage(response));
      }
    } catch (error) {
      console.error("Error unregistering:", error);
      showMessage("Failed to unregister. Please try again.");
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      if (response.ok) {
        signupForm.reset();

        // Refresh activities list to show updated participants
        const refreshed = await fetchActivities();
        showMessage(
          refreshed
            ? await responseMessage(response)
            : "Registered successfully, but failed to refresh activities.",
          refreshed ? "success" : "error"
        );
      } else {
        showMessage(await responseMessage(response));
      }
    } catch (error) {
      console.error("Error signing up:", error);
      showMessage("Failed to sign up. Please try again.");
    }
  });

  accountButton.addEventListener("click", () => {
    const isExpanded = accountButton.getAttribute("aria-expanded") === "true";
    accountButton.setAttribute("aria-expanded", String(!isExpanded));
    accountMenu.classList.toggle("hidden", isExpanded);
  });

  loginButton.addEventListener("click", () => {
    loginDialog.showModal();
    accountMenu.classList.add("hidden");
    accountButton.setAttribute("aria-expanded", "false");
  });

  document.getElementById("cancel-login").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginMessage.textContent = "";
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        loginMessage.textContent = await responseMessage(response);
        return;
      }

      const result = await response.json();
      isTeacher = true;
      updateAccountControls(result.username);
      loginForm.reset();
      loginDialog.close();
      const refreshed = await fetchActivities();
      showMessage(
        refreshed
          ? "Teacher login successful."
          : "Login succeeded, but failed to refresh activities.",
        refreshed ? "success" : "error"
      );
    } catch (error) {
      console.error("Error logging in:", error);
      loginMessage.textContent = "Failed to log in. Please try again.";
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        showMessage(await responseMessage(response));
        return;
      }
      isTeacher = false;
      updateAccountControls();
      const refreshed = await fetchActivities();
      accountMenu.classList.add("hidden");
      accountButton.setAttribute("aria-expanded", "false");
      showMessage(
        refreshed
          ? "Logged out successfully."
          : "Logged out, but failed to refresh activities.",
        refreshed ? "success" : "error"
      );
    } catch (error) {
      console.error("Error logging out:", error);
      showMessage("Failed to log out. Please try again.");
    }
  });

  async function restoreSession() {
    try {
      const response = await fetch("/auth/session");
      if (!response.ok) throw new Error(await responseMessage(response));
      const session = await response.json();
      isTeacher = session.authenticated;
      updateAccountControls(session.username || "");
    } catch (error) {
      console.error("Error checking login session:", error);
      updateAccountControls();
    }
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  // Initialize app
  updateAccountControls();
  restoreSession().then(fetchActivities);
});
