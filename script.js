const API_URL = "/items";

const form = document.querySelector("#itemForm");
const itemId = document.querySelector("#itemId");
const codeInput = document.querySelector("#code");
const itemInput = document.querySelector("#item");
const priceInput = document.querySelector("#price");
const tableBody = document.querySelector("#itemsTable");
const message = document.querySelector("#message");
const submitBtn = document.querySelector("#submitBtn");
const cancelBtn = document.querySelector("#cancelBtn");
const refreshBtn = document.querySelector("#refreshBtn");

function setMessage(text, isError = false) {
    message.textContent = text;
    message.classList.toggle("error", isError);
}

function formatPrice(value) {
    return Number(value).toFixed(2);
}

function resetForm() {
    form.reset();
    itemId.value = "";
    submitBtn.textContent = "Add Item";
    cancelBtn.hidden = true;
}

async function requestJson(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Request failed");
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

function renderItems(items) {
    if (!items.length) {
        tableBody.innerHTML = '<tr><td colspan="4" class="empty">No items found.</td></tr>';
        return;
    }

    tableBody.innerHTML = items.map((record) => `
        <tr>
            <td>${record.code}</td>
            <td>${record.item}</td>
            <td>${formatPrice(record.price)}</td>
            <td>
                <div class="row-actions">
                    <button type="button" class="secondary" data-action="edit" data-id="${record.id}">Edit</button>
                    <button type="button" class="danger" data-action="delete" data-id="${record.id}">Delete</button>
                </div>
            </td>
        </tr>
    `).join("");
}

async function loadItems() {
    try {
        setMessage("Loading items...");
        const items = await requestJson(API_URL);
        renderItems(items);
        setMessage("");
    } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="4" class="empty">Unable to load items.</td></tr>';
        setMessage(error.message, true);
    }
}

function getFormData() {
    return {
        code: codeInput.value.trim(),
        item: itemInput.value.trim(),
        price: Number(priceInput.value),
    };
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = getFormData();
    const id = itemId.value;

    try {
        if (id) {
            await requestJson(`${API_URL}/${id}`, {
                method: "PUT",
                body: JSON.stringify(payload),
            });
            setMessage("Item updated successfully.");
        } else {
            await requestJson(API_URL, {
                method: "POST",
                body: JSON.stringify(payload),
            });
            setMessage("Item added successfully.");
        }

        resetForm();
        await loadItems();
    } catch (error) {
        setMessage(error.message, true);
    }
});

tableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) {
        return;
    }

    const id = button.dataset.id;
    const action = button.dataset.action;

    if (action === "edit") {
        try {
            const record = await requestJson(`${API_URL}/${id}`);
            itemId.value = record.id;
            codeInput.value = record.code;
            itemInput.value = record.item;
            priceInput.value = record.price;
            submitBtn.textContent = "Update Item";
            cancelBtn.hidden = false;
            codeInput.focus();
            setMessage("Editing selected item.");
        } catch (error) {
            setMessage(error.message, true);
        }
    }

    if (action === "delete") {
        const confirmed = confirm("Delete this item?");
        if (!confirmed) {
            return;
        }

        try {
            await requestJson(`${API_URL}/${id}`, { method: "DELETE" });
            setMessage("Item deleted successfully.");
            await loadItems();
        } catch (error) {
            setMessage(error.message, true);
        }
    }
});

cancelBtn.addEventListener("click", () => {
    resetForm();
    setMessage("");
});

refreshBtn.addEventListener("click", loadItems);

loadItems();
