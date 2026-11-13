const $ = (id) => document.getElementById(id);
let selected, original, sequence = 0;
const node = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};

async function api(url, body) {
  const response = await fetch(url, body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)
  });
  if (!response.ok) {
    const detail = (await response.json()).detail;
    throw new Error(typeof detail === "string" ? detail : "Check the claim and try again.");
  }
  return response.json();
}

function drawChart(events, cricket) {
  const values = events.filter((item) => item.value !== null).map((item) => item.value);
  $("chart").replaceChildren();
  if (!values.length) return;
  const title = cricket ? "Required run rate" : "Pit-lane transit (seconds)";
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 600 108");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", title);
  const max = Math.max(...values, 1);
  if (cricket) {
    const line = document.createElementNS(svg.namespaceURI, "polyline");
    line.setAttribute("points", values.map((v, i) =>
      `${12 + 576 * i / Math.max(values.length - 1, 1)},${98 - 88 * v / max}`).join(" "));
    line.setAttribute("stroke", "#ad401e");
    line.setAttribute("stroke-width", "3");
    line.setAttribute("fill", "none");
    svg.append(line);
  } else {
    values.forEach((v, i) => {
      const bar = document.createElementNS(svg.namespaceURI, "rect");
      Object.entries({x: 36 + i * 190, y: 98 - 88 * v / max, width: 145,
        height: 88 * v / max, fill: ["#ad401e", "#377470", "#353634"][i % 3]})
        .forEach(([key, value]) => bar.setAttribute(key, value));
      svg.append(bar);
    });
  }
  $("chart").append(node("p", title, "chart-label"), svg);
}

async function select(item, level = 1, keepClaim = false) {
  const request = ++sequence;
  selected = item;
  original = null;
  $("challenge").hidden = true;
  $("results").replaceChildren();
  $("events").replaceChildren();
  $("chart").replaceChildren();
  $("sources").replaceChildren();
  $("run").disabled = true;
  $("status").textContent = "Loading case…";
  $("domain").textContent = item.domain;
  $("title").textContent = item.title;
  $("subtitle").textContent = item.subtitle;
  if (!keepClaim) $("claim").value = item.claim;
  $("reveal").checked = level === 2;
  $("spoiler").hidden = item.domain !== "Adaptations";
  for (const button of $("cases").children) {
    button.setAttribute("aria-pressed", String(button.dataset.id === item.id));
  }
  try {
    const data = await api(`/api/cases/${item.id}?level=${level}`);
    if (request !== sequence) return;
    $("count").textContent = `${data.events.length} RECORDS`;
    $("events").replaceChildren(...data.events.map((event) => {
      const li = node("li");
      li.id = `event-${event.id}`;
      li.tabIndex = -1;
      const detail = node("div");
      detail.append(node("small", event.lane), node("span", event.text));
      li.append(node("strong", event.label), detail);
      return li;
    }));
    drawChart(data.events, item.domain === "Cricket");
    for (const [label, url] of [[data.source, data.url], ...data.links]) {
      const a = node("a", label);
      a.href = url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      $("sources").append(a);
    }
    $("status").textContent = "";
    $("run").disabled = false;
  } catch (error) {
    if (request === sequence) $("status").textContent = error.message;
  }
}

function show(result) {
  const panel = node("article");
  const review = Boolean(result.parent_id);
  panel.append(node("h3", `${review ? "Opposing case" : "Verdict"}: ${result.verdict}`));
  panel.append(node("p", result.rationale));
  if (review) panel.append(node("p", result.changed ? "Verdict revised." : "Verdict unchanged."));
  for (const [heading, facts] of [["Supporting evidence", result.supporting],
    ["Conflicting evidence", result.conflicting]]) {
    if (!facts.length) continue;
    panel.append(node("strong", heading));
    const list = node("ul");
    for (const fact of facts) {
      const row = node("li", fact.text);
      for (const ref of fact.refs) {
        const target = $(`event-${ref}`);
        if (!target) continue;
        const link = node("button", target.firstChild.textContent, "citation");
        link.type = "button";
        link.onclick = () => {
          document.querySelector("#events .active")?.classList.remove("active");
          target.classList.add("active");
          target.focus({preventScroll:true});
          target.scrollIntoView({block: "nearest"});
        };
        row.append(link);
      }
      list.append(row);
    }
    panel.append(list);
  }
  panel.append(node("p", result.limitations));
  panel.append(node("small", `${result.model} · ${result.tools.length} tools · ${result.latency_ms} ms`));
  $("results").append(panel);
}

async function run(review) {
  const request = ++sequence;
  $("run").disabled = $("challenge").disabled = true;
  $("status").textContent = review ? "Testing the opposing case…" : "Gathering evidence…";
  if (!review) {
    original = null;
    $("challenge").hidden = true;
    $("results").replaceChildren();
  }
  try {
    const result = review
      ? await api(`/api/investigations/${original}/challenge`, null)
      : await api(`/api/cases/${selected.id}/investigations`, {
        claim: $("claim").value, level: $("reveal").checked ? 2 : 1
      });
    if (request !== sequence) return;
    if (!review) original = result.id;
    show(result);
    $("challenge").hidden = review;
    $("status").textContent = "";
  } catch (error) {
    if (request === sequence) $("status").textContent = error.message;
  } finally {
    if (request === sequence) $("run").disabled = $("challenge").disabled = false;
  }
}

$("form").onsubmit = (event) => { event.preventDefault(); run(false); };
$("challenge").onclick = () => run(true);
$("reveal").onchange = () => select(selected, $("reveal").checked ? 2 : 1, true);
try {
  const items = await api("/api/cases");
  for (const item of items) {
    const button = node("button", item.domain);
    button.dataset.id = item.id;
    button.onclick = () => select(item);
    $("cases").append(button);
  }
  if (items.length) await select(items[0]);
} catch (error) {
  $("status").textContent = error.message;
}
