const MAX_UI_MESSAGES = 200;

const elements = {
    clientsList: document.getElementById("clients-list"),
    messagesList: document.getElementById("messages-list"),
    clientsCount: document.getElementById("clients-count"),
    clientsUpdated: document.getElementById("clients-updated"),
    statClients: document.getElementById("stat-clients"),
    statClientsMeta: document.getElementById("stat-clients-meta"),
    statMessages: document.getElementById("stat-messages"),
    statRelations: document.getElementById("stat-relations"),
    statLast: document.getElementById("stat-last"),
    statusPill: document.getElementById("status-pill"),
    statusText: document.getElementById("status-text"),
    clearFeed: document.getElementById("clear-feed"),
};

const state = {
    clients: new Set(),
    messageCount: 0,
    relationCounts: new Map(),
    clientStats: new Map(),
    lastActivity: null,
};

function setStatus(online) {
    elements.statusPill.classList.toggle("online", online);
    elements.statusText.textContent = online ? "live" : "offline";
}

function formatTime(epochSeconds) {
    if (!epochSeconds) {
        return "--:--:--";
    }
    const ms = epochSeconds > 1e12 ? epochSeconds : epochSeconds * 1000;
    const date = new Date(ms);
    const hh = String(date.getHours()).padStart(2, "0");
    const mm = String(date.getMinutes()).padStart(2, "0");
    const ss = String(date.getSeconds()).padStart(2, "0");
    return `${hh}:${mm}:${ss}`;
}

function normalizeReceiver(receiver) {
    if (!receiver) {
        return "SERVER";
    }
    if (receiver === "ALL") {
        return "SERVER";
    }
    return receiver;
}

function pairKey(a, b) {
    if (!a || !b) {
        return null;
    }
    return [a, b].sort().join("|");
}

function sanitizePreview(value) {
    if (value === null || value === undefined) {
        return "";
    }
    if (typeof value === "string") {
        return value;
    }
    try {
        return JSON.stringify(value);
    } catch (err) {
        return String(value);
    }
}

function formatType(messageType, kind) {
    if (!messageType) {
        return kind.toUpperCase();
    }
    return messageType
        .replace("ENVOI_", "")
        .replace("RECEPTION_", "")
        .replace("ADMIN_", "")
        .replace(/_/g, " ")
        .toLowerCase();
}

function updateStats() {
    const clientsCount = state.clients.size;
    elements.statClients.textContent = clientsCount;
    elements.statClientsMeta.textContent = `${clientsCount} online`;
    elements.clientsCount.textContent = clientsCount;
    elements.statMessages.textContent = state.messageCount;
    elements.statRelations.textContent = state.relationCounts.size;
    elements.statLast.textContent = formatTime(state.lastActivity);
}

function updateClientsList() {
    const list = elements.clientsList;
    list.innerHTML = "";

    if (state.clients.size === 0) {
        const empty = document.createElement("li");
        empty.className = "client-item empty-state";
        empty.textContent = "No clients connected";
        list.appendChild(empty);
        return;
    }

    const clients = Array.from(state.clients).sort();
    for (const name of clients) {
        const stats = state.clientStats.get(name) || { messages: 0, lastSeen: null };
        const item = document.createElement("li");
        item.className = "client-item";

        const left = document.createElement("div");
        left.className = "client-left";

        const dot = document.createElement("span");
        dot.className = "client-dot";

        const label = document.createElement("div");
        label.className = "client-name";
        label.textContent = name;

        const right = document.createElement("div");
        right.className = "client-meta";
        const lastSeen = stats.lastSeen ? formatTime(stats.lastSeen / 1000) : "--:--:--";
        right.textContent = `${stats.messages} msgs | ${lastSeen}`;

        left.appendChild(dot);
        left.appendChild(label);

        item.appendChild(left);
        item.appendChild(right);
        list.appendChild(item);
    }
}

