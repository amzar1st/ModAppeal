const CONTRACT_ADDRESS = "0x5f4d4256736DC7B9288F4c02796c6A4c1b4B47c2";
const CHAIN_ID = 61999;
const RPC_URL = "https://studio.genlayer.com/api";
const EXPLORER_URL = "https://explorer-studio.genlayer.com";

const state = {
  sdk: null,
  chains: null,
  types: null,
  readClient: null,
  provider: null,
  account: null,
  cases: [],
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function log(message, kind = "") {
  const target = $("#actionLog");
  target.textContent = message;
  target.className = `action-log ${kind}`.trim();
}

function setNotice(message, kind = "") {
  const target = $("#liveNotice");
  target.innerHTML = `<span class="notice-icon">${kind === "error" ? "!" : "i"}</span><span>${message}</span>`;
}

function humanAddress(address) {
  return address ? `${address.slice(0, 6)}…${address.slice(-4)}` : "—";
}

function weiToGen(value) {
  try {
    const wei = BigInt(value ?? 0);
    const whole = wei / 1000000000000000000n;
    const fraction = (wei % 1000000000000000000n).toString().padStart(18, "0").slice(0, 3);
    return `${whole}.${fraction} GEN`;
  } catch {
    return "—";
  }
}

function hashLooksValid(value) {
  return /^[0-9a-f]{64}$/i.test(String(value || "").trim());
}

async function loadSdk() {
  if (state.sdk) return state.sdk;
  const [sdk, chains, types] = await Promise.all([
    import("https://esm.sh/genlayer-js@1.1.8?target=es2022"),
    import("https://esm.sh/genlayer-js@1.1.8/chains?target=es2022"),
    import("https://esm.sh/genlayer-js@1.1.8/types?target=es2022"),
  ]);
  state.sdk = sdk;
  state.chains = chains;
  state.types = types;
  state.readClient = sdk.createClient({ chain: chains.studionet });
  return sdk;
}

function requireDeployment() {
  if (!CONTRACT_ADDRESS) throw new Error("The public app is waiting for the first ModAppeal deployment.");
  return CONTRACT_ADDRESS;
}

async function ensureNetwork() {
  if (!state.provider) throw new Error("Connect a wallet before signing a write.");
  const chainId = `0x${CHAIN_ID.toString(16)}`;
  const current = await state.provider.request({ method: "eth_chainId" });
  if (String(current).toLowerCase() === chainId.toLowerCase()) return;
  try {
    await state.provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId }] });
  } catch (error) {
    if (Number(error?.code) !== 4902) throw error;
    await state.provider.request({
      method: "wallet_addEthereumChain",
      params: [{
        chainId,
        chainName: "GenLayer Studionet",
        rpcUrls: [RPC_URL],
        nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
        blockExplorerUrls: [EXPLORER_URL],
      }],
    });
  }
}

async function readContract(functionName, args = []) {
  await loadSdk();
  return state.readClient.readContract({
    address: requireDeployment(),
    functionName,
    args,
    transactionHashVariant: state.types.TransactionHashVariant.LATEST_FINAL,
  });
}

async function writeContract(functionName, args = [], value = 0n) {
  await loadSdk();
  await ensureNetwork();
  if (!state.account) throw new Error("Connect a wallet before signing a write.");
  const client = state.sdk.createClient({ chain: state.chains.studionet, account: state.account, provider: state.provider });
  const hash = await client.writeContract({ address: requireDeployment(), functionName, args, value });
  log(`Submitted ${functionName} · ${String(hash).slice(0, 12)}… waiting for finality`);
  const receipt = await state.readClient.waitForTransactionReceipt({
    hash,
    status: state.types.TransactionStatus.FINALIZED,
    interval: 3000,
    retries: 120,
  });
  if (receipt.txExecutionResultName !== state.types.ExecutionResult.FINISHED_WITH_RETURN) {
    throw new Error(`Execution ended as ${receipt.txExecutionResultName || "NOT_VOTED"}.`);
  }
  log(`Finalized ${functionName} · ${String(hash).slice(0, 12)}…`, "success");
  return { hash, receipt };
}

