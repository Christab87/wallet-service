let activeMint = null;
let pendingMint = null;
let currency = "usd";
let customMints = JSON.parse(localStorage.getItem("customMints")) || [];
let currentPrice = null; // Cache current price to reduce API requests

// Load persisted currency preference from localStorage
function loadCurrency() {
    const stored = localStorage.getItem("currency");
    if (stored) {
        currency = stored;
    }
    updateCurrencyUI();
}

// Toggle between USD and EUR, maintaining selection in localStorage
function toggleCurrency() {
    currency = currency === "usd" ? "eur" : "usd";
    localStorage.setItem("currency", currency);

    updateCurrencyUI();
    loadPrice();
    loadBalance();
    updateBtcChart();
}

// Update the UI label to reflect the currently selected currency
function updateCurrencyUI() {
    const label = document.getElementById("currency-label");
    if (label) {
        label.innerText = currency.toUpperCase();
    }
}

// Fetch and display the current Bitcoin price in the selected currency
async function loadPrice() {
    const el = document.getElementById("btc-price");

    try {
        const res = await fetch("/api/btc-price");
        const data = await res.json();
        currentPrice = data; // Cache price for other functions
        
        // Update exchange rates from cached price (no API call)
        if (typeof fetchExchangeRates === 'function') {
            fetchExchangeRates();
        }

        if (data[currency]) {
            const symbol = currency === "usd" ? "$" : "€";
            const priceValue = data[currency];
            el.innerText = symbol + priceValue.toLocaleString();

            // Record price in history for chart updates
            if (typeof recordPriceHistory === 'function') {
                recordPriceHistory(data.usd);
                // Update chart if available
                if (window.btcChart) {
                    updateBtcChart();
                }
            }

            el.classList.remove("price-pulse");
            void el.offsetWidth;
            el.classList.add("price-pulse");
            
            // Update balance fiat value with new price
            updateBalanceFiat();

        } else {
            el.innerText = "Error";
        }

    } catch {
        el.innerText = "Error";
    }
}

// Calculate and display balance in fiat currency equivalent
function updateFiatValue(balance, price) {
    const el = document.getElementById("fiat-value");

    if (!price || !price[currency]) {
        el.innerText = "≈ --";
        return;
    }

    const btc = balance / 100000000;
    const fiat = btc * price[currency];
    const symbol = currency === "usd" ? "$" : "€";

    el.innerText = `≈ ${symbol}${fiat.toFixed(2)}`;
}

// Fetch and update the total wallet balance
async function loadBalance() {
    const el = document.getElementById("balance");

    try {
        const res = await fetch("/api/wallet/balance");
        const data = await res.json();
        el.innerText = data.balance + " sats";
        
        // Update fiat value with cached price
        updateBalanceFiat();
    } catch {
        el.innerText = "Error";
    }
}

// Update balance fiat value using cached price (no API call)
function updateBalanceFiat() {
    const balanceEl = document.getElementById("balance");
    const fiatEl = document.getElementById("fiat-value");
    
    // Extract balance from text (e.g., "7500 sats" -> 7500)
    const balanceText = balanceEl.innerText;
    const balance = parseInt(balanceText);
    
    if (!balance || !currentPrice) {
        fiatEl.innerText = "≈ --";
        return;
    }
    
    updateFiatValue(balance, currentPrice);
}

// Update Bitcoin price chart with latest data
async function updateBtcChart() {
    if (!window.btcChart || !priceHistoryUSD || priceHistoryUSD.length === 0) return;
    
    // Update exchange rates from cached price (no API call needed)
    if (typeof fetchExchangeRates === 'function') {
        fetchExchangeRates();
    }
    
    // Convert prices based on current currency
    const convertedPrices = convertHistoricalPrices();
    const priceLabels = convertedPrices.map(p => p.time);
    const priceData = convertedPrices.map(p => p.price);
    
    // Update chart with converted data
    window.btcChart.data.labels = priceLabels;
    window.btcChart.data.datasets[0].label = "BTC Price (" + currency.toUpperCase() + ")";
    window.btcChart.data.datasets[0].data = priceData;
    window.btcChart.update();
}