function updateClientStats(name) {
    const now = Date.now();
    const stats = state.clientStats.get(name) || { messages: 0, lastSeen: null };
    stats.messages += 1;
    stats.lastSeen = now;
    state.clientStats.set(name, stats);
}

function addMessageEntry(data) {
    const item = document.createElement("li");
    const kind = data.kind || "text";
    const messageType = formatType(data.message_type, kind);
    item.className = "message is-new";

    const meta = document.createElement("div");
    meta.className = "message-meta";

    const timeEl = document.createElement("span");
    timeEl.className = "mono";
    timeEl.textContent = formatTime(data.timestamp);

    const tag = document.createElement("span");
    tag.className = `message-tag tag-${kind}`;
    tag.textContent = messageType;

    meta.appendChild(timeEl);
    meta.appendChild(tag);

    const route = document.createElement("div");
    route.className = "message-route";
    const receiver = data.receiver || "-";
    route.textContent = `${data.emitter} -> ${receiver}`;

    const preview = document.createElement("div");
    preview.className = "message-preview";
    preview.textContent = sanitizePreview(data.value);

    item.appendChild(meta);
    item.appendChild(route);
    item.appendChild(preview);

    elements.messagesList.prepend(item);
    setTimeout(() => item.classList.remove("is-new"), 500);

    while (elements.messagesList.children.length > MAX_UI_MESSAGES) {
        elements.messagesList.removeChild(elements.messagesList.lastChild);
    }
}

// D3 graph setup
const graphWrap = document.querySelector(".graph-wrap");
const svg = d3.select("#graph");
const linkLayer = svg.append("g").attr("class", "links");
const nodeLayer = svg.append("g").attr("class", "nodes");
const labelLayer = svg.append("g").attr("class", "labels");

let width = 800;
let height = 400;

const simulation = d3.forceSimulation()
    .force("link", d3.forceLink().id(d => d.id).distance(d => d.kind === "presence" ? 150 : 220))
    .force("charge", d3.forceManyBody().strength(-420))
    .force("center", d3.forceCenter(width / 2, height / 2));

let linkElements = linkLayer.selectAll("line");
let nodeElements = nodeLayer.selectAll("circle");
let labelElements = labelLayer.selectAll("text");

function updateGraphSize() {
    const rect = graphWrap.getBoundingClientRect();
    width = Math.max(300, rect.width);
    height = Math.max(280, rect.height);
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    simulation.force("center", d3.forceCenter(width / 2, height / 2));
}

function buildGraphData() {
    const nodeNames = new Set(["SERVER"]);
    for (const name of state.clients) {
        nodeNames.add(name);
    }
    for (const key of state.relationCounts.keys()) {
        const parts = key.split("|");
        nodeNames.add(parts[0]);
        nodeNames.add(parts[1]);
    }

    const nodes = Array.from(nodeNames).map(id => {
        let type = "client";
        if (id === "SERVER") {
            type = "server";
        } else if (id.toUpperCase().startsWith("ADMIN")) {
            type = "admin";
        }
        return { id, type };
    });

    const presenceLinks = Array.from(state.clients).map(name => ({
        source: name,
        target: "SERVER",
        kind: "presence",
        count: 1,
        key: `presence|${name}|SERVER`,
    }));

    const trafficLinks = Array.from(state.relationCounts.entries()).map(([key, count]) => {
        const parts = key.split("|");
        return {
            source: parts[0],
            target: parts[1],
            kind: "traffic",
            count,
            key: `traffic|${key}`,
        };
    });

    return { nodes, links: presenceLinks.concat(trafficLinks) };
}