function statusMarkup(status) {
  const cls = status === "FINALIZED" ? "finalized" : status === "APPEAL_OPEN" ? "open" : "recorded";
  return `<span class="status-label ${cls}">${String(status || "UNKNOWN").replaceAll("_", " ")}</span>`;
}

function verdictMarkup(verdict) {
  if (!verdict) return "<span class=\"verdict-label\">—</span>";
  const cls = verdict.includes("OVERTURNED") ? "overturned" : verdict.includes("CONFIRMED") ? "confirmed" : verdict.includes("PARTIAL") ? "partial" : "";
  return `<span class="verdict-label ${cls}">${String(verdict).replaceAll("_", " ")}</span>`;
}

function renderCases(cases) {
  state.cases = cases;
  const body = $("#caseRows");
  if (!cases.length) {
    body.innerHTML = `<tr><td colspan="6" class="empty-cell">No live cases have been read from the finalized contract.</td></tr>`;
    return;
  }
  body.innerHTML = cases.map((item) => `
    <tr>
      <td>${item.case_id || "—"}</td>
      <td>${item.community_id || "—"}</td>
      <td>${item.action_type || "—"}</td>
      <td>${statusMarkup(item.status)}</td>
      <td>${verdictMarkup(item.verdict)}</td>
      <td><button class="row-action" data-read-case="${item.case_id}">Inspect ↗</button></td>
    </tr>
  `).join("");
  $$('[data-read-case]').forEach((button) => button.addEventListener("click", () => {
    $("#readCaseId").value = button.dataset.readCase;
    $("#readCase").click();
    $("#protocol").scrollIntoView({ behavior: "smooth", block: "start" });
  }));
}

async function refresh() {
  if (!CONTRACT_ADDRESS) {
    $("#networkStatus").textContent = "PENDING DEPLOYMENT";
    $("#networkStatus").style.color = "var(--orange)";
    setNotice("The interface is ready. Add the deployed ModAppeal address to enable canonical reads and wallet actions.");
    renderCases([]);
    return;
  }
  try {
    await loadSdk();
    const [stats, ids] = await Promise.all([
      readContract("get_protocol_stats"),
      readContract("get_case_ids"),
    ]);
    $("#statCommunities").textContent = String(stats.total_communities ?? "0");
    $("#statCases").textContent = String(stats.total_cases ?? "0");
    $("#statAppeals").textContent = String(stats.total_appeals ?? "0");
    $("#statActive").textContent = String(stats.active_appeals ?? "0");
    const caseIds = Array.isArray(ids) ? ids : [];
    const cases = await Promise.all(caseIds.slice(-24).map((id) => readContract("get_case", [String(id)])));
    renderCases(cases.reverse());
    $("#networkStatus").textContent = "FINALIZED STATE";
    setNotice(`Live reads are sourced from LATEST_FINAL · ${cases.length} case${cases.length === 1 ? "" : "s"} indexed.`);
  } catch (error) {
    setNotice(error?.message || "The finalized contract state could not be read.", "error");
    log(error?.message || "Live read failed.", "error");
  }
}

async function connectWallet() {
  try {
    await loadSdk();
    state.provider = window.ethereum;
    if (!state.provider) throw new Error("No injected wallet was found. Open the app in a wallet-enabled browser.");
    const accounts = await state.provider.request({ method: "eth_requestAccounts" });
    state.account = accounts?.[0] || null;
    if (!state.account) throw new Error("The wallet returned no account.");
    const button = $("#connectWallet");
    button.textContent = humanAddress(state.account);
    button.classList.add("connected");
    log(`Wallet connected: ${state.account}`, "success");
  } catch (error) {
    log(error?.message || "Wallet connection failed.", "error");
  }
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

$("#connectWallet").addEventListener("click", connectWallet);
$("#refreshCases").addEventListener("click", refresh);
$$('[data-scroll]').forEach((button) => button.addEventListener("click", () => $(button.dataset.scroll).scrollIntoView({ behavior: "smooth" })));

$$('.tab').forEach((tab) => tab.addEventListener("click", () => {
  $$('.tab').forEach((item) => item.classList.toggle("active", item === tab));
  $$('.tool-form').forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === tab.dataset.tab));
  $(".setup-subforms").style.display = tab.dataset.tab === "setup" ? "grid" : "none";
}));