// Process received token and add proofs to wallet
async function receiveToken() {
    const input = document.getElementById("receive-token-input");
    const status = document.getElementById("receive-status");

    const token = input.value.trim();

    if (!token) {
        status.innerText = "Please paste a token";
        return;
    }

    try {
        const res = await fetch("/api/receive", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ token })
        });

        const data = await res.json();

        if (data.status === "ok") {
            // Display success message after receiving tokens
            status.innerText = `Received ${data.received} sats`;
            input.value = "";

            loadBalance();
        } else {
            status.innerText = "Error receiving token";
        }

    } catch {
        status.innerText = "Network error";
    }
}

// Highlight the currently active navigation item
function setActiveMenu(view) {
    const items = document.querySelectorAll(".nav-item");

    items.forEach(item => item.classList.remove("active"));

    items.forEach(item => {
        if (item.getAttribute("onclick")?.includes(view)) {
            item.classList.add("active");
        }
    });
}

// Display the requested view and hide others
function showView(view) {
    document.getElementById("wallet-view").style.display = "none";
    document.getElementById("mint-view").style.display = "none";
    document.getElementById("receive-view").style.display = "none";
    document.getElementById("send-view").style.display = "none";
    document.getElementById("history-view").style.display = "none";

    // Clear any status messages from the receive view when switching tabs
    const status = document.getElementById("receive-status");
    if (status) {
        status.innerText = "";
    }

    if (view === "wallet") {
        document.getElementById("wallet-view").style.display = "block";
    }

    if (view === "mint") {
        document.getElementById("mint-view").style.display = "block";
        loadMints();
    }

    if (view === "receive") {
        document.getElementById("receive-view").style.display = "block";
    }

    if (view === "send") {
        document.getElementById("send-view").style.display = "block";
        loadSendView();
    }

    if (view === "history") {
        document.getElementById("history-view").style.display = "block";
        loadTransactions();
    }

    setActiveMenu(view);
}

// Load and display available mints
function openMintConfirm(mint) {
    pendingMint = mint;
    loadMints();
}

async function loadMints() {
    const container = document.getElementById("mint-list");
    container.innerHTML = "Loading...";

    const res = await fetch("/api/mints");
    const data = await res.json();

    container.innerHTML = "";

    // Combine official and custom mints
    const allMints = [...data.mints, ...customMints];

    allMints.forEach(mint => {
        const div = document.createElement("div");
        div.className = "mint-item";
        const isCustom = customMints.some(m => m.url === mint.url);

        if (activeMint && activeMint.url === mint.url) {
            div.classList.add("selected");
        }

        const isPending = pendingMint && pendingMint.url === mint.url;

        if (isPending) {
            div.innerHTML = `
                <div class="mint-header">
                    <strong>${mint.name}</strong>
                    ${isCustom ? '<span class="mint-badge">Custom</span>' : ''}
                </div>
                <div class="mint-url">${mint.url}</div>
                <div class="mint-status">● ${mint.status}</div>
                <div class="mint-actions">
                    <button class="select" onclick="confirmSelectMint(event)">Select</button>
                    <button class="dismiss" onclick="dismissMint(event)">Dismiss</button>
                    ${isCustom ? `<button class="danger" onclick="removeCustomMint(event, '${mint.url}')">Delete</button>` : ''}
                </div>
            `;
        } else {
            div.innerHTML = `
                <div class="mint-header">
                    <strong>${mint.name}</strong>
                    ${isCustom ? '<span class="mint-badge">Custom</span>' : ''}
                </div>
                <div class="mint-url">${mint.url}</div>
                <div class="mint-status">● ${mint.status}</div>
                ${isCustom ? `<div class="mint-delete-btn" onclick="event.stopPropagation(); removeCustomMint(event, '${mint.url}')">Remove</div>` : ''}
            `;

            div.onclick = () => openMintConfirm(mint);
        }

        container.appendChild(div);
    });
}

// Handle minting confirmation
function confirmSelectMint(event) {
    event.stopPropagation();

    if (!pendingMint) return;

    activeMint = pendingMint;
    pendingMint = null;

    localStorage.setItem("activeMint", JSON.stringify(activeMint));

    updateActiveMintUI();
    showView("wallet");
}

