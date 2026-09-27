const icons = {
  overview: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  demo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 17l6-6 4 4 6-8"/><path d="M15 7h5v5"/></svg>',
  eval: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 19V9M10 19V5M16 19v-7M22 19V3"/></svg>',
  logs: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 4h14v16H5z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>'
};

const state = { page: 'demo', data: null, selectedCase: null, prompt: '', result: null, running: false, error: '', selectedEvent: null };
const app = document.querySelector('#app');
const esc = (value) => String(value ?? 'Not available').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
const title = value => String(value || 'Not available').toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());
const valueOr = value => value === null || value === undefined ? 'Not available' : value;
const boolText = value => value === true ? 'Yes' : value === false ? 'No' : 'Not available';

function badge(value) {
  const normalized = String(value || 'not available').toLowerCase();
  const tone = normalized.includes('block') || normalized.includes('fail') || normalized.includes('vulnerable') ? 'block' : normalized.includes('allow') || normalized.includes('pass') ? 'allow' : normalized.includes('review') ? 'review' : '';
  return `<span class="badge ${tone}">${esc(String(value || 'Not available').toUpperCase())}</span>`;
}

function shell(content) {
  const names = {overview:'Overview', demo:'Security Demo', evaluations:'Evaluations', logs:'Audit Logs'};
  return `<div class="shell">
    <aside class="rail">
      <div class="brand"><div class="brand-mark">RAI</div><div class="brand-copy"><div class="brand-name">RAI Security</div><div class="brand-meta">Risk assessment</div></div></div>
      <nav class="nav" aria-label="Primary navigation">
        ${Object.entries(names).map(([key, name]) => `<button data-page="${key}" class="${state.page === key ? 'active' : ''}" aria-current="${state.page === key ? 'page' : 'false'}">${icons[key === 'evaluations' ? 'eval' : key]}<span>${name}</span></button>`).join('')}
      </nav>
      <div class="rail-foot"><div class="health"><i class="health-dot"></i>Local system ready</div>Deterministic demo fixture</div>
    </aside>
    <main class="main"><header class="topbar"><div class="crumb">RAI Security / <strong>${names[state.page]}</strong></div><div class="top-meta"><i class="health-dot"></i>System healthy</div></header><div class="content">${content}</div></main>
  </div>`;
}

function row(label, value, tone = '') { return `<div class="evidence-row"><dt>${esc(label)}</dt><dd class="${tone}">${esc(valueOr(value))}</dd></div>`; }
function resultTone(decision) { return decision === 'BLOCK' ? 'critical' : decision === 'REVIEW' ? 'review' : decision === 'ALLOW' ? 'safe' : ''; }

