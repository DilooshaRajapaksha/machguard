/* Same-origin API; the token stays in memory and is cleared on sign-out/reload. */
const $ = (id) => document.getElementById(id);
let token = "", page = "Home", data = {machines: [], categories: [], engineers: [], reports: []};
let formKind = "", editing = null, saving = false, loaded = false;
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const empty = text => '<div class="empty">' + escapeHTML(text) + '</div>';

async function api(path, method = "GET", body) {
  let response;
  try {
    response = await fetch(path, {
      method, headers: {"Content-Type": "application/json", ...(token ? {Authorization: "Bearer " + token} : {})},
      ...(body === undefined ? {} : {body: JSON.stringify(body)})
    });
  } catch { throw new Error("Cannot reach the backend. Check that Uvicorn is running."); }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") signOut();
    const detail = result.detail;
    throw new Error(Array.isArray(detail) ? detail.map(x => x.loc.slice(1).join(" ") + ": " + x.msg).join("; ") : detail || "Request failed.");
  }
  return result;
}
function notice(text, error = false) {
  $("notice").textContent = text;
  $("notice").className = error ? "error" : "";
}
function showView(id) {
  ["login-view","password-view","workspace"].forEach(name => $(name).hidden = name !== id);
}
function signOut() {
  token = ""; loaded = false;
  data = {machines: [], categories: [], engineers: [], reports: []};
  $("modal").close(); $("record-form").reset(); $("content").replaceChildren();
  $("login-form").reset(); $("password-form").reset();
  $("login-error").textContent = ""; $("password-error").textContent = "";
  showView("login-view");
}
async function enterWorkspace() {
  const me = await api("/auth/me");
  if (me.must_change_password) { showView("password-view"); return; }
  if (me.role !== "admin") { signOut(); throw new Error("This panel is for administrators. Please use an admin account."); }
  page = "Home"; showView("workspace"); render(); await refresh();
}
$("login-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true; $("login-error").textContent = "";
  try {
    const result = await api("/auth/login", "POST", Object.fromEntries(new FormData(event.target)));
    token = result.access_token; event.target.reset(); await enterWorkspace();
  } catch (error) { $("login-error").textContent = error.message; }
  finally { button.disabled = false; }
});
$("password-form").addEventListener("submit", async event => {
  event.preventDefault(); event.submitter.disabled = true; $("password-error").textContent = "";
  try {
    const result = await api("/auth/change-password", "POST", Object.fromEntries(new FormData(event.target)));
    token = result.access_token; event.target.reset(); await enterWorkspace();
  } catch (error) { $("password-error").textContent = error.message; }
  finally { event.submitter.disabled = false; }
});
$("logout").onclick = signOut;
$("password-back").onclick = signOut;
async function refresh() {
  $("refresh").disabled = true; notice("Loading records…");
  try { data = await api("/admin/registry"); loaded = true; render(); notice("Records are up to date."); }
  catch (error) { notice(error.message, true); }
  finally { $("refresh").disabled = false; }
}
$("refresh").onclick = refresh;
document.querySelectorAll("[data-page]").forEach(button => {
  button.onclick = () => {page = button.dataset.page; render();};
});
function stat(label, number, note) {
  return '<div class="stat"><p>'+label+'</p><strong>'+number+'</strong><small>'+note+'</small></div>';
}
function table(headers, rows) {
  return '<div class="table-wrap"><table><thead><tr>'+headers.map(h=>'<th>'+h+'</th>').join("")+'</tr></thead><tbody>'+rows.join("")+'</tbody></table></div>';
}
function machineTable(machines) {
  if (!machines.length) return empty("No machines yet. Add a category, then add your first machine.");
  return table(["Machine","Category / location","Status","Assigned engineer","Action"], machines.map(m =>
    '<tr><td><strong>'+escapeHTML(m.name)+'</strong><small>'+escapeHTML(m.machine_id)+' · '+escapeHTML(m.model)+'</small></td><td>'+escapeHTML(m.category_name)+'<small>'+escapeHTML(m.location)+'</small></td><td><span class="badge '+escapeHTML(m.status)+'">'+escapeHTML(m.status)+'</span></td><td>'+escapeHTML(m.engineer_name || "Unassigned")+'</td><td class="row-actions"><button data-edit="'+m.id+'">Edit</button></td></tr>'
  ));
}
function render() {
  $("breadcrumb").textContent = page;
  $("page-title").textContent = {Home:"Dockyard overview",Machines:"Machine registry",Engineers:"Your engineering team",Reports:"Maintenance reports"}[page];
  $("subtitle").textContent = {Home:"A clear view of your equipment, people and maintenance records.",Machines:"Organise equipment by category and assign the right engineer.",Engineers:"Keep staff details together and see their machine assignments.",Reports:"Keep a record of inspections, findings and maintenance work."}[page];
  document.querySelectorAll("[data-page]").forEach(b => {
    b.classList.toggle("active", b.dataset.page === page);
    if(b.dataset.page === page) b.setAttribute("aria-current","page"); else b.removeAttribute("aria-current");
  });
  if (!loaded) { $("content").innerHTML = empty("Records have not loaded yet. Use Refresh to try again."); return; }
  const add = (kind,label) => '<button class="primary" data-add="'+kind+'">+ '+label+'</button>';
  let html = "";
  if (page === "Home") {
    const assigned = new Set(data.machines.filter(m=>m.engineer_id).map(m=>m.engineer_id)).size;
    html = '<section class="stats">'+stat("Machines working",data.machines.filter(m=>m.status==="Working").length,"Admin-entered status · not live telemetry")+stat("Engineers assigned",assigned,"Unique engineers assigned to machines")+stat("Maintenance reports",data.reports.length,"Saved inspection and maintenance notes")+'</section><section class="panel"><h2>Quick actions</h2><p class="muted">Start with the people and equipment at your dockyard.</p><div class="shortcuts"><button data-add="machine">+ Add machine<span>Register equipment and assign an engineer</span></button><button data-add="engineer">+ Add engineer<span>Add a staff record to your team</span></button><button data-add="report">+ Create report<span>Record an inspection or maintenance task</span></button></div></section><section class="panel"><div class="section-head"><h2>Recently registered machines</h2><button data-go="Machines">View all →</button></div>'+machineTable(data.machines.slice(0,5))+'</section>';
  } else if (page === "Machines") {
    html = '<section class="stats">'+stat("Registered machines",data.machines.length,"All equipment in the registry")+stat("Machine categories",data.categories.length,"Your equipment groups")+stat("Under maintenance",data.machines.filter(m=>m.status==="Maintenance").length,"Admin-entered status")+'</section><section class="panel"><div class="section-head"><h2>Equipment</h2><div class="actions">'+add("category","Add category")+add("machine","Add machine")+'</div></div>'+machineTable(data.machines)+'</section><section class="panel"><h2>Machine categories</h2>'+(data.categories.length?'<div class="category-list">'+data.categories.map(c=>'<span>'+escapeHTML(c.name)+' · '+data.machines.filter(m=>m.category_id===c.id).length+'</span>').join("")+'</div>':empty("No categories yet. Try Compressor or Generator."))+'</section>';
  } else if(page === "Engineers") {
    html = '<section class="panel"><div class="section-head"><div><h2>Engineers · '+data.engineers.length+'</h2><p class="muted">Staff records only. Adding a person here does not create a login account.</p></div>'+add("engineer","Add engineer")+'</div>'+
      (data.engineers.length?table(["Engineer","Email","Specialty","Assigned machines"],data.engineers.map(e=>'<tr><td>'+escapeHTML(e.name)+'</td><td>'+escapeHTML(e.email)+'</td><td>'+escapeHTML(e.specialty)+'</td><td>'+escapeHTML(data.machines.filter(m=>m.engineer_id===e.id).map(m=>m.name).join(", ")||"Unassigned")+'</td></tr>')):empty("No engineers yet. Add your first team member."))+'</section>';
  } else {
    html = '<section class="panel"><div class="section-head"><h2>Reports · '+data.reports.length+'</h2>'+add("report","Create report")+'</div>'+
      (data.reports.length?data.reports.map(r=>'<article class="report"><h3>'+escapeHTML(r.title)+'</h3><small>'+escapeHTML(r.machine_name)+' · '+escapeHTML(new Date(r.created_at).toLocaleString())+' · '+escapeHTML(r.created_by)+'</small><p>'+escapeHTML(r.notes)+'</p></article>').join(""):empty("No reports yet. Register a machine, then record its first inspection."))+'</section>';
  }
  $("content").innerHTML = html;
}
$("content").addEventListener("click", event => {
  const button = event.target.closest("button");
  if (!button) return;
  if (button.dataset.go) { page = button.dataset.go; render(); }
  if (button.dataset.add) openForm(button.dataset.add);
  if (button.dataset.edit) openForm("machine", data.machines.find(m=>m.id===Number(button.dataset.edit)));
});
function input(name, label, value = "", type = "text", max = 100, min = 2) {
  return '<label>'+label+'<input name="'+name+'" type="'+type+'" value="'+escapeHTML(value)+'" required maxlength="'+max+'" minlength="'+min+'"></label>';
}
function select(name,label,items,value="",optional=false) {
  return '<label>'+label+'<select name="'+name+'" '+(optional?"":"required")+'><option value="">'+(optional?"Unassigned":"Choose…")+'</option>'+
    items.map(item=>'<option value="'+escapeHTML(item.id)+'" '+(String(item.id)===String(value)?"selected":"")+'>'+escapeHTML(item.name)+'</option>').join("")+'</select></label>';
}
function openForm(kind, record = null) {
  if (kind === "machine" && !data.categories.length) {
    notice("First add a machine category. Then you can register the machine."); kind = "category";
  }
  if (kind === "report" && !data.machines.length) { notice("Please add a machine before creating a report.", true); return; }
  formKind = kind; editing = record; $("form-error").textContent = "";
  $("modal-title").textContent = {category:"Add machine category",engineer:"Add engineer",machine:record?"Edit machine":"Add machine",report:"Create maintenance report"}[kind];
  const r = record || {};
  let fields = "";
  if(kind === "category") fields = input("name","Category name","","text",80);
  if(kind === "engineer") fields = '<p class="muted">This creates a staff record, not a sign-in account.</p>'+input("name","Full name","","text",80)+input("email","Email address","","email",150)+input("specialty","Specialty (e.g. Mechanical maintenance)");
  if(kind === "machine") fields = input("machine_id","Machine ID (e.g. compressor-1)",r.machine_id,"text",64)+input("name","Machine name",r.name)+select("category_id","Category",data.categories,r.category_id)+input("model","Model",r.model,"text",100,1)+input("serial_number","Serial number",r.serial_number,"text",100,1)+input("location","Location",r.location,"text",150)+select("status","Recorded operating status",["Stopped","Working","Maintenance"].map(s=>({id:s,name:s})),r.status||"Stopped")+select("engineer_id","Assigned engineer",data.engineers,r.engineer_id,true);
  if(kind === "report") fields = select("machine_id","Machine",data.machines)+input("title","Report title","","text",150,3)+'<label>Inspection / maintenance notes<textarea name="notes" required minlength="3" maxlength="5000"></textarea></label>';
  $("fields").innerHTML = fields; $("modal").showModal();
}
$("close-modal").onclick = $("cancel-modal").onclick = () => {if(!saving) $("modal").close();};
$("modal").addEventListener("cancel", event => {if(saving) event.preventDefault();});
$("record-form").addEventListener("submit", async event => {
  event.preventDefault(); if (saving) return;
  saving = true; $("save").disabled = true; $("form-error").textContent = "";
  const body = Object.fromEntries(new FormData(event.target));
  for (const key of ["category_id","engineer_id"]) if(key in body) body[key] = body[key] ? Number(body[key]) : null;
  if(formKind === "report") body.machine_id = Number(body.machine_id);
  const route = {category:"categories",engineer:"engineers",machine:"machines",report:"reports"}[formKind];
  try {
    await api("/admin/registry/"+route+(editing?"/"+editing.id:""),editing?"PUT":"POST",body);
    $("modal").close(); event.target.reset(); await refresh();
  } catch(error) { $("form-error").textContent = error.message; }
  finally {saving = false; $("save").disabled = false;}
});