function updateGraph() {
    const graphData = buildGraphData();

    linkElements = linkLayer.selectAll("line").data(graphData.links, d => d.key);
    linkElements.exit().remove();
    const linkEnter = linkElements.enter().append("line");
    linkElements = linkEnter.merge(linkElements)
        .attr("class", d => d.kind)
        .attr("stroke-width", d => d.kind === "traffic" ? Math.min(5, 1.5 + d.count * 0.3) : 1.5);

    nodeElements = nodeLayer.selectAll("circle").data(graphData.nodes, d => d.id);
    nodeElements.exit().remove();
    const nodeEnter = nodeElements.enter()
        .append("circle")
        .attr("r", d => d.type === "server" ? 24 : 18)
        .attr("class", d => d.type)
        .call(drag(simulation));
    nodeElements = nodeEnter.merge(nodeElements)
        .attr("r", d => d.type === "server" ? 24 : 18)
        .attr("class", d => d.type);

    labelElements = labelLayer.selectAll("text").data(graphData.nodes, d => d.id);
    labelElements.exit().remove();
    const labelEnter = labelElements.enter()
        .append("text")
        .attr("text-anchor", "middle")
        .attr("dy", 4);
    labelElements = labelEnter.merge(labelElements)
        .text(d => d.id);

    simulation.nodes(graphData.nodes).on("tick", ticked);
    simulation.force("link").links(graphData.links);
    simulation.alpha(0.9).restart();
}

function ticked() {
    linkElements
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

    nodeElements
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);

    labelElements
        .attr("x", d => d.x)
        .attr("y", d => d.y);
}

function drag(simulationRef) {
    function dragStarted(event, d) {
        if (!event.active) simulationRef.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragEnded(event, d) {
        if (!event.active) simulationRef.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    return d3.drag().on("start", dragStarted).on("drag", dragged).on("end", dragEnded);
}

function flashLink(a, b) {
    const key = pairKey(a, b);
    if (!key) {
        return;
    }
    linkLayer.selectAll("line")
        .filter(d => d.key === `traffic|${key}`)
        .classed("flash", true)
        .transition()
        .duration(900)
        .on("end", function () {
            d3.select(this).classed("flash", false);
        });
}

function handleClientsUpdate(clients) {
    state.clients = new Set(clients);
    for (const name of state.clients) {
        if (!state.clientStats.has(name)) {
            state.clientStats.set(name, { messages: 0, lastSeen: null });
        }
    }
    for (const name of Array.from(state.clientStats.keys())) {
        if (!state.clients.has(name)) {
            state.clientStats.delete(name);
        }
    }
    elements.clientsUpdated.textContent = formatTime(Date.now() / 1000);
    updateClientsList();
    updateStats();
    updateGraph();
}

function handleMessage(data) {
    if (typeof data.id === "number") {
        state.messageCount = Math.max(state.messageCount, data.id);
    } else {
        state.messageCount += 1;
    }

    state.lastActivity = data.timestamp || Date.now() / 1000;

    const emitter = data.emitter || "unknown";
    const receiver = normalizeReceiver(data.receiver);
    updateClientStats(emitter);
    if (receiver && receiver !== "SERVER") {
        updateClientStats(receiver);
    }

    const key = pairKey(emitter, receiver);
    if (key) {
        const prev = state.relationCounts.get(key) || 0;
        state.relationCounts.set(key, prev + 1);
    }

    addMessageEntry(data);
    updateStats();
    updateClientsList();
    updateGraph();
    flashLink(emitter, receiver);
}

if (elements.clearFeed) {
    elements.clearFeed.addEventListener("click", () => {
        elements.messagesList.innerHTML = "";
    });
}

const evtSource = new EventSource("/stream");

evtSource.onopen = () => setStatus(true);

// Some browsers fire onerror on disconnect and reconnect attempts
evtSource.onerror = () => setStatus(false);

evtSource.onmessage = event => {
    const data = JSON.parse(event.data);
    if (data.type === "clients") {
        handleClientsUpdate(data.clients || []);
    }
    if (data.type === "message") {
        handleMessage(data);
    }
};

updateGraphSize();
updateGraph();

const resizeObserver = new ResizeObserver(() => {
    updateGraphSize();
    simulation.alpha(0.6).restart();
});

resizeObserver.observe(graphWrap);