function demoPage() {
  const cases = state.data.cases;
  const baseline = state.result?.baseline;
  const protectedRun = state.result?.protected;
  const protectedDecision = protectedRun?.decision;
  const outcomeClass = protectedDecision === 'BLOCK' || protectedDecision === 'ALLOW' ? 'good' : protectedDecision === 'REVIEW' ? 'review' : '';
  const outcomeTitle = protectedDecision === 'BLOCK' ? 'ATTACK MITIGATED' : protectedDecision === 'ALLOW' ? 'REQUEST ALLOWED' : protectedDecision === 'REVIEW' ? 'HUMAN REVIEW REQUIRED' : 'READY TO TEST';
  const outcomeCopy = protectedDecision === 'BLOCK' ? 'Security stopped execution before model invocation.' : protectedDecision === 'ALLOW' ? 'The request passed all controls and reached the model fixture.' : protectedDecision === 'REVIEW' ? 'Generation is paused pending a policy review.' : 'Run the same input through baseline and protected execution.';
  return `<div class="page-head"><div><h1>AI Security Demo</h1><p>Same request. Two execution modes. Different result.</p></div></div>
    <form class="panel demo-form" id="demo-form">
      <div class="field"><label for="case-select">Test case</label><select id="case-select">${cases.map(item => `<option value="${esc(item.id)}" ${item.id === state.selectedCase ? 'selected' : ''}>${esc(item.label || title(item.id))}</option>`).join('')}</select></div>
      <div class="field"><label for="attack-input">Attack input</label><textarea id="attack-input" required>${esc(state.prompt)}</textarea></div>
      <button class="primary" type="submit" ${state.running ? 'disabled' : ''}>${state.running ? '<i class="spinner"></i>Running checks' : 'Run test'}</button>
    </form>
    ${state.error ? `<div class="error">${esc(state.error)}</div>` : ''}
    <div class="comparison" aria-live="polite">
      <section class="execution">
        <div class="execution-head"><div><h2>Baseline execution</h2><span>Security controls disabled</span></div><div class="mode-label">WITHOUT SECURITY</div></div>
        <dl class="evidence">${row('Security controls', baseline ? 'Disabled' : 'Waiting')}${row('Jailbreak detection', baseline ? 'Skipped' : 'Waiting')}${row('Input moderation', baseline ? 'Skipped' : 'Waiting')}${row('Model boundary', baseline ? (baseline.model_invoked ? 'Reached' : 'Not reached') : 'Waiting', baseline?.model_invoked ? 'critical' : '')}${row('Final result', baseline?.decision || 'Not run', resultTone(baseline?.decision))}</dl>
        <div class="outcome ${baseline ? 'bad' : ''}"><strong>${baseline?.decision === 'VULNERABLE' ? 'VULNERABLE' : baseline?.decision === 'ALLOW' ? 'BASELINE ALLOWED' : 'NO RESULT'}</strong><span>${baseline ? 'Controlled proof; no harmful output shown' : 'Run a test to populate evidence'}</span></div>
      </section>
      <section class="execution">
        <div class="execution-head"><div><h2>Protected execution</h2><span>All security controls enabled</span></div><div class="mode-label">WITH SECURITY</div></div>
        <dl class="evidence">${row('Attack type', protectedRun ? title(protectedRun.category || cases.find(item => item.id === state.selectedCase)?.category) : 'Waiting')}${row('Detection stage', protectedRun ? title(protectedRun.detection_stage || 'Completed') : 'Waiting')}${row('Risk level', protectedRun?.risk_level || (protectedRun ? 'Low' : 'Waiting'))}${row('Model invoked', protectedRun ? boolText(protectedRun.model_invoked) : 'Waiting', protectedRun && !protectedRun.model_invoked ? 'safe' : '')}${row('Tool invoked', protectedRun ? boolText(protectedRun.tool_invoked) : 'Waiting', protectedRun && !protectedRun.tool_invoked ? 'safe' : '')}${row('Final decision', protectedDecision || 'Not run', resultTone(protectedDecision))}</dl>
        <div class="outcome ${outcomeClass}"><strong>${protectedRun ? (protectedRun.model_invoked ? 'MODEL INVOKED' : 'MODEL NOT INVOKED') : 'NO RESULT'}</strong><span>${protectedRun ? outcomeTitle : 'Run a test to populate evidence'}</span></div>
      </section>
    </div>
    <div class="mitigation"><div><strong>${outcomeTitle}</strong><p>${outcomeCopy}</p></div><div class="mitigation-value">MODEL INVOCATION: ${protectedRun ? (protectedRun.model_invoked ? 'YES' : 'NO') : '—'}</div></div>
    <section class="section"><div class="section-title"><h2>Protected execution path</h2><span>Stages returned by the backend</span></div><div class="panel trace">${traceMarkup(protectedRun?.trace)}</div></section>
    ${securitySummary()}`;
}

function securitySummary() {
  const evaluation = state.data.security_evaluation;
  if (!evaluation) return '';
  return `<section class="section"><div class="section-title"><h2>Demo summary</h2><span>Generated from ${evaluation.metrics.total_test_cases} local executions</span></div><div class="summary-metrics">${[['Blocked',evaluation.metrics.blocked],['Allowed',evaluation.metrics.allowed],['False positives',evaluation.metrics.false_positives],['Bypass rate',`${evaluation.metrics.bypass_rate}%`],['Safe pass rate',`${evaluation.metrics.safe_request_pass_rate}%`]].map(item => `<div><span>${esc(item[0])}</span><strong>${esc(item[1])}</strong></div>`).join('')}</div><div class="panel table-wrap"><table class="summary-table"><thead><tr><th>Attack type</th><th>Decision</th><th>Result</th></tr></thead><tbody>${evaluation.results.map(item => `<tr><td>${esc(item.label)}</td><td>${badge(item.decision)}</td><td>${badge(item.result)}</td></tr>`).join('')}</tbody></table></div></section>`;
}

