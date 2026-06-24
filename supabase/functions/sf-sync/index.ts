// Edge Function: sf-sync
// Salesforce(LEALA) -> Supabase dynamic.cases ETL (JWT Bearer flow).
//
// 認証: External Client App "ALO_Knowledge_DB" の JWT ベアラーフロー。
//   署名鍵・Consumer Key・username・login URL は Supabase Vault に格納
//   (sf_jwt_private_key / sf_consumer_key / sf_username / sf_login_url)。
//   このソースに秘密情報は含めない（Vault から SUPABASE_DB_URL 経由で取得）。
// 冪等: cases(sf_record_type, sf_record_id) を主キーに upsert。再実行で重複なし。
// 起動: pg_net / http 拡張から POST {"action":"sync"}。pg_cron で定期実行。

import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import postgres from "npm:postgres@3.4.5";

const API = "v60.0";

function b64url(buf: ArrayBuffer | Uint8Array): string {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let s = ""; for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlStr(str: string): string { return b64url(new TextEncoder().encode(str)); }
function pemToDer(pem: string): Uint8Array {
  const b64 = pem.replace(/-----BEGIN [^-]+-----/, "").replace(/-----END [^-]+-----/, "").replace(/\s+/g, "");
  const bin = atob(b64); const der = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) der[i] = bin.charCodeAt(i); return der;
}

async function getAccessToken(sec: Record<string, string>) {
  const key = await crypto.subtle.importKey("pkcs8", pemToDer(sec.sf_jwt_private_key),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const header = b64urlStr(JSON.stringify({ alg: "RS256" }));
  const claims = b64urlStr(JSON.stringify({ iss: sec.sf_consumer_key, sub: sec.sf_username, aud: sec.sf_login_url, exp: Math.floor(Date.now() / 1000) + 180 }));
  const signingInput = `${header}.${claims}`;
  const sig = await crypto.subtle.sign({ name: "RSASSA-PKCS1-v1_5" }, key, new TextEncoder().encode(signingInput));
  const jwt = `${signingInput}.${b64url(sig)}`;
  const res = await fetch(`${sec.sf_login_url}/services/oauth2/token`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion: jwt }) });
  const body = await res.json();
  return { ok: res.ok, status: res.status, body };
}

async function soqlAll(instance: string, access: string, obj: string, fields: string[]) {
  const q = `SELECT ${fields.join(",")} FROM ${obj}`;
  let url: string | null = `${instance}/services/data/${API}/query?q=${encodeURIComponent(q)}`;
  const records: any[] = [];
  while (url) {
    const r = await fetch(url, { headers: { Authorization: `Bearer ${access}` } });
    if (!r.ok) throw new Error(`query ${obj} ${r.status}: ${await r.text()}`);
    const j = await r.json();
    records.push(...j.records);
    url = j.nextRecordsUrl ? `${instance}${j.nextRecordsUrl}` : null;
  }
  return records;
}

const BUSINESS_FIELDS = ["Id","Name","leala__Status__c","leala__ChargeLawyer__c","leala__Clerk__c","leala__Team__c","leala__Source__c","leala__SourceMiddle__c","leala__SourcePartner__c","leala__CaseCategorySingle__c","leala__MandatoryDate__c","leala__CloseDate__c","leala__ExpectedCloseDate__c","ALO_Next_Deadline_At__c","ALO_Waiting_On__c","ALO_Outcome__c","leala__Consultation__c","leala__UploadFolderUrlBox__c","leala__AccountName__c","Earnings__c","leala__Memo__c","leala__CaseOutline__c","CreatedDate","LastModifiedDate"];
const CONSULTATION_FIELDS = ["Id","Name","leala__StageName__c","leala__ChargeLawyer__c","leala__Clerk__c","leala__Team__c","leala__Source__c","leala__SourceMiddle__c","leala__SourcePartner__c","leala__CaseCategorySingle__c","leala__ConsultationReceptionDate__c","leala__ConsultedDate__c","leala__CloseDate__c","leala__ExpectedCloseDate__c","leala__ReasonForFailure__c","leala__ReasonWhyNotReachConsultation__c","leala__DetailedReasonForClosing__c","leala__Probability__c","leala__ConsultationConverted__c","leala__UploadFolderUrlBox__c","leala__AccountKana__c","leala__DisplayName__c","leala__CaseOutline__c","CreatedDate","LastModifiedDate"];

function mapRow(obj: string, rec: any) {
  const g = (k: string) => { const v = rec[k]; return (v === undefined || v === "") ? null : v; };
  return {
    sf_record_type: obj, sf_record_id: rec.Id,
    case_label: g("Name"), name: g("Name"),
    status: g("leala__Status__c") ?? g("leala__StageName__c"),
    charge_lawyer_id: g("leala__ChargeLawyer__c"), clerk_id: g("leala__Clerk__c"), team_id: g("leala__Team__c"),
    source: g("leala__Source__c"), source_middle: g("leala__SourceMiddle__c"), source_partner_id: g("leala__SourcePartner__c"),
    case_category: g("leala__CaseCategorySingle__c"),
    reception_date: g("leala__ConsultationReceptionDate__c"), consulted_date: g("leala__ConsultedDate__c"),
    mandatory_date: g("leala__MandatoryDate__c"), close_date: g("leala__CloseDate__c"), expected_close_date: g("leala__ExpectedCloseDate__c"),
    reason_for_failure: g("leala__ReasonForFailure__c"), reason_not_reach: g("leala__ReasonWhyNotReachConsultation__c"), detailed_reason_closing: g("leala__DetailedReasonForClosing__c"),
    next_deadline_at: g("ALO_Next_Deadline_At__c"), waiting_on: g("ALO_Waiting_On__c"), outcome: g("ALO_Outcome__c"),
    probability: g("leala__Probability__c"), consultation_converted: g("leala__ConsultationConverted__c"),
    consultation_ref: g("leala__Consultation__c"), box_folder_url: g("leala__UploadFolderUrlBox__c"),
    account_name: g("leala__AccountName__c") ?? g("leala__DisplayName__c"), earnings: g("Earnings__c"),
    sf_created_date: g("CreatedDate"), sf_last_modified: g("LastModifiedDate"),
    first_date: g("CreatedDate"), last_date: g("LastModifiedDate"), sf_raw: rec,
  };
}