function dismissMint(event) {
    event.stopPropagation();
    pendingMint = null;
    loadMints();
}

// -------- STORAGE --------
function loadStoredMint() {
    const stored = localStorage.getItem("activeMint");

    if (stored) {
        activeMint = JSON.parse(stored);
    }

    updateActiveMintUI();
}

// -------- UI --------
function updateActiveMintUI() {
    const container = document.querySelector(".active-mint");
    const nameEl = document.getElementById("active-mint-name");
    const sendMintBadge = document.getElementById("send-mint-badge");

    const banner = document.getElementById("selected-mint-banner");
    const bannerName = document.getElementById("selected-mint-banner-name");

    if (activeMint) {
        nameEl.innerText = activeMint.url;
        container.classList.add("active");

        banner.classList.remove("hidden");
        bannerName.innerText = activeMint.name;

        if (sendMintBadge) {
            sendMintBadge.innerText = activeMint.name || activeMint.url;
            sendMintBadge.classList.remove("none");
        }

    } else {
        nameEl.innerText = "None";
        container.classList.remove("active");

        banner.classList.add("hidden");

        if (sendMintBadge) {
            sendMintBadge.innerText = "No mint selected";
            sendMintBadge.classList.add("none");
        }

        const sendSats = document.getElementById("send-sats-available");
        const sendFiat = document.getElementById("send-fiat-available");
        if (sendSats) sendSats.innerText = "0 sats";
        if (sendFiat) sendFiat.innerHTML = "&asymp; $0.00";
    }
}

// -------- MODAL --------
function openDeleteModal() {
    if (!activeMint) return;
    document.getElementById("delete-modal").classList.add("active");
}

function closeDeleteModal() {
    document.getElementById("delete-modal").classList.remove("active");
}

function confirmDeleteMint() {
    activeMint = null;
    localStorage.removeItem("activeMint");

    updateActiveMintUI();
    closeDeleteModal();
}

// -------- HISTORY --------
async function loadTransactions() {
    const container = document.getElementById("tx-list");
    container.innerHTML = "Loading...";

    const res = await fetch("/api/transactions");
    const data = await res.json();

    container.innerHTML = "";

    if (data.transactions.length === 0) {
        container.innerHTML = "No transactions yet";
        return;
    }

    data.transactions.forEach(tx => {
        const div = document.createElement("div");
        div.className = "mint-item";

        const date = new Date(tx.timestamp * 1000);

        div.innerHTML = `
            <strong>${tx.type.toUpperCase()} ${tx.amount} sats</strong><br>
            <div class="mint-url">${tx.mint}</div>
            <div class="mint-status">${date.toLocaleString()}</div>
        `;

        container.appendChild(div);
    });
}

// Add custom mint from input fields
function addCustomMint() {
    const urlInput = document.getElementById("mint-url-input");
    const nameInput = document.getElementById("mint-name-input");
    
    const urlValue = urlInput.value.trim();
    const nameValue = nameInput.value.trim();
    
    // Validate inputs
    if (!urlValue) {
        alert("Please enter a mint URL");
        return;
    }
    
    if (!nameValue) {
        alert("Please enter a mint name");
        return;
    }
    
    // Construct full URL with https://
    const fullUrl = "https://" + urlValue;
    
    // Check if mint already exists
    const exists = customMints.some(m => m.url === fullUrl);
    if (exists) {
        alert("This mint URL already exists");
        return;
    }
    
    // Create custom mint object
    const customMint = {
        name: nameValue,
        url: fullUrl,
        status: "online"
    };
    
    // Add to custom mints list
    customMints.push(customMint);
    localStorage.setItem("customMints", JSON.stringify(customMints));
    
    // Set as active mint
    activeMint = customMint;
    localStorage.setItem("activeMint", JSON.stringify(activeMint));
    
    // Clear input fields
    urlInput.value = "";
    nameInput.value = "";
    
    // Update UI
    updateActiveMintUI();
    
    // Show success message
    alert(`Mint "${nameValue}" has been added successfully!`);
}