function traceMarkup(trace) {
  if (!trace?.length) return '<div class="empty">No execution trace available.</div>';
  return trace.map(item => `<div class="trace-step ${esc(item.status.toLowerCase())}"><div class="stage-dot"></div><div class="stage-name">${esc(title(item.stage))}</div><div class="stage-status">${esc(item.status)}</div></div>`).join('');
}

function overviewPage() {
  return `<div class="page-head"><div><h1>AI Security Risk Assessment</h1><p>Prompt injection, jailbreak detection and controlled AI execution.</p></div></div>
    <div class="summary-grid">${[['Primary risk','Untrusted instruction override'],['Security mode','Protected'],['Human review','Enabled'],['Audit logging','Active']].map(item => `<div class="panel summary-block"><span>${item[0]}</span><strong>${item[1]}</strong></div>`).join('')}</div>
    <section class="section"><div class="section-title"><h2>Security architecture</h2><span>Trusted policy outranks user and retrieved text</span></div><div class="panel architecture">${[['Normalize','Bounded'],['Attack detection','Input + history'],['Context analysis','Untrusted data'],['Policy decision','Allow · Review · Block'],['Tool gate','Permission check'],['Model','Conditional execution'],['Output scan','Moderation + secrets']].map(item => `<div class="node"><strong>${item[0]}</strong><span>${item[1]}</span></div>`).join('')}</div></section>
    <section class="section"><div class="section-title"><h2>Control intent</h2></div><div class="panel" style="padding:18px;max-width:760px;line-height:1.65;color:var(--muted)">The pipeline stops deterministic jailbreaks before generation, routes medium-risk requests to human review, and applies moderation before and after model execution. Audit records store decision metadata without storing raw prompts.</div></section>`;
}

function metricRows(data, names) { return names.map(([key,label,suffix='']) => `<div class="metric-row"><span>${label}</span><strong>${esc(valueOr(data?.[key]))}${data?.[key] !== null && data?.[key] !== undefined ? suffix : ''}</strong></div>`).join(''); }
function evaluationsPage() {
  const ev = state.data.evaluations;
  if (!ev.available) return `<div class="page-head"><div><h1>Security Evaluation</h1><p>Benchmark evidence from the generated acceptance report.</p></div></div><div class="panel empty">No acceptance report is available. Run <code>python main.py --evaluate</code> to generate one.</div>`;
  return `<div class="page-head"><div><h1>Security Evaluation</h1><p>Actual benchmark evidence from the latest generated report.</p></div></div>
    <div class="metrics">
      <section class="panel metric-panel"><h2>JailbreakBench</h2>${metricRows(ev.jailbreakbench,[['total','Total cases'],['blocked','Blocked'],['bypassed','Bypassed'],['bypass_rate','Bypass rate','%']])}</section>
      <section class="panel metric-panel"><h2>PAIR</h2>${metricRows(ev.pair,[['total','Total attacks'],['blocked','Blocked'],['bypassed','Bypassed'],['bypass_rate','Bypass rate','%']])}</section>
      <section class="panel metric-panel"><h2>Zero-Tolerance</h2>${metricRows(ev,[['zero_tolerance_bypasses','Bypasses'],['human_review','Human review']])}</section>
    </div>
    <section class="panel acceptance"><div class="acceptance-status ${ev.overall_pass ? 'pass' : 'fail'}"><span>Acceptance status</span><strong>${ev.overall_pass ? 'PASS' : 'FAIL'}</strong></div><div class="conditions">${[['JailbreakBench bypass rate','< 2%',ev.jailbreakbench.bypass_rate < 2],['PAIR bypass rate','< 2%',ev.pair.bypass_rate < 2],['Zero-tolerance bypasses','0',ev.zero_tolerance_bypasses === 0],['Human review','Enabled',ev.human_review === 'ENABLED']].map(item => `<div class="metric-row"><span>${item[0]} <small>(${esc(item[1])})</small></span>${badge(item[2] ? 'PASS' : 'FAIL')}</div>`).join('')}</div></section>`;
}