$("#setupForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    await writeContract("create_community", [data.communityId, data.name, data.description]);
    await refresh();
  } catch (error) { log(error?.message || "Community creation failed.", "error"); }
});

$("#policyForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  if (!hashLooksValid(data.sha256)) return log("Use a lowercase or uppercase 64-character SHA-256 fingerprint.", "error");
  try {
    await writeContract("publish_policy", [data.communityId, Number(data.version), data.policyText, data.sha256]);
    await refresh();
  } catch (error) { log(error?.message || "Policy publication failed.", "error"); }
});

$("#moderatorForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    await writeContract("register_moderator", [data.communityId, data.moderator]);
    log("Moderator registration finalized.", "success");
  } catch (error) { log(error?.message || "Moderator registration failed.", "error"); }
});

$("#recordForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  if (!hashLooksValid(data.contentSha256)) return log("Use a 64-character SHA-256 content fingerprint.", "error");
  try {
    await writeContract("record_action", [data.caseId, data.communityId, data.subject, data.actionType, data.contentUrl, data.contentSha256, data.reason, Number(data.version)]);
    await refresh();
  } catch (error) { log(error?.message || "Moderation action recording failed.", "error"); }
});

$("#appealForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  const deadline = Math.floor(Date.now() / 1000) + Number(data.deadlineSeconds);
  const value = BigInt(Math.round(Number(data.bond) * 1e18));
  try {
    await writeContract("open_appeal", [data.caseId, deadline], value);
    await refresh();
  } catch (error) { log(error?.message || "Appeal opening failed.", "error"); }
});

async function submitEvidence(side) {
  const data = formData($("#evidenceForm"));
  if (!hashLooksValid(data.sha256)) return log("Use a 64-character SHA-256 evidence fingerprint.", "error");
  try {
    await writeContract(side === "moderator" ? "submit_counter_evidence" : "submit_evidence", [data.caseId, data.url, data.sha256, data.note]);
    await refresh();
  } catch (error) { log(error?.message || "Evidence submission failed.", "error"); }
}

$("#evidenceForm").addEventListener("submit", async (event) => { event.preventDefault(); await submitEvidence("appellant"); });
$("#counterEvidence").addEventListener("click", async () => { await submitEvidence("moderator"); });

async function settle(action) {
  const data = formData($("#settleForm"));
  try {
    await writeContract(action, [data.caseId]);
    await refresh();
  } catch (error) { log(error?.message || `${action} failed.`, "error"); }
}

$("#settleForm").addEventListener("submit", async (event) => { event.preventDefault(); await settle("adjudicate"); });
$("#finalizeCase").addEventListener("click", async () => { await settle("finalize"); });
$("#claimBond").addEventListener("click", async () => { await settle("claim_bond"); });

$("#readCase").addEventListener("click", async () => {
  const id = $("#readCaseId").value.trim();
  if (!id) return;
  try {
    $("#readOutput").textContent = "Reading finalized state…";
    const [item, result, evidence] = await Promise.all([
      readContract("get_case", [id]),
      readContract("get_result", [id]),
      readContract("get_case_evidence", [id]),
    ]);
    $("#readOutput").textContent = JSON.stringify({ case: item, result, evidence }, null, 2);
  } catch (error) { $("#readOutput").textContent = error?.message || "Read failed."; }
});

refresh();