Deno.serve(async (req: Request) => {
  const sql = postgres(Deno.env.get("SUPABASE_DB_URL")!, { prepare: false });
  const log = async (action: string, ok: boolean, detail: unknown) => {
    try { await sql`insert into dynamic.sf_sync_runs (action, ok, detail) values (${action}, ${ok}, ${sql.json(detail as any)})`; } catch (_) { /* noop */ }
  };
  let action = "sync";
  try { const b = await req.json(); if (b && b.action) action = b.action; } catch (_) { /* noop */ }
  try {
    const rows = await sql`select name, decrypted_secret from vault.decrypted_secrets where name in ('sf_consumer_key','sf_jwt_private_key','sf_login_url','sf_username')`;
    const sec: Record<string, string> = {}; for (const r of rows) sec[r.name as string] = r.decrypted_secret as string;
    const tok = await getAccessToken(sec);
    if (!tok.ok) { await log(action, false, { step: "token", status: tok.status, body: tok.body }); await sql.end(); return Response.json({ ok: false, step: "token", status: tok.status, body: tok.body }); }
    const access = tok.body.access_token as string; const instance = tok.body.instance_url as string;

    const counts: Record<string, number> = {};
    for (const [obj, fields] of [["leala__Business__c", BUSINESS_FIELDS], ["leala__Consultation__c", CONSULTATION_FIELDS]] as const) {
      const recs = await soqlAll(instance, access, obj, fields as string[]);
      for (const rec of recs) {
        const m = mapRow(obj, rec);
        await sql`insert into dynamic.cases (sf_record_type, sf_record_id, case_label, name, status, charge_lawyer_id, clerk_id, team_id, source, source_middle, source_partner_id, case_category, reception_date, consulted_date, mandatory_date, close_date, expected_close_date, reason_for_failure, reason_not_reach, detailed_reason_closing, next_deadline_at, waiting_on, outcome, probability, consultation_converted, consultation_ref, box_folder_url, account_name, earnings, sf_created_date, sf_last_modified, first_date, last_date, sf_raw, sf_synced_at)
          values (${m.sf_record_type}, ${m.sf_record_id}, ${m.case_label}, ${m.name}, ${m.status}, ${m.charge_lawyer_id}, ${m.clerk_id}, ${m.team_id}, ${m.source}, ${m.source_middle}, ${m.source_partner_id}, ${m.case_category}, ${m.reception_date}, ${m.consulted_date}, ${m.mandatory_date}, ${m.close_date}, ${m.expected_close_date}, ${m.reason_for_failure}, ${m.reason_not_reach}, ${m.detailed_reason_closing}, ${m.next_deadline_at}, ${m.waiting_on}, ${m.outcome}, ${m.probability}, ${m.consultation_converted}, ${m.consultation_ref}, ${m.box_folder_url}, ${m.account_name}, ${m.earnings}, ${m.sf_created_date}, ${m.sf_last_modified}, ${m.first_date}, ${m.last_date}, ${sql.json(m.sf_raw)}, now())
          on conflict (sf_record_type, sf_record_id) do update set case_label=excluded.case_label, name=excluded.name, status=excluded.status, charge_lawyer_id=excluded.charge_lawyer_id, clerk_id=excluded.clerk_id, team_id=excluded.team_id, source=excluded.source, source_middle=excluded.source_middle, source_partner_id=excluded.source_partner_id, case_category=excluded.case_category, reception_date=excluded.reception_date, consulted_date=excluded.consulted_date, mandatory_date=excluded.mandatory_date, close_date=excluded.close_date, expected_close_date=excluded.expected_close_date, reason_for_failure=excluded.reason_for_failure, reason_not_reach=excluded.reason_not_reach, detailed_reason_closing=excluded.detailed_reason_closing, next_deadline_at=excluded.next_deadline_at, waiting_on=excluded.waiting_on, outcome=excluded.outcome, probability=excluded.probability, consultation_converted=excluded.consultation_converted, consultation_ref=excluded.consultation_ref, box_folder_url=excluded.box_folder_url, account_name=excluded.account_name, earnings=excluded.earnings, sf_created_date=excluded.sf_created_date, sf_last_modified=excluded.sf_last_modified, first_date=excluded.first_date, last_date=excluded.last_date, sf_raw=excluded.sf_raw, sf_synced_at=now()`;
      }
      counts[obj] = recs.length;
    }
    await log(action, true, { counts });
    await sql.end();
    return Response.json({ ok: true, action, counts });
  } catch (e) {
    try { await log(action, false, { error: String(e) }); } catch (_) { /* noop */ }
    try { await sql.end(); } catch (_) { /* noop */ }
    return Response.json({ ok: false, step: "exception", error: String(e) });
  }
});