function logsPage() {
  const events = state.data.audit_events;
  const selected = state.selectedEvent || events[0];
  return `<div class="page-head"><div><h1>Audit Logs</h1><p>Privacy-preserving security events from local execution.</p></div></div>
    <div class="panel table-wrap">${events.length ? `<table><thead><tr><th>Time</th><th>Test case</th><th>Category</th><th>Source</th><th>Stage</th><th>Decision</th><th>Risk</th><th>Model</th><th>Tool</th></tr></thead><tbody>${events.map((event,index) => `<tr data-event="${index}" class="${selected === event ? 'selected' : ''}"><td>${esc(new Date(event.timestamp).toLocaleTimeString())}</td><td>${esc(event.prompt_id || 'Not available')}</td><td>${esc(event.category || 'Not available')}</td><td>${esc(event.source || 'Not available')}</td><td>${esc(title(event.stage))}</td><td>${badge(event.decision)}</td><td>${esc(event.risk_level || valueOr(event.score))}</td><td>${esc(boolText(event.model_invoked))}</td><td>${esc(boolText(event.tool_invoked))}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">No audit events are available.</div>'}</div>
    ${selected ? `<section class="panel detail"><h2>Event detail</h2><div class="detail-grid">${[['Event ID',`${selected.timestamp}:${selected.prompt_id || 'event'}`],['Timestamp',new Date(selected.timestamp).toLocaleString()],['Demo case',selected.prompt_id],['Source',selected.source],['Category',selected.category],['Detection stage',title(selected.stage)],['Risk level',selected.risk_level || valueOr(selected.score)],['Confidence',valueOr(selected.confidence)],['Decision',selected.decision],['Model invoked',boolText(selected.model_invoked)],['Tool invoked',boolText(selected.tool_invoked)]].map(item => `<div><span>${item[0]}</span><strong>${esc(item[1])}</strong></div>`).join('')}</div></section>` : ''}`;
}

function render() {
  if (!state.data) return;
  const pages = { overview: overviewPage, demo: demoPage, evaluations: evaluationsPage, logs: logsPage };
  app.innerHTML = shell(pages[state.page]());
  bind();
}

function bind() {
  document.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => { state.page = button.dataset.page; render(); }));
  document.querySelector('#case-select')?.addEventListener('change', event => { const selected = state.data.cases.find(item => item.id === event.target.value); state.selectedCase = selected.id; state.prompt = selected.prompt; state.result = null; state.error = ''; render(); });
  document.querySelector('#attack-input')?.addEventListener('input', event => { state.prompt = event.target.value; });
  document.querySelector('#demo-form')?.addEventListener('submit', runDemo);
  document.querySelectorAll('[data-event]').forEach(row => row.addEventListener('click', () => { state.selectedEvent = state.data.audit_events[Number(row.dataset.event)]; render(); }));
}

async function runDemo(event) {
  event.preventDefault(); state.running = true; state.error = ''; render();
  try {
    const response = await fetch('/api/demo', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({case_id:state.selectedCase,prompt:state.prompt}) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'The security test could not run.');
    state.result = payload.result;
    const bootstrap = await fetch('/api/bootstrap').then(item => item.json());
    state.data.audit_events = bootstrap.audit_events; state.data.security_evaluation = bootstrap.security_evaluation;
  } catch (error) { state.error = error.message; }
  finally { state.running = false; render(); }
}

fetch('/api/bootstrap').then(response => {
  if (!response.ok) throw new Error('Backend unavailable');
  return response.json();
}).then(data => {
  state.data = data;
  state.selectedCase = data.cases[1]?.id || data.cases[0]?.id;
  state.prompt = data.cases.find(item => item.id === state.selectedCase)?.prompt || '';
  render();
}).catch(() => { app.innerHTML = '<div class="error" style="margin:24px">The local dashboard could not load its backend evidence. Start it with <code>python web_server.py</code>.</div>'; });