// Remove custom mint
function removeCustomMint(event, mintUrl) {
    event.stopPropagation();
    
    if (!confirm("Are you sure you want to remove this mint?")) {
        return;
    }
    
    // Remove from custom mints array
    customMints = customMints.filter(m => m.url !== mintUrl);
    localStorage.setItem("customMints", JSON.stringify(customMints));
    
    // If this was the active mint, clear it
    if (activeMint && activeMint.url === mintUrl) {
        activeMint = null;
        localStorage.removeItem("activeMint");
        updateActiveMintUI();
    }
    
    // Reload mints list
    loadMints();
}

// -------- SEND --------
let padVal = "0";

function loadSendView() {
    padVal = "0";
    document.getElementById("send-amount-display").innerText = "0";
    document.getElementById("send-status").innerText = "";
    document.getElementById("send-token-section").style.display = "none";

    const mintBadge = document.getElementById("send-mint-badge");
    if (activeMint) {
        mintBadge.innerText = activeMint.name || activeMint.url;
        mintBadge.classList.remove("none");
    } else {
        mintBadge.innerText = "No mint selected";
        mintBadge.classList.add("none");
        document.getElementById("send-sats-available").innerText = "0 sats";
        document.getElementById("send-fiat-available").innerHTML = "&asymp; $0.00";
        return;
    }

    fetch("/api/wallet/balance")
        .then(r => r.json())
        .then(d => {
            const sats = d.balance || 0;
            document.getElementById("send-sats-available").innerText = sats + " sats";
            if (currentPrice && currentPrice[currency]) {
                const btc = sats / 100000000;
                const fiat = btc * currentPrice[currency];
                const sym = currency === "usd" ? "$" : "\u20ac";
                document.getElementById("send-fiat-available").innerText = "\u2248 " + sym + fiat.toFixed(2);
            }
        });
}

function padInput(d) {
    if (padVal === "0") padVal = d;
    else if (padVal.length < 12) padVal += d;
    document.getElementById("send-amount-display").innerText = padVal;
}

function padClear() {
    padVal = "0";
    document.getElementById("send-amount-display").innerText = "0";
}

function padBack() {
    padVal = padVal.length <= 1 ? "0" : padVal.slice(0, -1);
    document.getElementById("send-amount-display").innerText = padVal;
}

async function doSend() {
    const amt = parseInt(padVal);
    const st = document.getElementById("send-status");
    const btn = document.getElementById("send-go-btn");

    st.innerText = "";
    st.style.color = "";

    if (!activeMint) { st.innerText = "Select a mint first"; st.style.color = "#f87171"; return; }
    if (amt <= 0) { st.innerText = "Enter an amount"; st.style.color = "#f87171"; return; }

    btn.disabled = true; btn.innerText = "Sending...";
    st.innerText = "Processing..."; st.style.color = "#93c5fd";

    try {
        const res = await fetch("/api/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount: amt, mint: activeMint.url })
        });
        const data = await res.json();

        if (data.token) {
            st.innerText = "Token created!"; st.style.color = "#22c55e";
            document.getElementById("send-token-out").value = data.token;
            document.getElementById("send-token-section").style.display = "block";
            padVal = "0";
            document.getElementById("send-amount-display").innerText = "0";
            await loadBalance();
            document.getElementById("send-sats-available").innerText = document.getElementById("balance").textContent;
            document.getElementById("send-fiat-available").innerText = document.getElementById("fiat-value").textContent;
        } else {
            st.innerText = data.error || "Error"; st.style.color = "#f87171";
        }
    } catch (e) {
        st.innerText = "Network error"; st.style.color = "#f87171";
    } finally {
        btn.disabled = false; btn.innerText = "Send";
    }
}

function copyToken() {
    navigator.clipboard.writeText(document.getElementById("send-token-out").value)
        .then(() => { alert("Copied!"); });
}

// -------- INIT --------
function init() {
    loadCurrency();
    loadPrice();
    loadBalance();
    loadStoredMint();
    setActiveMenu("wallet");

    setInterval(loadPrice, 900000);
}

init();